import {parseDocument} from 'yaml';
import {wgConf, wgUri, mieruUri, mihomoNodes, openvpnConf} from './protocols.mjs';
import {awgConfLink, awgProxy, ttProxies} from './protocol-converters.mjs';

const fail = message => {throw new Error(message);};
const bytes = text => new TextEncoder().encode(text).length;
function port(value) {if(!/^\d+$/.test(String(value)) || +value<1 || +value>65535) fail('Некорректный порт.'); return +value;}
function text(value) {if(typeof value!=='string' || !value || /[\u0000-\u001f\u007f]/.test(value)) fail('Не заполнено поле узла.'); return value;}
function bool(value) {if(['1','true'].includes(value)) return true; if(['0','false'].includes(value)) return false; fail('Некорректное логическое значение.');}
function base64(value) {const s=value.replace(/-/g,'+').replace(/_/g,'/'); return new TextDecoder('utf-8',{fatal:true}).decode(Uint8Array.from(atob(s),c=>c.charCodeAt(0)));}
function ttNodes(source) {
  if(bytes(source)>2*1024*1024) fail('TT-файл больше 2 МиБ.');
  const doc=parseDocument(source,{schema:'core',uniqueKeys:true,maxDepth:40});
  if(doc.errors.length || doc.warnings.length) fail('Некорректный YAML/JSON TrustTunnel.');
  const data=doc.toJS({maxAliasCount:0});
  if(!data || !Array.isArray(data.proxies) || !data.proxies.length) fail('В TT-файле нет массива proxies с узлами.');
  const allowed=['name','type','server','port','username','password','sni','alpn','skip-cert-verify','client-fingerprint','fingerprint','certificate','quic','congestion-controller','udp','health-check','tfo','mptcp','ip-version'];
  return data.proxies.map(p=>{
    if(!p || typeof p!=='object' || p.type!=='trusttunnel' || Object.keys(p).some(k=>!allowed.includes(k))) fail('TT-файл должен содержать только поддерживаемые узлы TrustTunnel.');
    for(const field of ['name','server','username','password']) text(p[field]);
    port(p.port);
    for(const field of ['sni','client-fingerprint','fingerprint','certificate','ip-version']) if(p[field]!==undefined) text(p[field]);
    for(const field of ['skip-cert-verify','quic','udp','health-check','tfo','mptcp']) if(p[field]!==undefined && typeof p[field]!=='boolean') fail('Некорректное логическое поле TT.');
    if(p.alpn!==undefined && (!Array.isArray(p.alpn) || p.alpn.some(v=>typeof v!=='string'))) fail('Некорректный ALPN TT.');
    return {...p,port:+p.port};
  });
}
function uriNode(raw) {
  if(raw.startsWith('awg://')) {
    const [encoded,...fragment]=raw.slice(6).split('#');
    if(!/^[A-Za-z0-9_-]+={0,2}$/.test(encoded)) fail('Некорректная ссылка AWG.');
    return [awgProxy(awgConfLink(base64(encoded), (decodeURIComponent(fragment.join('#')||'AWG')||'AWG')+'.conf'))];
  }
  if(raw.startsWith('wg://')) return new URL(raw).searchParams.has('obfs') ? [awgProxy(raw)] : wgUri(raw);
  if(raw.startsWith('wireguard://')) return wgUri(raw);
  if(raw.startsWith('mierus://')) return mieruUri(raw);
  if(raw.startsWith('tt://')) return ttProxies([raw]);
  let link=raw;
  if(link.startsWith('ss://') && !link.slice(5).split('#')[0].includes('@')) {
    const [body,...hash]=link.slice(5).split('#'); link='ss://'+base64(body)+(hash.length?'#'+hash.join('#'):'');
  }
  const u=new URL(link), scheme=u.protocol.slice(0,-1);
  if(!['vless','trojan','ss','hy2','hysteria2'].includes(scheme)) fail('Протокол не поддерживается.');
  if(!u.hostname || (u.pathname && u.pathname!=='/')) fail('Некорректный адрес узла.');
  const common=['sni','peer','alpn','insecure','allowInsecure','fp','security','type','host','path','serviceName','flow','pbk','sid','spx','encryption','headerType','packetEncoding','udp','mode'];
  const allowed=scheme==='ss'?[]:['hy2','hysteria2'].includes(scheme)?['sni','insecure','alpn','obfs','obfs-password','up','down']:common;
  for(const key of u.searchParams.keys()) if(!allowed.includes(key) || u.searchParams.getAll(key).length!==1) fail('Неизвестный или повторный параметр ссылки.');
  const q=key=>u.searchParams.get(key);
  const name=decodeURIComponent(u.hash.slice(1)) || scheme.toUpperCase();
  const p={name,type:['hy2','hysteria2'].includes(scheme)?'hysteria2':scheme,server:u.hostname.replace(/^\[|\]$/g,''),port:port(u.port || (['trojan','hy2','hysteria2'].includes(scheme)?443:'')),udp:true};
  if(scheme==='ss') {
    let auth=decodeURIComponent(u.username)+(u.password?':'+decodeURIComponent(u.password):'');
    if(!auth.includes(':')) auth=base64(auth);
    const i=auth.indexOf(':'); if(i<1) fail('Не заполнены cipher и пароль SS.');
    p.cipher=auth.slice(0,i); p.password=text(auth.slice(i+1)); return [p];
  }
  if(scheme==='vless') {
    p.uuid=decodeURIComponent(u.username); if(!/^[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12}$/i.test(p.uuid) || u.password) fail('Некорректный UUID VLESS.');
    if(q('encryption') && q('encryption')!=='none') fail('Поддерживается encryption=none.');
    const security=q('security')||'none'; if(!['none','tls','reality'].includes(security)) fail('Неизвестный режим TLS VLESS.');
    p.tls=security!=='none'; if(q('flow')) {if(q('flow')!=='xtls-rprx-vision') fail('Неизвестный flow VLESS.'); p.flow=q('flow');}
    if(security==='reality') {p['reality-opts']={'public-key':text(q('pbk'))}; if(q('sid')) {if(!/^(?:[\da-f]{2}){1,8}$/i.test(q('sid'))) fail('Некорректный short-id.'); p['reality-opts']['short-id']=q('sid');} if(q('spx')) p['reality-opts']['spider-x']=q('spx');}
    else if(q('pbk') || q('sid') || q('spx')) fail('Параметры Reality без security=reality.');
  } else {
    p.password=text(decodeURIComponent(u.username)+(u.password?':'+decodeURIComponent(u.password):''));
    if(scheme==='trojan' && q('security') && q('security')!=='tls') fail('Trojan требует TLS.');
  }
  if(q('sni') && q('peer') && q('sni')!==q('peer')) fail('Различаются sni и peer.');
  const sni=q('sni')||q('peer'); if(sni) p[scheme==='vless'?'servername':'sni']=sni;
  if(q('alpn')) p.alpn=q('alpn').split(',');
  const insecure=q('insecure')??q('allowInsecure');
  if(q('insecure')!==null && q('allowInsecure')!==null && bool(q('insecure'))!==bool(q('allowInsecure'))) fail('Различаются insecure и allowInsecure.');
  if(insecure!==null) p['skip-cert-verify']=bool(insecure);
  if(q('fp')) p['client-fingerprint']=q('fp');
  if(q('udp')!==null) p.udp=bool(q('udp'));
  if(p.type==='hysteria2') {
    if(q('obfs')) {if(q('obfs')!=='salamander') fail('Неизвестный obfs Hysteria2.'); p.obfs='salamander'; p['obfs-password']=text(q('obfs-password'));}
    else if(q('obfs-password')) fail('Пароль obfs без obfs.');
    for(const key of ['up','down']) if(q(key)) p[key]=q(key);
    return [p];
  }
  if(scheme==='trojan' && ['flow','pbk','sid','spx','encryption','packetEncoding'].some(k=>q(k)!==null)) fail('Параметр VLESS в ссылке Trojan.');
  if(q('headerType') && q('headerType')!=='none') fail('TCP headerType не поддерживается.');
  if(q('packetEncoding')) {if(!['xudp','packetaddr'].includes(q('packetEncoding'))) fail('Неизвестный packetEncoding.'); p[q('packetEncoding')==='xudp'?'xudp':'packet-addr']=true;}
  const network=q('type')||'tcp';
  if(!['tcp','ws','grpc','httpupgrade','xhttp'].includes(network)) fail('Транспорт ссылки не поддерживается.');
  if(network==='xhttp') {
    if(scheme!=='vless'||q('serviceName')||q('flow')) fail('Несовместимые параметры XHTTP.');
    const mode=q('mode')||'auto';if(!['auto','packet-up','stream-up','stream-one'].includes(mode)) fail('Неизвестный режим XHTTP.');
    p.network='xhttp';p['xhttp-opts']={host:q('host')||u.hostname,path:q('path')||'/',mode};
  } else if(q('mode')) fail('mode требует XHTTP.');
  if(network==='tcp' && ['host','path','serviceName'].some(k=>q(k)!==null)) fail('Параметры транспорта не соответствуют TCP.');
  if(network==='grpc') {if(q('host')||q('path')) fail('Параметры WS не соответствуют gRPC.'); p.network='grpc'; p['grpc-opts']={'grpc-service-name':q('serviceName')||''};}
  if(['ws','httpupgrade'].includes(network)) {
    if(q('serviceName')) fail('serviceName не соответствует WS.');
    p.network='ws'; p['ws-opts']={path:q('path')||'/'};
    if(q('host')) p['ws-opts'].headers={Host:q('host')};
    if(network==='httpupgrade') p['ws-opts']['v2ray-http-upgrade']=true;
  }
  return [p];
}
export function bonusProxies({ttFiles=[],awgFiles=[],wgFiles=[],ovpnFiles=[],mihomoFiles=[],links=''}) {
  if(ttFiles.length+awgFiles.length+wgFiles.length+ovpnFiles.length+mihomoFiles.length>100) fail('Допускается не более 100 файлов.');
  if(bytes(links)>1024*1024) fail('Поле ссылок больше 1 МиБ.');
  const proxies=[], keys=new Set();
  const add=(nodes,prefix)=>{
    for(const [i,p] of nodes.entries()) {
      if(p.type==='wireguard'&&p['private-key']) {
        const identity=JSON.stringify([p['private-key'],p.server,p.port,p['public-key'],p.ip,p.ipv6]);
        if(keys.has(identity)) fail('Один WG/AWG-профиль добавлен несколько раз.');
        keys.add(identity);
      }
      proxies.push({...p,name:`[${prefix}-${i+1}] ${p.name}`});
      if(proxies.length>500) fail('Допускается не более 500 дополнительных узлов.');
    }
  };
  for(const [i,f] of ttFiles.entries()) {try {add(ttNodes(f.text),`TT${i+1}`);} catch {fail(`TT-файл ${i+1}: проверьте формат Mihomo и параметры TrustTunnel.`);}}
  for(const [i,f] of awgFiles.entries()) {try {add([awgProxy(awgConfLink(f.text,f.name))],`AWG${i+1}`);} catch(error) {fail(`AWG-файл ${i+1}: ${error.message.startsWith('awg_')?'некорректные параметры AWG.':error.message}`);}}
  for(const [kind,files,convert] of [['WG',wgFiles,wgConf],['OpenVPN',ovpnFiles,openvpnConf],['Mihomo',mihomoFiles,mihomoNodes]]) {
    for(const [i,f] of files.entries()) {try {add(convert(f.text,f.name),`${kind}${i+1}`);} catch {fail(`${kind}-файл ${i+1}: проверьте формат и параметры профиля.`);}}
  }
  for(const [i,line] of links.split(/\r?\n/).entries()) {if(!line.trim()) continue; try {add(uriNode(line.trim()),`URI${i+1}`);} catch {fail(`Ссылка в строке ${i+1}: неверный формат, неизвестный параметр или неподдерживаемый протокол.`);}}
  return proxies;
}
