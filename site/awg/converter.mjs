import {shadowrocketName} from '../clash/src/protocol-converters.mjs';

// WG and AWG share connection validation and the Shadowrocket wg:// contract.
// Only pure conversion lives here; no I/O, storage, or network APIs.
const legacy = ['Jc','Jmin','Jmax','S1','S2','H1','H2','H3','H4'];
const awg2 = ['Jc','Jmin','Jmax','S1','S2','S3','S4','H1','H2','H3','H4','I1','I2','I3','I4','I5'];
const extended = {
  HeaderProtectionKey:'header_protection_key', ContentPaddingAddition:'content_padding_addition',
  RekeyAfterTime:'rekey_after_time', RekeyTimeout:'rekey_timeout', RejectAfterTime:'reject_after_time',
  KeepaliveTimeout:'keepalive_timeout', MaxHandshakeAttempts:'max_handshake_attempts',
  RandomTrailers:'random_trailers', DisableCookies:'disable_cookies',
};
const fail = field => { throw new Error(`Недопустимое значение поля ${field}.`); };
function uint(value, field, max = 4294967295) {
  if (!/^[0-9]+$/.test(value) || value.length > String(max).length || Number(value) > max)
    throw new Error(`В поле ${field} требуется целое число от 0 до ${max}.`);
  return Number(value);
}
function range(value, field, max = 65535) {
  if (!/^[0-9]+(?:-[0-9]+)?$/.test(value)) fail(field);
  const [low, high = low] = value.split('-');
  if (uint(low, field, max) > uint(high, field, max)) fail(field);
}
function key(value, field) {
  try { if (atob(value).length === 32 && btoa(atob(value)) === value) return; } catch {}
  fail(field);
}
function ip(value) {
  if (value.includes(':')) {
    if (!/^[0-9a-f:.]+$/i.test(value)) return 0;
    try { return new URL(`http://[${value}]/`).hostname.startsWith('[') ? 6 : 0; } catch { return 0; }
  }
  return /^(?:0|[1-9][0-9]{0,2})(?:\.(?:0|[1-9][0-9]{0,2})){3}$/.test(value)
    && value.split('.').every(n => Number(n) <= 255) ? 4 : 0;
}
function endpoint(value) {
  const match = /^(\[[^\]]+\]|[^:]+):([0-9]+)$/.exec(value);
  if (!match || uint(match[2], 'Endpoint', 65535) === 0) fail('Endpoint');
  const host = match[1];
  if (host.startsWith('[')) {
    if (ip(host.slice(1, -1)) !== 6) fail('Endpoint');
  } else if (host.length > 253 || host.split('.').some(part =>
    part.length > 63 || !/^[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?$/.test(part))) fail('Endpoint');
  return `${host}:${Number(match[2])}`;
}
function parse(text) {
  if (typeof text !== 'string' || new TextEncoder().encode(text).length > 65536)
    throw new Error('Размер .conf должен быть не больше 64 КиБ.');
  const sections = new Map();
  let section;
  for (const raw of text.replace(/^\uFEFF/, '').split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || /^[#;]/.test(line)) continue;
    if (line.startsWith('[')) {
      if (!['[Interface]', '[Peer]'].includes(line) || sections.has(line))
        throw new Error('Нужны одна секция [Interface] и одна [Peer].');
      section = new Map(); sections.set(line, section); continue;
    }
    const entry = /^([A-Za-z][A-Za-z0-9]*)\s*=\s*(.*)$/.exec(line);
    if (!section || !entry) throw new Error('Некорректный формат .conf.');
    const [, field, value] = entry;
    // Never include untrusted field names or values in errors.
    if (section.has(field)) throw new Error('В .conf повторяется поле.');
    if (!value || /\$(?:[A-Za-z_]|\{)/.test(value)) throw new Error('В .conf есть пустое значение или шаблон.');
    section.set(field, value);
  }
  if (sections.size !== 2) throw new Error('Нужны одна секция [Interface] и одна [Peer].');
  return [sections.get('[Interface]'), sections.get('[Peer]')];
}

export function convertConf(text, filename = 'profile.conf') {
  const [inter, peer] = parse(text);
  const allowedInterface = new Set(['PrivateKey','Address','DNS','MTU',...awg2,...Object.keys(extended)]);
  const allowedPeer = new Set(['PublicKey','PresharedKey','AllowedIPs','Endpoint','PersistentKeepalive']);
  if ([...inter.keys()].some(f => !allowedInterface.has(f)) || [...peer.keys()].some(f => !allowedPeer.has(f)))
    throw new Error('В .conf есть неподдерживаемое поле. Преобразование остановлено.');
  const isAwg = [...awg2,...Object.keys(extended)].some(f => inter.has(f));
  const isExtended = [...awg2.filter(f => !legacy.includes(f)),...Object.keys(extended)].some(f => inter.has(f));
  const fields = isExtended ? awg2 : isAwg ? legacy : [];
  const protocol = isAwg ? 'AWG' : 'WireGuard';
  for (const f of ['PrivateKey','Address',...fields]) if (!inter.has(f))
    throw new Error(`В профиле ${protocol} отсутствует обязательное поле ${f}.`);
  for (const f of ['PublicKey','AllowedIPs','Endpoint']) if (!peer.has(f))
    throw new Error(`В профиле ${protocol} отсутствует обязательное поле ${f}.`);
  key(inter.get('PrivateKey'), 'PrivateKey'); key(peer.get('PublicKey'), 'PublicKey');
  if (peer.has('PresharedKey')) key(peer.get('PresharedKey'), 'PresharedKey');
  if (isAwg) {
    uint(inter.get('Jc'), 'Jc');
    if (uint(inter.get('Jmin'), 'Jmin') > uint(inter.get('Jmax'), 'Jmax')) fail('Jmin/Jmax');
  }
  for (const f of fields.filter(f => f.startsWith('S'))) uint(inter.get(f), f, 65535);
  for (const f of fields.filter(f => f.startsWith('H'))) {
    if (isExtended) range(inter.get(f), f, 4294967295); else uint(inter.get(f), f);
  }
  for (const f of fields.filter(f => f.startsWith('I'))) {
    const value = inter.get(f);
    const tokens = value.match(/<(?:b 0x(?:[0-9a-fA-F]{2})+|(?:r|rc|rd) [0-9]+|t)>/g);
    if (!tokens || tokens.join('') !== value) fail(f);
    for (const token of tokens) {
      const count = /^<(?:r|rc|rd) ([0-9]+)>$/.exec(token);
      if (count) uint(count[1], f, 65535);
    }
  }
  for (const item of inter.get('Address').split(',')) {
    const [address, prefix, extra] = item.trim().split('/');
    const family = ip(address);
    if (!family || extra !== undefined) fail('Address');
    if (prefix !== undefined) uint(prefix, 'Address', family === 4 ? 32 : 128);
  }
  if (inter.has('DNS') && inter.get('DNS').split(',').some(value => !ip(value.trim()))) fail('DNS');
  const allowed = peer.get('AllowedIPs').split(',').map(value => value.trim());
  if (new Set(allowed).size !== allowed.length || !allowed.includes('0.0.0.0/0')
      || allowed.some(value => !['0.0.0.0/0','::/0'].includes(value)))
    throw new Error('AllowedIPs: ссылка поддерживает только полный туннель IPv4 или IPv4 + IPv6.');
  const obfs = Object.fromEntries(fields.map(f => [f.toLowerCase(), inter.get(f)]));
  for (const [field, mapped] of Object.entries(extended)) {
    if (!inter.has(field)) continue;
    let value = inter.get(field);
    if (field === 'HeaderProtectionKey') {
      key(value, field);
      if (['S1','S2','S3','S4'].some(f => Number(inter.get(f)) < 12)) fail('S1–S4');
    } else if (['RandomTrailers','DisableCookies'].includes(field)) {
      if (/^(on|true|1)$/i.test(value)) value = 'true';
      else if (/^(off|false|0)$/i.test(value)) value = 'false';
      else fail(field);
    } else range(value, field);
    obfs[mapped] = value;
  }
  const query = {publicKey:peer.get('PublicKey'), privateKey:inter.get('PrivateKey')};
  if (peer.has('PresharedKey')) query.presharedKey = peer.get('PresharedKey');
  query.ip = inter.get('Address');
  if (inter.has('DNS')) query.dns = inter.get('DNS');
  if (peer.has('PersistentKeepalive')) {
    uint(peer.get('PersistentKeepalive'), 'PersistentKeepalive', 65535);
    query.keepalive = peer.get('PersistentKeepalive');
  }
  if (isAwg) {
    query.obfs = 'amneziawg'; query.obfsParam = JSON.stringify(obfs);
  }
  if (inter.has('MTU')) { uint(inter.get('MTU'), 'MTU', 65535); query.mtu = inter.get('MTU'); }
  const version = !isAwg ? 'WG' : ['RandomTrailers','DisableCookies'].some(field => inter.has(field)) ? 'AWG3.1'
    : Object.keys(extended).some(field => inter.has(field)) ? 'AWG3' : isExtended ? 'AWG2' : 'AWG';
  const stem = String(filename).replace(/\.conf$/i, '').replace(/[\u0000-\u001f\u007f]/g, '').slice(0, 200) || 'profile';
  const flag = {nl:'🇳🇱',se:'🇸🇪',si:'🇸🇮'}[stem.split('_').at(-1).toLowerCase()];
  const title = shadowrocketName(`${flag ? flag + ' ' : ''}${stem}`, version);
  // Match the existing converter's percent encoding rather than form encoding.
  const encode = value => encodeURIComponent(value).replace(/[!'()*]/g, c => '%' + c.charCodeAt(0).toString(16).toUpperCase());
  return `wg://${endpoint(peer.get('Endpoint'))}?${Object.entries(query).map(([k,v]) => `${k}=${encode(v)}`).join('&')}#${encode(title)}`;
}
