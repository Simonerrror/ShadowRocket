// Native inputs missing from the original form. No network or persistent storage.
import {parseDocument} from 'yaml';
const fail=()=>{throw new Error('Некорректный или неподдерживаемый вход.');};
const str=v=>{if(typeof v!=='string'||!v||/[\u0000-\u001f\u007f]/.test(v))fail();return v;};
const num=(v,max=65535)=>{if(!/^\d+$/.test(String(v))||!Number.isSafeInteger(+v)||+v>max)fail();return +v;};
const port=v=>{const n=num(v);if(!n)fail();return n;};
const key=v=>{str(v);if(!/^[A-Za-z0-9+/]{43}=$/.test(v)||atob(v).length!==32||btoa(atob(v))!==v)fail();return v;};
function ip(v){
  if(v.includes(':')){if(v.includes('%'))fail();try{new URL(`http://[${v}]/`);}catch{fail();}return 6;}
  const p=v.split('.');if(p.length!==4||p.some(x=>! /^(0|[1-9]\d{0,2})$/.test(x)||+x>255))fail();return 4;
}
function addresses(value){
  const result={};
  for(const entry of str(value).split(',')){
    const [addr,mask,...rest]=entry.trim().split('/'), family=ip(addr);
    if(rest.length)fail();if(mask!==undefined)num(mask,family===4?32:128);
    const field=family===4?'ip':'ipv6';if(result[field])fail();result[field]=addr;
  }
  return result;
}
function endpoint(value){
  const m=/^(\[[^\]]+\]|[A-Za-z0-9._-]+):(\d+)$/.exec(str(value));if(!m)fail();
  return {server:m[1].replace(/^\[|\]$/g,''),port:port(m[2])};
}
function wgFields(a,p,name){
  const node={name,type:'wireguard',...endpoint(p.Endpoint),...addresses(a.Address),'private-key':key(a.PrivateKey),'public-key':key(p.PublicKey),udp:true};
  if(p.PresharedKey)node['pre-shared-key']=key(p.PresharedKey);
  if(p.PersistentKeepalive!==undefined)node['persistent-keepalive']=num(p.PersistentKeepalive);
  if(a.MTU!==undefined){node.mtu=num(a.MTU);if(node.mtu<576)fail();}
  if(a.DNS){node.dns=a.DNS.split(',').map(v=>v.trim());node.dns.forEach(ip);node['remote-dns-resolve']=true;}
  return node;
}
export function wgConf(source,name){
  if(new TextEncoder().encode(source).length>65536)fail();
  const sections={};let section;
  for(const raw of source.replace(/^\uFEFF/,'').split(/\r?\n/)){
    const line=raw.trim();if(!line||/^[#;]/.test(line))continue;
    const h=/^\[(Interface|Peer)\]$/.exec(line);
    if(h){if(sections[h[1]])fail();section=sections[h[1]]={};continue;}
    const m=/^([A-Za-z]+)\s*=\s*(.+)$/.exec(line);if(!section||!m||Object.hasOwn(section,m[1]))fail();section[m[1]]=m[2].trim();
  }
  const a=sections.Interface,p=sections.Peer;if(!a||!p)fail();
  if(Object.keys(a).some(k=>!['PrivateKey','Address','DNS','MTU'].includes(k))||Object.keys(p).some(k=>!['PublicKey','PresharedKey','AllowedIPs','Endpoint','PersistentKeepalive'].includes(k)))fail();
  const allowed=str(p.AllowedIPs).split(',').map(v=>v.trim());
  if(!allowed.includes('0.0.0.0/0')||allowed.some(v=>!['0.0.0.0/0','::/0'].includes(v)))fail();
  return [wgFields(a,p,name.replace(/\.conf$/i,''))];
}
export function wgUri(raw){
  const u=new URL(raw);if(!['wg:','wireguard:'].includes(u.protocol)||u.password||(u.pathname&&u.pathname!=='/'))fail();
  const allowed=['privateKey','privatekey','publicKey','publickey','presharedKey','presharedkey','ip','address','dns','keepalive','mtu','reserved'];
  for(const k of u.searchParams.keys())if(!allowed.includes(k)||u.searchParams.getAll(k).length!==1)fail();
  const q=(...names)=>{const values=names.map(k=>u.searchParams.get(k)).filter(v=>v!==null);if(values.length>1)fail();return values[0];};
  const a={PrivateKey:q('privateKey','privatekey')||decodeURIComponent(u.username),Address:q('ip','address')};
  if(u.username&&q('privateKey','privatekey'))fail();
  for(const [field,value] of [['DNS',q('dns')],['MTU',q('mtu')]])if(value!==undefined)a[field]=value;
  const p={Endpoint:`${u.hostname}:${u.port}`,PublicKey:q('publicKey','publickey')};
  for(const [field,value] of [['PresharedKey',q('presharedKey','presharedkey')],['PersistentKeepalive',q('keepalive')]])if(value!==undefined)p[field]=value;
  const n=wgFields(a,p,decodeURIComponent(u.hash.slice(1))||'WG');
  if(q('reserved')){n.reserved=q('reserved').split(',').map(v=>num(v,255));if(n.reserved.length!==3)fail();}
  return [n];
}
export function mieruUri(raw){
  const u=new URL(raw);if(u.protocol!=='mierus:'||!u.hostname||u.port||(u.pathname&&u.pathname!=='/'))fail();
  const multi=['port','protocol'],single=['profile','multiplexing','handshake-mode','traffic-pattern','mtu'];
  for(const k of u.searchParams.keys())if(![...multi,...single].includes(k)||(!multi.includes(k)&&u.searchParams.getAll(k).length!==1))fail();
  // Mihomo's mieru v3.38.0 uses DefaultMTU=1400 and has no outbound MTU field.
  if(u.searchParams.has('mtu')&&u.searchParams.get('mtu')!=='1400')fail();
  const ports=u.searchParams.getAll('port'),transports=u.searchParams.getAll('protocol');if(!ports.length||ports.length!==transports.length)fail();
  return ports.map((v,i)=>{
    if(!['TCP','UDP'].includes(transports[i]))fail();
    const n={name:`${decodeURIComponent(u.hash.slice(1))||u.searchParams.get('profile')||'Mieru'} ${i+1}`,type:'mieru',server:u.hostname.replace(/^\[|\]$/g,''),username:str(decodeURIComponent(u.username)),password:str(decodeURIComponent(u.password)),transport:transports[i],udp:true};
    if(v.includes('-')){const m=/^(\d+)-(\d+)$/.exec(v);if(!m||port(m[1])>port(m[2]))fail();n['port-range']=v;}else n.port=port(v);
    for(const k of single.filter(k=>!['profile','mtu'].includes(k)))if(u.searchParams.has(k))n[k]=str(u.searchParams.get(k));
    return n;
  });
}
export function mihomoNodes(source){
  if(new TextEncoder().encode(source).length>2*1024*1024)fail();
  const doc=parseDocument(source,{schema:'core',uniqueKeys:true,maxDepth:40});if(doc.errors.length||doc.warnings.length)fail();
  const data=doc.toJS({maxAliasCount:0});if(!data||!Array.isArray(data.proxies)||!data.proxies.length)fail();
  const types=['vless','trojan','ss','hysteria2','openvpn','wireguard','trusttunnel','mieru'];
  return data.proxies.map(n=>{
    if(!n||typeof n!=='object'||!types.includes(n.type))fail();str(n.name);str(n.server);
    if(n.type==='mieru'&&n['port-range']){
      const m=/^(\d+)-(\d+)$/.exec(n['port-range']);if(n.port||!m||port(m[1])>port(m[2]))fail();
    }else port(n.port);
    for(const k of ({vless:['uuid'],trojan:['password'],ss:['cipher','password'],hysteria2:['password'],openvpn:[],wireguard:['private-key'],trusttunnel:['username','password'],mieru:['username','password','transport']})[n.type])str(n[k]);
    if(n.type==='openvpn'&&(typeof n.ca!=='string'||!n.ca.trim()||n.ca.includes('\0')))fail();
    if(n.type==='wireguard'){key(n['private-key']);if(n.peers){if(!Array.isArray(n.peers)||!n.peers.length)fail();}else key(n['public-key']);if(!n.ip&&!n.ipv6)fail();}
    if(n.type==='mieru'&&!['TCP','UDP'].includes(n.transport))fail();
    return {...n, ...(n.port!==undefined?{port:+n.port}:{})};
  });
}
export function openvpnConf(source,name){
  if(new TextEncoder().encode(source).length>2*1024*1024)fail();
  const blocks={};
  let content=source.replace(/<(ca|cert|key|tls-auth|tls-crypt|tls-crypt-v2|auth-user-pass)>\s*\r?\n([\s\S]*?)<\/\1>/gi,(_,tag,body)=>{tag=tag.toLowerCase();if(Object.hasOwn(blocks,tag))fail();blocks[tag]=body.trim()+'\n';return '';});
  if(!blocks.ca||!blocks.ca.includes('-----BEGIN CERTIFICATE-----'))fail();
  const n={name:name.replace(/\.ovpn$/i,''),type:'openvpn',udp:true,dev:'tun',...blocks};delete n['auth-user-pass'];
  if(blocks['auth-user-pass']){const lines=blocks['auth-user-pass'].trim().split(/\r?\n/);if(lines.length!==2)fail();n.username=str(lines[0]);n.password=str(lines[1]);}
  if(Boolean(n.cert)!==Boolean(n.key)||(!n.cert&&!n.username))fail();
  const remotes=[],seen=new Set();let proto='udp';
  const scalar={cipher:'cipher',auth:'auth','data-ciphers-fallback':'data-ciphers-fallback','key-direction':'key-direction','comp-lzo':'comp-lzo'};
  const numeric={'ping':'ping','ping-restart':'ping-restart','tun-mtu':'mtu','tran-window':'tran-window','hand-window':'handshake-timeout'};
  const local={client:0,'tls-client':0,nobind:0,'persist-key':0,'persist-tun':0,'auth-nocache':0,'mute-replay-warnings':0,'remote-random':0,verb:1,mute:1,'resolv-retry':1};
  const protocol=v=>{if(['tcp','tcp-client','tcp4','tcp4-client'].includes(v))return 'tcp';if(['udp','udp4'].includes(v))return 'udp';fail();};
  for(const raw of content.split(/\r?\n/)){
    const line=raw.trim();if(!line||/^[#;]/.test(line))continue;
    const tokens=line.match(/"[^"\r\n]*"|'[^'\r\n]*'|[^\s]+/g)?.map(v=>/^['"]/.test(v)?v.slice(1,-1):v);if(!tokens)fail();
    const [k,...args]=tokens;if(k==='remote'){if(args.length<1||args.length>3)fail();remotes.push({server:str(args[0]),port:port(args[1]||1194),...(args[2]?{proto:protocol(args[2])}:{})});continue;}
    if(seen.has(k)&&!Object.hasOwn(local,k))fail();seen.add(k);
    if(Object.hasOwn(local,k)){if(args.length!==local[k])fail();continue;}
    if(k==='remote-cert-tls'){if(args.length!==1||args[0]!=='server')fail();continue;}
    if(k==='dev'){if(args.length!==1||args[0]!=='tun')fail();continue;}
    if(k==='proto'){if(args.length!==1)fail();proto=protocol(args[0]);continue;}
    if(Object.hasOwn(scalar,k)){if(args.length!==1)fail();n[scalar[k]]=str(args[0]);continue;}
    if(Object.hasOwn(numeric,k)){if(args.length!==1)fail();n[numeric[k]]=num(args[0]);continue;}
    if(k==='data-ciphers'){if(args.length!==1)fail();n['data-ciphers']=args[0].split(':').map(str);continue;}
    if(k==='auth-user-pass'&&blocks[k]&&args.length===0)continue;
    fail();
  }
  if(!remotes.length)fail();
  const ciphers=['AES-128-GCM','AES-192-GCM','AES-256-GCM','AES-128-CBC','AES-192-CBC','AES-256-CBC','CHACHA20-POLY1305'];
  if(n.cipher&&!ciphers.includes(n.cipher)||n.auth&&!['MD5','SHA1','SHA256','SHA384','SHA512'].includes(n.auth)||n['data-ciphers']?.some(v=>!ciphers.includes(v)))fail();
  if(n['key-direction']&&!['0','1'].includes(n['key-direction']))fail();
  if(['tls-auth','tls-crypt','tls-crypt-v2'].filter(k=>n[k]).length>1)fail();
  return remotes.map((remote,i)=>({...n,proto,...remote,name:remotes.length===1?n.name:`${n.name} ${i+1}`}));
}
