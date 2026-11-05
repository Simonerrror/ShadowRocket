import {convertConf} from './converter.mjs';
import {inflateProfile, unpackProfileZip} from '../clash/src/archive.mjs';

const VPN_LIMIT = 2 * 1024 * 1024;
const TOTAL_LIMIT = 16 * 1024 * 1024;
const failInput = message => { throw new Error(message); };
const textBytes = text => new TextEncoder().encode(text).length;
function decodeText(data) {
  try { return new TextDecoder('utf-8', {fatal:true}).decode(data).trim(); }
  catch { failInput('Некорректный UTF-8 в профиле.'); }
}
function jsonObject(text) {
  let data;
  try { data = JSON.parse(text); } catch { failInput('Некорректный JSON Amnezia.'); }
  if (!data || typeof data !== 'object' || Array.isArray(data)) failInput('Некорректный контейнер Amnezia.');
  return data;
}
async function uncompressVpn(data) {
  if (data.byteLength < 6) failInput('Некорректный сжатый .vpn.');
  const expected = new DataView(data.buffer,data.byteOffset,data.byteLength).getUint32(0);
  if (!expected || expected > VPN_LIMIT) failInput('Распакованный .vpn должен быть не больше 2 МиБ.');
  const body = await inflateProfile(data.subarray(4), 'deflate', expected);
  if (body.length !== expected) failInput('Неверная длина сжатого .vpn.');
  return jsonObject(decodeText(body));
}
async function vpnData(data) {
  let text;
  try { text = new TextDecoder('utf-8', {fatal:true}).decode(data).trim(); } catch {}
  if (text?.startsWith('{')) return jsonObject(text);
  if (text && /^(?:vpn:\/\/)?[A-Za-z0-9_-]+={0,2}$/.test(text)) {
    const encoded = text.replace(/^vpn:\/\//, '').replace(/-/g,'+').replace(/_/g,'/');
    try { data = Uint8Array.from(atob(encoded),c=>c.charCodeAt(0)); }
    catch { failInput('Некорректная кодировка .vpn.'); }
    if (data[0] === 123) return jsonObject(decodeText(data));
  }
  return uncompressVpn(data);
}
async function vpnProfiles(data, filename) {
  const root = await vpnData(data);
  if (!Array.isArray(root.containers) || root.containers.length > 100) failInput('В .vpn нет допустимого списка контейнеров Amnezia.');
  const profiles=[];
  for (const container of root.containers) {
    if (!container || typeof container !== 'object' || !/^amnezia-awg(?:2)?$/.test(container.container)) continue;
    const value = container.awg?.last_config;
    const last = typeof value === 'string' ? jsonObject(value) : value;
    if (!last || typeof last.config !== 'string' || textBytes(last.config) > 65536)
      failInput('В .vpn нет готового клиентского AWG .conf. Экспортируйте подключение AWG, а не доступ к серверу.');
    const stem = typeof root.description === 'string' && root.description.trim()
      ? root.description.trim() : filename.replace(/\.vpn$/i,'');
    profiles.push({name:stem + (profiles.length ? ` ${profiles.length+1}` : '') + '.conf',text:last.config});
  }
  if (!profiles.length) failInput('В .vpn нет клиентских профилей AWG.');
  return profiles;
}

export async function convertFiles(files) {
  if (!files.length || files.length > 100) failInput('Добавьте файлы или текст .vpn: от 1 до 100 входов.');
  if (files.reduce((sum,file)=>sum+file.size,0) > TOTAL_LIMIT) failInput('Выбранный набор больше 16 МиБ.');
  const links=[], seen=new Set(); let expanded=0, configs=0;
  for (const [index,file] of files.entries()) {
    try {
      const limit = /\.zip$/i.test(file.name) ? 8*1024*1024 : /\.vpn$/i.test(file.name) ? VPN_LIMIT : 65536;
      if (!/\.(?:conf|vpn|zip)$/i.test(file.name) || file.size > limit)
        failInput('Нужны .conf до 64 КиБ, .vpn до 2 МиБ или ZIP до 8 МиБ.');
      let buffer;
      try { buffer = await file.arrayBuffer(); } catch { failInput('Не удалось прочитать файл.'); }
      if (buffer.byteLength > limit) failInput('Превышен размер файла.');
      const entries = /\.zip$/i.test(file.name)
        ? await unpackProfileZip(buffer,{extensions:/\.(?:conf|vpn)$/i,binary:true})
        : [{name:file.name,data:new Uint8Array(buffer)}];
      for (const entry of entries) {
        expanded += entry.data.byteLength;
        if (expanded > TOTAL_LIMIT) failInput('Распакованный набор больше 16 МиБ.');
        const profiles = /\.vpn$/i.test(entry.name) ? await vpnProfiles(entry.data,entry.name)
          : [{name:entry.name,text:decodeText(entry.data)}];
        for (const profile of profiles) {
          configs += textBytes(profile.text);
          if (configs > TOTAL_LIMIT || links.length >= 100) failInput('Допускается до 100 профилей и 16 МиБ конфигов.');
          const link = convertConf(profile.text,profile.name);
          const identity = link.split('#')[0];
          if (seen.has(identity)) failInput('Один AWG-профиль выбран несколько раз.');
          seen.add(identity); links.push(link);
        }
      }
    } catch (error) {
      // Only our converter messages can include field names; never echo parser input.
      const detail = error instanceof Error && !['SyntaxError','TypeError','RangeError'].includes(error.name)
        ? error.message : 'Некорректный профиль или архив.';
      failInput(`Файл ${index+1}: ${detail}`);
    }
  }
  return links;
}
