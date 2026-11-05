import {parseDocument} from 'yaml';
import {shadowrocketName} from './protocol-converters.mjs';

// Static v1 TLV layout matches the maintained Shadowrocket TT converter.
const nonwire = ['client-fingerprint','health-check','udp'];
const allowed = new Set(['type','name','server','port','username','password','sni',
  'skip-cert-verify','alpn','has-ipv6','quic',...nonwire]);
const reject = message => { throw new Error(message); };
function string(value, field) {
  if(typeof value!=='string' || !value.trim() || /[\u0000-\u001f\u007f]/.test(value))
    reject(`TrustTunnel: проверьте ${field}.`);
  return value;
}
function boolean(value, field, fallback=false) {
  if(value===undefined) return fallback;
  if(typeof value!=='boolean') reject(`TrustTunnel: проверьте ${field}.`);
  return value;
}
function hostname(value, field) {
  let host=string(value,field).trim();
  if(host.startsWith('[') || host.endsWith(']')) {
    if(!host.startsWith('[') || !host.endsWith(']') || !host.includes(':')) reject(`TrustTunnel: проверьте ${field}.`);
    host=host.slice(1,-1);
  }
  if(host.includes(':')) {
    if(!/^[0-9a-f:.]+$/i.test(host)) reject(`TrustTunnel: проверьте ${field}.`);
    try { new URL(`https://[${host}]/`); } catch { reject(`TrustTunnel: проверьте ${field}.`); }
  } else if(host.length>253 || host.split('.').some(part=>part.length>63 || !/^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/i.test(part)))
    reject(`TrustTunnel: проверьте ${field}.`);
  return host;
}
function varint(value) {
  const size=value<64?1:value<16384?2:4;
  const bytes=new Uint8Array(size), view=new DataView(bytes.buffer);
  if(size===1) bytes[0]=value;
  else if(size===2) view.setUint16(0,value|0x4000);
  else view.setUint32(0,value|0x80000000);
  return bytes;
}
function tlv(tag, value) {
  const bytes=typeof value==='string'?new TextEncoder().encode(value):value;
  return new Uint8Array([...varint(tag),...varint(bytes.length),...bytes]);
}
function base64url(fields) {
  const length=fields.reduce((sum,field)=>sum+field.length,0), data=new Uint8Array(length);
  let offset=0;for(const field of fields){data.set(field,offset);offset+=field.length;}
  let binary='';for(let i=0;i<data.length;i+=32768) binary+=String.fromCharCode(...data.subarray(i,i+32768));
  return btoa(binary).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
}
function encodeNode(proxy) {
  if(Object.keys(proxy).some(key=>!allowed.has(key))) reject('TrustTunnel: есть поле, которое нельзя перенести в TT-ссылку.');
  const name=shadowrocketName(string(proxy.name,'name'),'TT');
  const server=hostname(proxy.server,'server');
  const port=Number(proxy.port);
  if(!/^[0-9]+$/.test(String(proxy.port)) || !Number.isInteger(port) || port<1 || port>65535) reject('TrustTunnel: проверьте port.');
  const username=string(proxy.username,'username'), password=string(proxy.password,'password');
  const sni=proxy.sni===undefined?server:hostname(proxy.sni,'sni');
  const skip=boolean(proxy['skip-cert-verify'],'skip-cert-verify');
  const quic=boolean(proxy.quic,'quic');
  const alpn=proxy.alpn??['h2'];
  if(!Array.isArray(alpn) || !alpn.length || alpn.some(value=>typeof value!=='string' || !['h2','h3','http/3','http3'].includes(value.toLowerCase())))
    reject('TrustTunnel: ALPN нельзя перенести в TT-ссылку.');
  const h3=quic || alpn.some(value=>value.toLowerCase()!=='h2');
  for(const field of ['udp','health-check']) if(proxy[field]!==undefined) boolean(proxy[field],field);
  if(proxy['client-fingerprint']!==undefined) string(proxy['client-fingerprint'],'client-fingerprint');
  const fields=[tlv(0,varint(1)),tlv(1,sni),tlv(2,`${server.includes(':')?'['+server+']':server}:${port}`),tlv(3,sni)];
  if(proxy['has-ipv6']!==undefined) fields.push(tlv(4,new Uint8Array([+boolean(proxy['has-ipv6'],'has-ipv6')])));
  fields.push(tlv(5,username),tlv(6,password));
  if(skip) fields.push(tlv(7,new Uint8Array([1])));
  if(h3) fields.push(tlv(9,varint(2)));
  const identity='tt:'+base64url(fields);
  fields.push(tlv(12,name));
  return {name,link:'tt://?'+base64url(fields),identity};
}

export function trustTunnelNodes(source) {
  if(typeof source!=='string' || new TextEncoder().encode(source).length>2*1024*1024)
    reject('Конфиг Mihomo должен быть не больше 2 МиБ.');
  let root;
  try {
    const doc=parseDocument(source,{schema:'core',uniqueKeys:true,merge:true});
    if(doc.errors.length || doc.warnings.length) throw new Error();
    root=doc.toJS({maxAliasCount:100});
  } catch { reject('Не удалось прочитать YAML/JSON Mihomo. Проверьте структуру и повторяющиеся поля.'); }
  if(!root || typeof root!=='object' || Array.isArray(root)) reject('Нужен конфиг Mihomo с proxies или описание одного TrustTunnel.');
  const proxies=root.type==='trusttunnel'?[root]:root.proxies;
  if(!Array.isArray(proxies)) reject('В конфиге нет proxies. Удалённые провайдеры не загружаются: добавьте их скачанный YAML.');
  const selected=proxies.filter(proxy=>proxy && typeof proxy==='object' && proxy.type==='trusttunnel');
  if(!selected.length || selected.length>100) reject('В proxies нужно от 1 до 100 узлов TrustTunnel.');
  const nodes=selected.map(encodeNode), notes=[];
  const omitted=nonwire.filter(field=>selected.some(proxy=>Object.hasOwn(proxy,field)));
  if(omitted.length) notes.push(`Без эквивалента в TT-ссылке: ${omitted.join(', ')}.`);
  if(root['proxy-providers']) notes.push('Удалённые провайдеры не загружались.');
  return {nodes,notes,skipped:proxies.length-nodes.length};
}
