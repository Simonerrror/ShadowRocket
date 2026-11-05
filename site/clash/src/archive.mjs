// ZIP stays in memory. No extraction to disk; stored/deflated profile entries only.
function crc32(data) {
  let crc=0xffffffff;
  for(const byte of data) {crc^=byte; for(let i=0;i<8;i++) crc=(crc>>>1)^((crc&1)?0xedb88320:0);}
  return (crc^0xffffffff)>>>0;
}
// Bound actual output, not just the size declared by an untrusted container.
export async function inflateProfile(body, format, limit) {
  let reader;
  try {
    reader = new Blob([body]).stream().pipeThrough(new DecompressionStream(format)).getReader();
    const chunks=[]; let length=0;
    while (true) {
      const {done,value}=await reader.read(); if(done) break;
      length+=value.length;
      if(length>limit) { await reader.cancel(); throw new Error(); }
      chunks.push(value);
    }
    const result=new Uint8Array(length); let offset=0;
    for(const chunk of chunks) { result.set(chunk,offset); offset+=chunk.length; }
    return result;
  } catch {
    throw new Error('Не удалось распаковать профиль: проверьте файл, размер и поддержку сжатия в браузере.');
  } finally { reader?.releaseLock(); }
}
export async function unpackProfileZip(buffer, {extensions=/\.(?:conf|ovpn|ya?ml|json)$/i, binary=false} = {}) {
  const data=new Uint8Array(buffer), view=new DataView(data.buffer,data.byteOffset,data.byteLength);
  const fail=()=>{throw new Error('Некорректный ZIP: нужны файлы профилей без шифрования, до 100 файлов; размер распакованного набора — до 16 МиБ.');};
  if(data.length>8*1024*1024 || data.length<22) fail();
  let end=-1;
  for(let i=data.length-22;i>=Math.max(0,data.length-65557);i--) if(view.getUint32(i,true)===0x06054b50 && i+22+view.getUint16(i+20,true)===data.length) {end=i;break;}
  if(end<0 || view.getUint16(end+4,true)!==0 || view.getUint16(end+6,true)!==0) fail();
  const count=view.getUint16(end+10,true), size=view.getUint32(end+12,true), start=view.getUint32(end+16,true);
  if(!count || count>200 || view.getUint16(end+8,true)!==count || start+size!==end) fail();
  const result=[]; let offset=start,total=0;
  for(let n=0;n<count;n++) {
    if(offset+46>end || view.getUint32(offset,true)!==0x02014b50) fail();
    const flags=view.getUint16(offset+8,true), method=view.getUint16(offset+10,true), crc=view.getUint32(offset+16,true), compressed=view.getUint32(offset+20,true), raw=view.getUint32(offset+24,true), nameLen=view.getUint16(offset+28,true), extraLen=view.getUint16(offset+30,true), commentLen=view.getUint16(offset+32,true), local=view.getUint32(offset+42,true);
    if(offset+46+nameLen+extraLen+commentLen>end || view.getUint16(offset+34,true)!==0) fail();
    const name=new TextDecoder('utf-8',{fatal:true}).decode(data.slice(offset+46,offset+46+nameLen));
    offset+=46+nameLen+extraLen+commentLen;
    if(name.endsWith('/') || name.startsWith('__MACOSX/') || name.split('/').at(-1).startsWith('._') || name.split('/').at(-1)==='.DS_Store') continue;
    const entryLimit=/\.conf$/i.test(name)?65536:2*1024*1024;
    total+=raw;
    if(!extensions.test(name) || name.includes('..') || flags&1 || ![0,8].includes(method) || raw>entryLimit || total>16*1024*1024 || !raw || result.length>=100 || local+30>start || view.getUint32(local,true)!==0x04034b50) fail();
    const localName=view.getUint16(local+26,true), localExtra=view.getUint16(local+28,true), content=local+30+localName+localExtra;
    if(content+compressed>start || view.getUint16(local+8,true)!==method || view.getUint16(local+6,true)!==flags || new TextDecoder('utf-8',{fatal:true}).decode(data.slice(local+30,local+30+localName))!==name) fail();
    let body=data.slice(content,content+compressed);
    if(method===8) body=await inflateProfile(body, 'deflate-raw', Math.min(entryLimit,raw));
    if(body.length!==raw || crc32(body)!==crc) fail();
    result.push({name:name.split('/').at(-1), ...(binary ? {data:body} : {text:new TextDecoder('utf-8',{fatal:true}).decode(body)})});
  }
  if(offset!==end || !result.length) fail();
  return result;
}
