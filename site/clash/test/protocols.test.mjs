import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {parse} from 'yaml';
import {buildConfig, defaultDns} from '../src/config.mjs';
import {awgConfLink, awgProxy, ttProxies} from '../src/protocol-converters.mjs';
import {unpackProfileZip} from '../src/archive.mjs';

const key = n => Buffer.alloc(32,n).toString('base64');
const options = {subscriptions:'https://sub.example.test/mihomo'};
const wg = `[Interface]\nPrivateKey = ${key(1)}\nAddress = 10.2.0.2/32, fd00::2/128\nDNS = 9.9.9.9\nMTU = 1380\n[Peer]\nPublicKey = ${key(2)}\nAllowedIPs = 0.0.0.0/0, ::/0\nEndpoint = wg.example.test:51820\nPersistentKeepalive = 25\n`;
const ovpn = `client\ndev tun\nproto tcp-client\nremote ovpn.example.test 443\nremote backup.example.test 1194 udp\nnobind\npersist-key\npersist-tun\nremote-cert-tls server\nauth SHA256\ncipher AES-256-GCM\ndata-ciphers AES-256-GCM:AES-128-GCM\nverb 3\n<ca>\n-----BEGIN CERTIFICATE-----\nc3ludGhldGlj\n-----END CERTIFICATE-----\n</ca>\n<auth-user-pass>\nsynthetic-user\nsynthetic-password\n</auth-user-pass>\n`;
const nodes = config => parse(config)['proxy-providers'].Bonus.payload;
const awg = `[Interface]\nPrivateKey = ${key(1)}\nAddress = 10.8.0.2/32, fd00::2/128\nDNS = 1.1.1.1\nMTU = 1280\nJc = 4\nJmin = 40\nJmax = 70\nS1 = 12\nS2 = 13\nS3 = 14\nS4 = 15\nH1 = 1-3\nH2 = 4\nH3 = 5\nH4 = 6\nI1 = <t>\nI2 = <r 15>\nI3 = <rc 10>\nI4 = <rd 4>\nI5 = <b 0x1234>\nHeaderProtectionKey = ${key(4)}\nRandomTrailers = on\nDisableCookies = 0\n[Peer]\nPublicKey = ${key(2)}\nPresharedKey = ${key(3)}\nAllowedIPs = 0.0.0.0/0, ::/0\nEndpoint = vpn.example.test:51820\nPersistentKeepalive = 25\n`;

function quic(value) {
  if (value < 64) return Buffer.from([value]);
  if (value < 16384) return Buffer.from([0x40 | (value >> 8), value & 0xff]);
  throw new Error('test varint too large');
}
function ttField(tag, value) {
  const bytes = Buffer.isBuffer(value) ? value : Buffer.from(value);
  return Buffer.concat([quic(tag), quic(bytes.length), bytes]);
}
const ttLink = 'tt://' + Buffer.concat([
  ttField(1, 'tt-origin.example.test'),
  ttField(2, 'proxy.example.test:443'),
  ttField(2, '[2001:db8::2]:8443'),
  ttField(3, 'sni.example.test'),
  ttField(5, 'synthetic-user'),
  ttField(6, 'synthetic-password'),
  ttField(7, Buffer.from([1])),
  ttField(9, quic(2)),
  ttField(12, 'TT Demo'),
]).toString('base64url');

test('missing or blank DNS uses public SR resolvers; unrelated inputs are optional',()=>{
  for(const dns of [undefined,'','  ']) {
    const c=parse(buildConfig({...options,dns}));
    assert.deepEqual(c.dns.nameserver,defaultDns);
    assert.equal(c.dns['nameserver-policy'],undefined);
    assert.equal(c.hosts,undefined);
  }
  assert.deepEqual(parse(buildConfig({...options,dns:'https://custom.example.test/dns-query'})).dns.nameserver,['https://custom.example.test/dns-query']);
});
test('WG conf works as the only input, preserving peer, addresses and optional defaults',()=>{
  const n=nodes(buildConfig({wgFiles:[{name:'plain.conf',text:wg}]}))[0];
  assert.equal(n.type,'wireguard');
  assert.equal(n.server,'wg.example.test');assert.equal(n.port,51820);
  assert.equal(n.ip,'10.2.0.2');assert.equal(n.ipv6,'fd00::2');
  assert.equal(n['private-key'],key(1));assert.equal(n['public-key'],key(2));
  assert.equal(n.mtu,1380);assert.equal(n['persistent-keepalive'],25);
  assert.equal(n['amnezia-wg-option'],undefined);
  const minimal=wg.replace('DNS = 9.9.9.9\n','').replace('PersistentKeepalive = 25\n','');
  assert.equal(nodes(buildConfig({wgFiles:[{name:'minimal.conf',text:minimal}]}))[0].type,'wireguard');
});
test('plain WG URIs support query credentials and wireguard userinfo; AWG is not inferred',()=>{
  const query=new URLSearchParams({privateKey:key(1),publicKey:key(2),ip:'10.2.0.2/32',dns:'9.9.9.9',keepalive:'25',reserved:'1,2,3'});
  const n=nodes(buildConfig({links:`wg://wg.example.test:51820?${query}#Plain` }))[0];
  assert.equal(n.type,'wireguard');assert.deepEqual(n.reserved,[1,2,3]);
  assert.equal(n['amnezia-wg-option'],undefined);
  const wireguard=`wireguard://${encodeURIComponent(key(1))}@wg.example.test:51820?publickey=${encodeURIComponent(key(2))}&address=10.2.0.2%2F32#Plain`;
  assert.equal(nodes(buildConfig({links:wireguard}))[0]['public-key'],key(2));
});
test('Mieru URI preserves credentials, ranges, transports and multiplexing',()=>{
  const links='mierus://user:p%3Ass@mr.example.test?port=2090&protocol=TCP&port=3000-3010&protocol=UDP&multiplexing=MULTIPLEXING_LOW#Mieru';
  const n=nodes(buildConfig({links}));
  assert.equal(n.length,2);assert.equal(n[0].type,'mieru');assert.equal(n[0].password,'p:ss');
  assert.equal(n[0].transport,'TCP');assert.equal(n[0].port,2090);
  assert.equal(n[1].transport,'UDP');assert.equal(n[1]['port-range'],'3000-3010');assert.equal(n[1].port,undefined);
  assert.equal(n[0].multiplexing,'MULTIPLEXING_LOW');
});
test('OpenVPN inline credentials and each remote become native OpenVPN nodes',()=>{
  const n=nodes(buildConfig({ovpnFiles:[{name:'office.ovpn',text:ovpn}]}));
  assert.equal(n.length,2);assert.equal(n[0].type,'openvpn');assert.equal(n[0].proto,'tcp');
  assert.equal(n[1].proto,'udp');assert.equal(n[1].server,'backup.example.test');
  assert.equal(n[0].username,'synthetic-user');assert.equal(n[0].password,'synthetic-password');
  assert.equal(n[0].auth,'SHA256');assert.equal(n[0].cipher,'AES-256-GCM');
  assert.deepEqual(n[0]['data-ciphers'],['AES-256-GCM','AES-128-GCM']);
  assert.match(n[0].ca,/BEGIN CERTIFICATE/);
});
test('Mihomo file preserves all nine protocol variants and ignores its routing',()=>{
  const input=[
    {name:'V',type:'vless',server:'v.example.test',port:443,uuid:'12345678-1234-1234-1234-123456789abc',network:'xhttp','xhttp-opts':{path:'/x',host:'cover.example.test',mode:'auto'}},
    {name:'T',type:'trojan',server:'t.example.test',port:443,password:'synthetic'},
    {name:'S',type:'ss',server:'s.example.test',port:443,cipher:'aes-128-gcm',password:'synthetic'},
    {name:'H',type:'hysteria2',server:'h.example.test',port:443,password:'synthetic'},
    {name:'O',type:'openvpn',server:'o.example.test',port:1194,ca:'synthetic',username:'synthetic',password:'synthetic'},
    {name:'W',type:'wireguard',server:'w.example.test',port:51820,ip:'10.2.0.2','private-key':key(1),'public-key':key(2)},
    {name:'A',type:'wireguard',server:'a.example.test',port:51820,ip:'10.2.0.3','private-key':key(1),'public-key':key(2),'amnezia-wg-option':{version:3,jc:4,'random-trailers':true}},
    {name:'TT',type:'trusttunnel',server:'tt.example.test',port:443,username:'synthetic',password:'synthetic',quic:true},
    {name:'M',type:'mieru',server:'m.example.test',port:2090,transport:'TCP',username:'synthetic',password:'synthetic'},
  ];
  const c=parse(buildConfig({mihomoFiles:[{name:'all.json',text:JSON.stringify({proxies:input,rules:['MATCH,REJECT'],dns:{enable:false}})}]}));
  assert.equal(c['proxy-providers'].Bonus.payload.length,9);
  assert.deepEqual(c['proxy-providers'].Bonus.payload.map(({name,...p})=>p),input.map(({name,...p})=>p));
  assert.equal(c.rules.includes('MATCH,REJECT'),false);assert.equal(c.dns.enable,true);
  assert.equal(c['proxy-groups'].find(g=>g.name==='Режим').use[0],'Bonus');
});
test('VLESS XHTTP URI becomes native xhttp options',()=>{
  const n=nodes(buildConfig({links:'vless://12345678-1234-1234-1234-123456789abc@v.example.test:443?security=tls&type=xhttp&host=cover.example.test&path=%2Fx&mode=auto#XHTTP'}))[0];
  assert.equal(n.network,'xhttp');assert.deepEqual(n['xhttp-opts'],{host:'cover.example.test',path:'/x',mode:'auto'});
});
test('invalid supplied files fail without leaking input or weakening protocol properties',()=>{
  for(const extra of [
    {wgFiles:[{name:'broken.conf',text:wg.replace('AllowedIPs = 0.0.0.0/0, ::/0','AllowedIPs = 10.0.0.0/8')}]},
    {wgFiles:[{name:'broken.conf',text:wg+'PostUp = sensitive-command\n'}]},
    {ovpnFiles:[{name:'broken.ovpn',text:ovpn+'script-security 2\nup sensitive-command\n'}]},
    {ovpnFiles:[{name:'broken.ovpn',text:ovpn.replace(/<ca>[\s\S]*?<\/ca>/,'ca sensitive-path')}]},
    {links:'mierus://user:sensitive-password@mr.example.test?port=2090&protocol=BOGUS#MR'},
    {links:'naive+https://user:sensitive-password@naive.example.test#NV'},
    {mihomoFiles:[{name:'bad.yaml',text:'proxies: [{name: NV, type: naive, password: sensitive-password}]'}]},
    {mihomoFiles:[{name:'bad.yaml',text:'proxies: &x [*x]'}]},
  ]) assert.throws(()=>buildConfig({...options,...extra}),e=>!e.message.includes('sensitive-'));
});
test('file limits cover every protocol input together; no absent input causes a TypeError',()=>{
  assert.throws(()=>buildConfig({...options,wgFiles:Array(101).fill({name:'a.conf',text:wg})}),/100/);
  assert.throws(()=>buildConfig({}),e=>!(e instanceof TypeError)&&/источник|подписк|узл/i.test(e.message));
});

test('Mihomo OpenVPN accepts and preserves multiline inline PEM material',()=>{
  const ca='-----BEGIN CERTIFICATE-----\nc3ludGhldGlj\n-----END CERTIFICATE-----\n';
  const n=nodes(buildConfig({mihomoFiles:[{name:'vpn.json',text:JSON.stringify({proxies:[{name:'OVPN',type:'openvpn',server:'o.example.test',port:1194,ca,username:'synthetic',password:'synthetic'}]})}]}))[0];
  assert.equal(n.ca,ca);
});

test('mixed ZIP imports WG, OpenVPN and native Mihomo files without requiring every category',async()=>{
  const {unpackProfileZip}=await import('../src/archive.mjs');
  const {execFileSync}=await import('node:child_process');
  const files={'wg.conf':wg,'vpn.ovpn':ovpn,'mr.json':JSON.stringify({proxies:[{name:'M',type:'mieru',server:'m.example.test',port:2090,transport:'TCP',username:'synthetic',password:'synthetic'}]})};
  const python=`import sys,json,io,zipfile\nb=io.BytesIO()\nwith zipfile.ZipFile(b,'w',compression=8) as z:\n for name,text in json.load(sys.stdin).items():z.writestr(name,text)\nsys.stdout.buffer.write(b.getvalue())`;
  const zip=execFileSync('python3',['-c',python],{input:JSON.stringify(files)});
  const unpacked=await unpackProfileZip(zip);
  assert.deepEqual(Object.fromEntries(unpacked.map(f=>[f.name,f.text])),files);
  const c=buildConfig({wgFiles:unpacked.filter(f=>f.name.endsWith('.conf')),ovpnFiles:unpacked.filter(f=>f.name.endsWith('.ovpn')),mihomoFiles:unpacked.filter(f=>f.name.endsWith('.json'))});
  assert.deepEqual(nodes(c).map(n=>n.type),['wireguard','openvpn','openvpn','mieru']);
});

test('Mieru default MTU from provider links matches the core default; custom MTU is not silently lost',()=>{
  const uri='mierus://user:synthetic@mr.example.test?port=2090&protocol=TCP&mtu=1400&multiplexing=MULTIPLEXING_LOW&profile=France%20MR#France%20MR';
  const n=nodes(buildConfig({links:uri}))[0];
  assert.equal(n.type,'mieru');assert.equal(n.multiplexing,'MULTIPLEXING_LOW');
  assert.throws(()=>buildConfig({links:uri.replace('mtu=1400','mtu=1500')}));
});

test('AWG profile conversion keeps synthetic AWG 3.1 fields in a native Mihomo node', () => {
  const converted = awgProxy(awgConfLink(awg, 'demo.conf'));
  assert.equal(converted.type, 'wireguard');
  assert.equal(converted.server, 'vpn.example.test');
  assert.equal(converted.port, 51820);
  assert.equal(converted['private-key'], key(1));
  assert.equal(converted.ip, '10.8.0.2');
  assert.equal(converted.ipv6, 'fd00::2');
  assert.deepEqual(converted['amnezia-wg-option'], {
    version: 3, jc: 4, jmin: 40, jmax: 70, s1: 12, s2: 13, s3: 14, s4: 15,
    h1: '1-3', h2: '4', h3: '5', h4: '6', i1: '<t>', i2: '<r 15>', i3: '<rc 10>', i4: '<rd 4>', i5: '<b 0x1234>',
    'header-protection-key': key(4), 'random-trailers': true, 'disable-cookies': false,
  });
});

test('TrustTunnel URI conversion yields one Mihomo node for each address', () => {
  const converted = ttProxies([ttLink]);
  assert.deepEqual(converted.map(node => [node.name, node.server, node.port]), [
    ['TT Demo 1', 'proxy.example.test', 443],
    ['TT Demo 2', '2001:db8::2', 8443],
  ]);
  assert.equal(converted[0].sni, 'sni.example.test');
  assert.equal(converted[0].username, 'synthetic-user');
  assert.equal(converted[0].password, 'synthetic-password');
  assert.equal(converted[0]['skip-cert-verify'], true);
  assert.equal(converted[0].quic, true);
  assert.equal(converted[1].quic, true);
  assert.throws(() => ttProxies([ttLink, ttLink]));
});

test('ZIP parsing accepts stored/deflated synthetic files and rejects corruption or encryption', async () => {
  const script = `import sys,io,zipfile\nb=io.BytesIO()\nwith zipfile.ZipFile(b,'w',compression=int(sys.argv[1])) as z:z.writestr('profiles/demo.conf',sys.stdin.read())\nsys.stdout.buffer.write(b.getvalue())`;
  for (const method of ['0', '8']) {
    const zip = execFileSync('python3', ['-c', script, method], {input: awg});
    assert.deepEqual(await unpackProfileZip(zip), [{name: 'demo.conf', text: awg}]);
    const corrupt = Buffer.from(zip);
    corrupt[50] ^= 1;
    await assert.rejects(unpackProfileZip(corrupt));
    const encrypted = Buffer.from(zip);
    const central = encrypted.indexOf(Buffer.from('504b0102', 'hex'));
    encrypted[central + 8] |= 1;
    await assert.rejects(unpackProfileZip(encrypted));
  }
});

test('ZIP parser rejects a synthetic compressed archive above the total expansion limit', async () => {
  const script = `import sys,io,json,zipfile\nfiles=json.load(sys.stdin)\nb=io.BytesIO()\nwith zipfile.ZipFile(b,'w',compression=8) as z:\n for name,text in files.items():z.writestr(name,text)\nsys.stdout.buffer.write(b.getvalue())`;
  const files = Object.fromEntries(Array.from({length: 9}, (_, i) => [`profile-${i}.yaml`, 'x'.repeat(2 * 1024 * 1024)]));
  const zip = execFileSync('python3', ['-c', script], {input: JSON.stringify(files), maxBuffer: 1024 * 1024});
  await assert.rejects(unpackProfileZip(zip));
});
