import {parse,stringify} from 'yaml';
import {bonusProxies} from './inputs.mjs';
import {baseline} from '../generated/baseline.mjs';
export const geminiHosts = ['+.gemini.google.com', 'geminiweb-pa.clients6.google.com', 'waa-pa.clients6.google.com', 'ogads-pa.clients6.google.com'];
const sourceConfig=parse(baseline);
export const defaultDns = sourceConfig.dns.nameserver;
function httpsUrl(value, label) {
  if (typeof value !== 'string' || /[\s\u0000-\u001f\u007f]/u.test(value)) throw new Error(`${label}: укажите HTTPS-ссылку без пробелов.`);
  let url;
  try { url = new URL(value); } catch { throw new Error(`${label}: неверная ссылка.`); }
  if (url.protocol !== 'https:' || !url.hostname || url.username || url.password || value.includes('#')) throw new Error(`${label}: нужна HTTPS-ссылка без логина, пароля и фрагмента #.`);
  return value;
}
function relayIp(value) {
  const parts = value.split('.');
  if (parts.length !== 4 || parts.some(p => !/^(0|[1-9]\d{0,2})$/.test(p) || +p > 255) ||
      +parts[0] === 0 || +parts[0] === 10 || +parts[0] === 127 || +parts[0] >= 224 ||
      (+parts[0] === 169 && +parts[1] === 254) || (+parts[0] === 172 && +parts[1] >= 16 && +parts[1] <= 31) ||
      (+parts[0] === 192 && +parts[1] === 168) || (+parts[0] === 100 && +parts[1] >= 64 && +parts[1] <= 127)) throw new Error('IP релея: укажите внешний IPv4-адрес.');
  return value;
}
export function buildConfig({subscriptions = '', dns = '', smartDns = '', relay = '', ttFiles = [], awgFiles = [], wgFiles = [], ovpnFiles = [], mihomoFiles = [], links = ''}) {
  const urls = [...new Set(String(subscriptions).split(/\r?\n/).map(s => s.trim()).filter(Boolean))];
  const bonus = bonusProxies({ttFiles, awgFiles, wgFiles, ovpnFiles, mihomoFiles, links});
  if (!urls.length && !bonus.length) throw new Error('Добавьте хотя бы одну подписку, ссылку или файл протокола.');
  if (urls.length > 20) throw new Error('Допускается не более 20 подписок.');
  urls.forEach(url => httpsUrl(url, 'Подписка'));
  dns = dns.trim(); if(dns) dns = httpsUrl(dns, 'DNS'); smartDns = smartDns.trim(); relay = relay.trim();
  if (smartDns) httpsUrl(smartDns, 'Smart DNS');
  if (relay && !smartDns) throw new Error('Для IP релея укажите Smart DNS.');
  if (relay) relayIp(relay);
  const providerNames = urls.map((_, i) => `Sub-${i + 1}`);
  const config=parse(baseline);
  const sourceProvider=config['proxy-providers']['Main-Sub'];
  const healthCheck=sourceProvider['health-check'];
  config['proxy-providers']=Object.fromEntries(urls.map((url,i)=>[providerNames[i],{
    ...sourceProvider, url, path:`./proxies/sub-${i+1}.yaml`,
    override:{...sourceProvider.override,'additional-prefix':`[${i+1}] `},
    'health-check':{...healthCheck},
  }]));
  if(bonus.length) {
    providerNames.push('Bonus');
    config['proxy-providers'].Bonus={type:'inline','health-check':{...healthCheck},payload:bonus};
  }
  const {filter,proxies,...auto}=config['proxy-groups'].find(group=>group.name==='Режим');
  config['proxy-groups']=[{...auto,use:providerNames}];
  if(dns) config.dns.nameserver=[dns];
  if(smartDns) {
    config.dns['fake-ip-filter']=[...new Set([...config.dns['fake-ip-filter'],...geminiHosts])];
    config.dns['nameserver-policy']={...config.dns['nameserver-policy'],
      ...Object.fromEntries(geminiHosts.map(host=>[host,`${smartDns}#Режим`]))};
    if(relay) config.hosts={...config.hosts,...Object.fromEntries(geminiHosts.map(host=>[host,relay]))};
    const rules=['DOMAIN-SUFFIX,gemini.google.com,Режим',...geminiHosts.slice(1).map(host=>`DOMAIN,${host},Режим`)];
    config.rules=[...rules,...config.rules];
  }
  return '# FLCLASH / MIHOMO CONFIG\n'+stringify(config,{lineWidth:0});

}
