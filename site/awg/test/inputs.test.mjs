import {test} from 'node:test';
import assert from 'node:assert/strict';
import {deflateSync} from 'node:zlib';
import {execFileSync} from 'node:child_process';
import {convertFiles} from '../inputs.mjs';
const convertLinks = async files => (await convertFiles(files)).nodes.map(node=>node.link);

const key = n => Buffer.alloc(32,n).toString('base64');
const conf = `[Interface]
PrivateKey = ${key(1)}
Address = 10.8.0.2/32
DNS = 1.1.1.1
Jc = 4
Jmin = 40
Jmax = 70
S1 = 12
S2 = 13
H1 = 1
H2 = 2
H3 = 3
H4 = 4
[Peer]
PublicKey = ${key(2)}
AllowedIPs = 0.0.0.0/0
Endpoint = vpn.example.test:51820
`;
const wireguard = conf.replace(/^(?:Jc|Jmin|Jmax|S[12]|H[1-4]) = .*\n/gm, '');
const config = (text=conf,description='Тест') => ({description, containers:[{container:'amnezia-awg',awg:{last_config:JSON.stringify({config:text})}}]});
const json = data => Buffer.from(JSON.stringify(data));
function compress(data) {
  const body = json(data), header=Buffer.alloc(4); header.writeUInt32BE(body.length);
  return Buffer.concat([header,deflateSync(body)]);
}
const vpn = data => 'vpn://' + compress(data).toString('base64url');
const file = (name,data) => new File([data],name);
function zip(entries,method=8) {
  const code = 'import sys,json,io,zipfile,base64\nb=io.BytesIO()\nwith zipfile.ZipFile(b,"w",compression=int(sys.argv[1])) as z:\n for name,data in json.load(sys.stdin).items(): z.writestr(name,base64.b64decode(data))\nsys.stdout.buffer.write(b.getvalue())';
  return execFileSync('python3',['-c',code,String(method)], {input:JSON.stringify(Object.fromEntries(Object.entries(entries).map(([name,data])=>[name,Buffer.from(data).toString('base64')])))});
}

test('mixed WG and AWG files and ZIP preserve every profile in order', async () => {
  const wg = wireguard.replace('51820','51821');
  for (const inputs of [[file('first.conf',conf),file('second.conf',wg)],
    [file('mixed.zip',zip({'first.conf':conf,'second.conf':wg}))]]) {
    const result=await convertFiles(inputs);
    assert.deepEqual(result.nodes.map(node=>node.name),['first AWG','second WG']);
    assert.deepEqual(result.nodes.map(node=>new URL(node.link).port),['51820','51821']);
    assert.equal(new URL(result.nodes[0].link).searchParams.get('obfs'),'amneziawg');
    assert.equal(new URL(result.nodes[1].link).searchParams.has('obfs'),false);
  }
});

test('plain WG inside supported Amnezia containers works as a file and pasted vpn text', async () => {
  for (const container of ['amnezia-awg','amnezia-awg2','amnezia-wireguard']) {
    const protocol=container==='amnezia-wireguard'?'wireguard':'awg';
    const lastConfig=JSON.stringify({config:wireguard.replace('1.1.1.1','$PRIMARY_DNS')});
    const data={
      description:'Тест',
      dns1:'9.9.9.9',
      containers:[{container,[protocol]:{last_config:lastConfig}}],
    };
    for (const result of [await convertFiles([file('plain.vpn',vpn(data))]),await convertFiles([],vpn(data))]) {
      assert.equal(result.nodes[0].name,'Тест WG');
      assert.equal(new URL(result.nodes[0].link).searchParams.get('dns'),'9.9.9.9');
      assert.equal(new URL(result.nodes[0].link).searchParams.has('obfs'),false);
    }
  }
});

test('AWG3.1 with header protection and omitted headers and CPS works in conf and vpn inputs', async () => {
  const text=conf.replace(/^H[1-4] = .*\n/gm,'').replace('[Peer]',
    `S3 = 12\nS4 = 12\nHeaderProtectionKey = ${key(4)}\nContentPaddingAddition = 8-24\nRandomTrailers = on\n[Peer]`);
  const data=config(text,'Header protection');
  data.containers[0].container='amnezia-awg2';
  for (const result of [await convertFiles([file('protected.conf',text)]),
    await convertFiles([file('protected.vpn',vpn(data))]),await convertFiles([],vpn(data))]) {
    assert.equal(result.nodes.length,1);
    assert.match(result.nodes[0].name,/ AWG3\.1$/);
    const link=new URL(result.nodes[0].link);
    assert.equal(link.host,'vpn.example.test:51820');
    assert.equal(link.searchParams.get('privateKey'),key(1));
    assert.deepEqual(JSON.parse(link.searchParams.get('obfsParam')),{
      jc:'4',jmin:'40',jmax:'70',s1:'12',s2:'13',s3:'12',s4:'12',
      h1:'1',h2:'2',h3:'3',h4:'4',header_protection_key:key(4),
      content_padding_addition:'8-24',random_trailers:'true',
    });
  }
});

test('errors locate the bad ZIP entry and vpn profile without exposing input names or values', async () => {
  const marker='synthetic-secret-marker';
  const broken=conf.replace(/^Jc = .*\n/m,'');
  await assert.rejects(convertFiles([file(marker+'.zip',zip({'first.conf':wireguard,[marker+'.conf']:broken}))]),error=>{
    assert.match(error.message,/Файл 1, запись 2.*AWG.*отсутствует обязательное поле Jc/);
    assert.equal(error.message.includes(marker),false);
    assert.equal(error.message.includes(key(1)),false);
    return true;
  });
  const data=config(); data.containers.push(config(broken).containers[0]);
  await assert.rejects(convertFiles([],vpn(data)),/Вставленный текст, профиль 2.*отсутствует обязательное поле Jc/);
});

test('multiple selected .conf and .vpn produce one complete list with original names', async () => {
  const result = await convertLinks([file('first.conf',conf),file('second.vpn',vpn(config(conf.replace('51820','51821'),'Второй')))]);
  assert.equal(result.length,2);
  assert.deepEqual(result.map(link=>new URL(link).port),['51820','51821']);
  assert.deepEqual(result.map(link=>decodeURIComponent(new URL(link).hash.slice(1))),['first AWG','Второй AWG']);
  for (const link of result) assert.equal(new URL(link).searchParams.get('privateKey'),key(1));
});

test('.vpn supports Amnezia text, JSON, raw qCompress and uncompressed base64 JSON', async () => {
  const data=config();
  for (const body of [vpn(data),json(data),compress(data),'vpn://'+json(data).toString('base64url'),compress(data).toString('base64url')]) {
    const result=await convertLinks([file('profile.vpn',body)]);
    assert.equal(result.length,1);
    assert.equal(new URL(result[0]).host,'vpn.example.test:51820');
  }
});

test('Amnezia DNS placeholders use export addresses in files, pasted text and ZIP', async () => {
  const data={...config(conf.replace('DNS = 1.1.1.1','DNS = $PRIMARY_DNS, $SECONDARY_DNS')),
    dns1:'9.9.9.9',dns2:'2606:4700:4700::1111'};
  for (const body of [vpn(data),json(data),compress(data)]) {
    const result=await convertFiles([file('profile.vpn',body)]);
    assert.equal(new URL(result.nodes[0].link).searchParams.get('dns'),'9.9.9.9, 2606:4700:4700::1111');
  }
  for (const result of [await convertFiles([],vpn(data)),
    await convertFiles([file('profiles.zip',zip({'profile.vpn':vpn(data)}))])]) {
    assert.equal(new URL(result.nodes[0].link).searchParams.get('dns'),'9.9.9.9, 2606:4700:4700::1111');
  }
  const literal=await convertFiles([file('literal.vpn',vpn({...config(),dns1:'8.8.8.8',dns2:'8.8.4.4'}))]);
  assert.equal(new URL(literal.nodes[0].link).searchParams.get('dns'),'1.1.1.1');
  const primary=await convertFiles([file('primary.vpn',vpn({...config(conf.replace('1.1.1.1','$PRIMARY_DNS')),dns1:'9.9.9.9'}))]);
  assert.equal(new URL(primary.nodes[0].link).searchParams.get('dns'),'9.9.9.9');
});

test('Amnezia DNS substitution rejects missing addresses, injection and unknown variables', async () => {
  const marker='synthetic-secret-marker';
  const data={...config(conf.replace('DNS = 1.1.1.1','DNS = $PRIMARY_DNS, $SECONDARY_DNS')),
    dns1:'9.9.9.9',dns2:'1.1.1.1'};
  for (const dns2 of [undefined,null,42,'',marker,'999.1.1.1','dns.example.test','1.1.1.1\nMTU = 1280']) {
    await assert.rejects(convertFiles([file('invalid.vpn',vpn({...data,dns2}))]),error=>{
      assert.equal(error.message.includes(marker),false);
      assert.equal(error.message.includes(key(1)),false);
      return true;
    });
  }
  for (const text of [conf.replace('1.1.1.1','$UNKNOWN_DNS'),
    conf.replace('1.1.1.1','$PRIMARY_DNS_EXTRA'),conf.replace(key(1),'$PRIMARY_DNS')]) {
    await assert.rejects(convertFiles([file('invalid.vpn',vpn({...config(text),dns1:'9.9.9.9'}))]));
  }
});

test('one .vpn extracts all ready AWG containers and ignores other protocols', async () => {
  const data=config();
  data.containers.unshift({container:'amnezia-dns',dns:{}});
  data.containers.push(config(conf.replace('51820','51822')).containers[0]);
  const result=await convertLinks([file('multi.vpn',vpn(data))]);
  assert.deepEqual(result.map(link=>new URL(link).port),['51820','51822']);
});

test('stored and deflated ZIPs support .conf, text/binary .vpn and macOS metadata', async () => {
  const entries={'nested/first.conf':conf,'second.vpn':vpn(config(conf.replace('51820','51821'))),'third.vpn':compress(config(conf.replace('51820','51822'))),'__MACOSX/._first.conf':'metadata','.DS_Store':'metadata'};
  for (const method of [0,8]) {
    const result=await convertLinks([file('profiles.zip',zip(entries,method))]);
    assert.deepEqual(result.map(link=>new URL(link).port),['51820','51821','51822']);
  }
});

test('invalid input aborts the entire batch without exposing private values', async () => {
  const marker='synthetic-secret-marker';
  const invalid=[
    [],[file('a.exe',marker)],[file('a.conf','x'.repeat(65537))],
    [file('first.conf',conf),file('bad.vpn','vpn://'+marker)],
    [file('a.vpn',json(config(marker)))],
    [file('a.vpn',vpn({containers:[{container:'amnezia-awg',awg:{}}]}))],
    [file('a.vpn',vpn({containers:[{container:'amnezia-xray',xray:{}}]}))],
    [file('a.conf',conf),file('same.conf',conf)],
    [file('bad.zip',zip({'first.conf':conf,'unknown.txt':marker}))],
    [file('bad.zip',zip({'../bad.conf':conf}))],
    [file('bad.zip',zip({'nested.zip':'not a profile'}))],
    [file('too-many.zip',zip(Object.fromEntries(Array.from({length:101},(_,i)=>[i+'.conf',conf.replace('51820',String(51000+i))]))))],
  ];
  const bomb=compress(config('x'.repeat(2*1024*1024)));
  invalid.push([file('bomb.vpn',bomb)]);
  const wrongLength=Buffer.from(compress(config())); wrongLength.writeUInt32BE(1);
  invalid.push([file('bad-length.vpn',wrongLength)]);
  const broken=Buffer.from(compress(config())); broken[broken.length-1]^=1;
  invalid.push([file('broken.vpn',broken)]);
  for (const files of invalid) await assert.rejects(convertLinks(files), error=>{
    assert.equal(error.message.includes(marker),false);
    assert.equal(error.message.includes(key(1)),false);
    return true;
  });
});

test('Mihomo YAML, JSON, pasted text and ZIP join the same AWG/TT result',async()=>{
  const tt={type:'trusttunnel',name:'Single TT',server:'tt.example.test',port:443,username:'synthetic',password:'synthetic'};
  const source=JSON.stringify({proxies:[{type:'ss',name:'Other'},tt]});
  for(const entry of [file('tt.yaml',source),file('tt.json',source),file('set.zip',zip({'tt.yaml':source,'a.conf':conf}))]) {
    const result=await convertFiles([entry]);
    assert.equal(result.nodes.filter(node=>node.link.startsWith('tt://?')).length,1);
    assert.match(result.notes.join(' '),/других протоколов: 1/);
  }
  const result=await convertFiles([file('a.conf',conf)],source);
  assert.equal(result.nodes.length,2);
  assert.deepEqual(result.nodes.map(node=>node.name),['a AWG','Single TT']);
  const textOnly=await convertFiles([],source);
  assert.equal(textOnly.nodes[0].name,'Single TT');
  const pastedVpn=await convertFiles([],vpn(config()));
  assert.equal(pastedVpn.nodes[0].name,'Тест AWG');
});

test('TT duplicate identity and an invalid TT in a mixed set abort the full result',async()=>{
  const tt={type:'trusttunnel',name:'One',server:'tt.example.test',port:443,username:'synthetic',password:'synthetic'};
  await assert.rejects(convertFiles([file('set.json',JSON.stringify({proxies:[tt,{...tt,name:'Alias'}]}))]));
  await assert.rejects(convertFiles([file('a.conf',conf),file('bad.yaml',JSON.stringify({...tt,port:0}))]));
});

test('skipped protocol counts are accumulated across multiple Mihomo files',async()=>{
  const node={type:'trusttunnel',name:'One',server:'tt.example.test',port:443,username:'synthetic',password:'synthetic'};
  const result=await convertFiles([
    file('one.yaml',JSON.stringify({proxies:[{type:'ss'},node]})),
    file('two.yaml',JSON.stringify({proxies:[{type:'ss'},{...node,name:'Two',port:444}]})),
  ]);
  assert.match(result.notes.join(' '),/других протоколов: 2/);
});
