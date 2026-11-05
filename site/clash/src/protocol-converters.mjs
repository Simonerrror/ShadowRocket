// Browser adapter of convert_awg_conf.py: same accepted INI fields and wg:// contract.
const numeric = ['Jc','Jmin','Jmax','S1','S2','S3','S4'];
const strings = ['H1','H2','H3','H4','I1','I2','I3','I4','I5'];
const extra = {HeaderProtectionKey:'header_protection_key',ContentPaddingAddition:'content_padding_addition',RekeyAfterTime:'rekey_after_time',RekeyTimeout:'rekey_timeout',RejectAfterTime:'reject_after_time',KeepaliveTimeout:'keepalive_timeout',MaxHandshakeAttempts:'max_handshake_attempts',RandomTrailers:'random_trailers',DisableCookies:'disable_cookies'};
const requiredI = ['Address','DNS','PrivateKey',...numeric,...strings];
const requiredP = ['PublicKey','PresharedKey','AllowedIPs','Endpoint','PersistentKeepalive'];
const fail = message => { throw new Error(message); };
function uint(value, max = 4294967295) {
  if (!/^\d+$/.test(value) || !Number.isSafeInteger(+value) || +value > max) fail('Некорректное числовое поле AWG.');
  return +value;
}
function range(value, max) {
  const m = /^(\d+)(?:-(\d+))?$/.exec(value);
  if (!m || uint(m[1],max) > uint(m[2] ?? m[1],max)) fail('Некорректный диапазон AWG.');
}
function key(value) {
  if (!/^[A-Za-z0-9+/]{43}=$/.test(value) || atob(value).length !== 32 || btoa(atob(value)) !== value) fail('Некорректный ключ AWG.');
}
function ip(value) {
  if (value.includes(':')) {
    try { if (value.includes('%')) fail('IPv6'); new URL(`http://[${value}]/`); return 6; } catch { fail('Некорректный IPv6 AWG.'); }
  }
  const p = value.split('.');
  if (p.length !== 4 || p.some(s => !/^(0|[1-9]\d{0,2})$/.test(s) || +s > 255)) fail('Некорректный IPv4 AWG.');
  return 4;
}
// These final tokens are consumed by Shadowrocket policy filters.
export function shadowrocketName(value, protocol) {
  const base = String(value).trim().replace(/(?:(?:^|[\s_-]+)(?:(?:AWG|AVG)(?:[0-9]+(?:\.[0-9]+)?)?|TT|NV|Naive))+$/i, '').trim();
  return `${base || 'Узел'} ${protocol}`;
}

export function awgConfLink(text, filename) {
  if (new TextEncoder().encode(text).length > 65536) fail('AWG-файл больше 64 КиБ.');
  const sections = Object.create(null); let section;
  for (const line of text.replace(/^\uFEFF/,'').split(/\r?\n/)) {
    const s = line.trim(); if (!s || /^[#;]/.test(s)) continue;
    const h = /^\[(Interface|Peer)\]$/.exec(s);
    if (h) { if (sections[h[1]]) fail('Повторный раздел AWG.'); section = sections[h[1]] = Object.create(null); continue; }
    const m = /^([A-Za-z][A-Za-z0-9]*)\s*=\s*(.*)$/.exec(s);
    if (!section || !m || Object.hasOwn(section,m[1])) fail('Некорректная структура AWG.');
    section[m[1]] = m[2].trim();
  }
  const a = sections.Interface, p = sections.Peer;
  if (!a || !p || Object.keys(a).some(k=>![...requiredI,'MTU',...Object.keys(extra)].includes(k)) || Object.keys(p).some(k=>!requiredP.includes(k))) fail('Неизвестное поле или раздел AWG.');
  const extended = ['S3','S4',...strings.slice(4),...Object.keys(extra)].some(k=>Object.hasOwn(a,k));
  const fields = extended ? requiredI : requiredI.filter(k=>!['S3','S4',...strings.slice(4)].includes(k));
  for (const [section, keys] of [[a,fields],[p,requiredP]]) for (const field of keys) if (!section[field] || /\$(?:[A-Za-z_]|\{)/.test(section[field])) fail('Не заполнено обязательное поле AWG.');
  for (const field of numeric.filter(k=>Object.hasOwn(a,k))) uint(a[field],field.startsWith('S')?65535:4294967295);
  if (+a.Jmin > +a.Jmax) fail('Jmin больше Jmax.');
  for (const field of strings.slice(0,4)) extended ? range(a[field],4294967295) : uint(a[field]);
  for (const field of strings.slice(4).filter(k=>Object.hasOwn(a,k))) {
    const tokens = a[field].match(/<(?:b 0x(?:[0-9A-Fa-f]{2})+|(?:r|rc|rd) [0-9]+|t)>/g);
    if (!tokens || tokens.join('') !== a[field]) fail('Некорректная инструкция AWG.');
    for (const token of tokens) {const m = /^<(?:r|rc|rd) (\d+)>$/.exec(token); if(m) uint(m[1],65535);}
  }
  for (const value of [a.PrivateKey,p.PublicKey,p.PresharedKey]) key(value);
  for (const value of a.Address.split(',')) {
    const [address,prefix,...rest] = value.trim().split('/'); const family = ip(address);
    if (rest.length || prefix === undefined) fail('Некорректная маска AWG.');
    uint(prefix,family === 4?32:128);
  }
  for (const value of a.DNS.split(',')) ip(value.trim());
  const allowed = p.AllowedIPs.split(',').map(v=>v.trim());
  if (!allowed.includes('0.0.0.0/0') || allowed.some(v=>!['0.0.0.0/0','::/0'].includes(v)) || new Set(allowed).size !== allowed.length) fail('AWG: поддерживается AllowedIPs 0.0.0.0/0 и необязательный ::/0.');
  const endpoint = /^(\[[^\]]+\]|[A-Za-z0-9.-]+):(\d+)$/.exec(p.Endpoint);
  if (!endpoint || !uint(endpoint[2],65535)) fail('Некорректный Endpoint AWG.');
  if (endpoint[1].startsWith('[')) ip(endpoint[1].slice(1,-1));
  else if (endpoint[1].length > 253 || endpoint[1].split('.').some(v=>!v || v.length>63 || !/^[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?$/.test(v))) fail('Некорректный хост AWG.');
  uint(p.PersistentKeepalive,65535);
  const obfs = Object.fromEntries([...numeric,...strings].filter(k=>Object.hasOwn(a,k)).map(k=>[k.toLowerCase(),a[k]]));
  for (const [field,target] of Object.entries(extra)) if (Object.hasOwn(a,field)) {
    let v = a[field]; if (!v || /\$(?:[A-Za-z_]|\{)/.test(v)) fail('Не заполнено поле AWG.');
    if (field === 'HeaderProtectionKey') {key(v); if(['S1','S2','S3','S4'].some(k=>+a[k]<12)) fail('С HeaderProtectionKey значения S1–S4 должны быть не меньше 12.');}
    else if (['RandomTrailers','DisableCookies'].includes(field)) {
      v=v.toLowerCase(); if(['on','true','1'].includes(v)) v='true'; else if(['off','false','0'].includes(v)) v='false'; else fail('Некорректное логическое поле AWG.');
    } else range(v,65535);
    obfs[target]=v;
  }
  const query = new URLSearchParams({publicKey:p.PublicKey,privateKey:a.PrivateKey,presharedKey:p.PresharedKey,ip:a.Address,dns:a.DNS,keepalive:p.PersistentKeepalive,obfs:'amneziawg',obfsParam:JSON.stringify(obfs)});
  if (Object.hasOwn(a,'MTU')) { if(uint(a.MTU,65535)<576) fail('Некорректный MTU AWG.'); query.set('mtu',a.MTU); }
  const version = ['RandomTrailers','DisableCookies'].some(k=>Object.hasOwn(a,k))?'AWG3.1':Object.keys(extra).some(k=>Object.hasOwn(a,k))?'AWG3':extended?'AWG2':'AWG';
  return `wg://${endpoint[1]}:${endpoint[2]}?${query}#${encodeURIComponent(filename.replace(/\.conf$/i,'')+' '+version)}`;
}

function decodeBase64Bytes(value) {
  const compact = value.replace(/\s+/g, '');
  if (!compact || !/^[A-Za-z0-9+/_=-]+$/.test(compact)) return null;
  const normalized = compact.replace(/-/g, '+').replace(/_/g, '/');
  const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, '=');
  try {
    return Uint8Array.from(atob(padded), character => character.charCodeAt(0));
  } catch {
    return null;
  }
}

function readQuicVarint(bytes, offset) {
  if (offset >= bytes.length) throw new Error('tt_tlv_truncated');
  const size = 1 << (bytes[offset] >> 6);
  if (offset + size > bytes.length) throw new Error('tt_tlv_truncated');
  let value = BigInt(bytes[offset] & 0x3f);
  for (let index = 1; index < size; index += 1) value = (value << 8n) | BigInt(bytes[offset + index]);
  if (value > BigInt(Number.MAX_SAFE_INTEGER)) throw new Error('tt_tlv_too_large');
  return {value: Number(value), next: offset + size};
}

function decodeTtLink(link) {
  const opaque = link.slice('tt://'.length).replace(/^\?/, '').split('#', 1)[0];
  const bytes = decodeBase64Bytes(opaque);
  if (bytes === null) throw new Error('tt_payload_invalid');
  const decoder = new TextDecoder('utf-8', {fatal: true});
  const fields = new Map();
  let offset = 0;
  while (offset < bytes.length) {
    const tag = readQuicVarint(bytes, offset);
    const length = readQuicVarint(bytes, tag.next);
    const end = length.next + length.value;
    if (end > bytes.length) throw new Error('tt_tlv_truncated');
    const values = fields.get(tag.value) ?? [];
    values.push(bytes.slice(length.next, end));
    fields.set(tag.value, values);
    offset = end;
  }

  const lastText = tag => {
    const values = fields.get(tag);
    return values?.length ? decoder.decode(values.at(-1)) : null;
  };
  const lastBool = (tag, fallback) => {
    const values = fields.get(tag);
    if (!values?.length) return fallback;
    const value = values.at(-1);
    if (value.length !== 1 || (value[0] !== 0 && value[0] !== 1)) throw new Error('tt_bool_invalid');
    return value[0] === 1;
  };
  const lastVarint = (tag, fallback) => {
    const values = fields.get(tag);
    if (!values?.length) return fallback;
    const value = values.at(-1);
    const parsed = readQuicVarint(value, 0);
    if (parsed.next !== value.length) throw new Error('tt_varint_invalid');
    return parsed.value;
  };

  const version = lastVarint(0, 0);
  const hostname = lastText(1);
  const addresses = (fields.get(2) ?? []).map(value => decoder.decode(value));
  const username = lastText(5);
  const password = lastText(6);
  if (version > 1) throw new Error('tt_version_unsupported');
  if (!hostname || addresses.length === 0 || !username || !password) throw new Error('tt_required_field_missing');
  if ((fields.get(8) ?? []).length > 0) throw new Error('tt_certificate_unsupported');
  if (lastBool(10, false)) throw new Error('tt_anti_dpi_unsupported');
  if (lastText(11)) throw new Error('tt_random_prefix_unsupported');
  return {
    hostname,
    addresses,
    customSni: lastText(3),
    username,
    password,
    skipCertVerify: lastBool(7, false),
    upstreamProtocol: lastVarint(9, 1),
    name: lastText(12),
  };
}

function splitAddress(value) {
  if (value.startsWith('[')) {
    const close = value.indexOf(']');
    if (close < 0 || value[close + 1] !== ':') throw new Error('tt_address_invalid');
    return {host: value.slice(1, close), port: value.slice(close + 2)};
  }
  const separator = value.lastIndexOf(':');
  if (separator <= 0) throw new Error('tt_address_invalid');
  return {host: value.slice(0, separator), port: value.slice(separator + 1)};
}

export function ttProxies(links) {
  const proxies = [];
  for (const [linkIndex, link] of links.entries()) {
    const tt = decodeTtLink(link);
    if (tt.upstreamProtocol !== 1 && tt.upstreamProtocol !== 2) throw new Error('tt_upstream_protocol_unsupported');
    for (const [addressIndex, address] of tt.addresses.entries()) {
      const {host, port: rawPort} = splitAddress(address);
      const port = Number(rawPort);
      if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('tt_address_invalid');
      const baseName = tt.name || `TT ${linkIndex + 1}`;
      const name = tt.addresses.length === 1 ? baseName : `${baseName} ${addressIndex + 1}`;
      proxies.push({...tt, host, port, name});
    }
  }
  if (proxies.length === 0) throw new Error('tt_feed_empty');
  if (new Set(proxies.map(({name}) => name)).size !== proxies.length) throw new Error('tt_name_duplicate');
  return proxies.map(proxy => ({
    name: proxy.name,
    type: 'trusttunnel',
    server: proxy.host,
    port: proxy.port,
    username: proxy.username,
    password: proxy.password,
    'client-fingerprint': 'chrome',
    'health-check': true,
    udp: true,
    sni: proxy.customSni || proxy.hostname,
    'skip-cert-verify': proxy.skipCertVerify,
    ...(proxy.upstreamProtocol === 2 ? {quic: true} : {alpn: ['h2']}),
  }));
}

function awgInteger(value, min, max, error) {
  if (!/^\d+$/.test(value || '')) throw new Error(error);
  const number = Number(value);
  if (!Number.isSafeInteger(number) || number < min || number > max) throw new Error(error);
  return number;
}

function checkedParams(url, allowed, error) {
  for (const key of url.searchParams.keys()) if (!allowed.includes(key)) throw new Error(error);
}

function oneParam(url, key, required = true) {
  const values = url.searchParams.getAll(key);
  if (values.length > 1 || (required && (!values.length || !values[0]))) throw new Error('parameter_invalid');
  return values[0];
}

function awgKey(value) {
  if (!value || !/^[A-Za-z0-9+/]{43}=$/.test(value) || atob(value).length !== 32) throw new Error('awg_key_invalid');
  return value;
}

export function awgProxy(link) {
  const url = new URL(link);
  checkedParams(url, ['publicKey', 'privateKey', 'presharedKey', 'ip', 'dns', 'keepalive', 'obfs', 'obfsParam', 'mtu'], 'awg_parameter_unsupported');
  if (oneParam(url, 'obfs') !== 'amneziawg') throw new Error('awg_obfs_unsupported');
  const server = url.hostname.replace(/^\[|\]$/g, '');
  const name = decodeURIComponent(url.hash.slice(1));
  if (!server || !name) throw new Error('awg_required_field_missing');
  const options = JSON.parse(oneParam(url, 'obfsParam'));
  const numeric = ['jc', 'jmin', 'jmax', 's1', 's2', 's3', 's4'];
  const strings = ['h1', 'h2', 'h3', 'h4', 'i1', 'i2', 'i3', 'i4', 'i5'];
  const v3 = ['header_protection_key', 'content_padding_addition', 'rekey_after_time', 'rekey_timeout', 'reject_after_time', 'keepalive_timeout', 'max_handshake_attempts', 'random_trailers', 'disable_cookies'];
  const allowed = [...numeric, ...strings, ...v3];
  if (!options || Array.isArray(options) || typeof options !== 'object' || Object.keys(options).some(key => !allowed.includes(key))) throw new Error('awg_obfs_parameter_unsupported');
  const extended = ['s3', 's4', ...strings.slice(4), ...v3].some(key => Object.hasOwn(options, key));
  const obfs = {version: v3.some(key => Object.hasOwn(options, key)) ? 3 : extended ? 2 : 1};
  for (const [key, rawValue] of Object.entries(options)) {
    const value = String(rawValue), target = key.replaceAll('_', '-');
    if (numeric.includes(key)) obfs[target] = awgInteger(value, 0, key.startsWith('s') ? 65535 : 4294967295, 'awg_obfs_invalid');
    else if (['random_trailers', 'disable_cookies'].includes(key)) {
      if (!['true', 'false'].includes(value)) throw new Error('awg_bool_invalid');
      obfs[target] = value === 'true';
    } else obfs[target] = key === 'header_protection_key' ? awgKey(value) : value;
  }
  const required = extended ? [...numeric, ...strings] : ['jc', 'jmin', 'jmax', 's1', 's2', 'h1', 'h2', 'h3', 'h4'];
  for (const key of required) if (!Object.hasOwn(obfs, key)) throw new Error('awg_obfs_required_field_missing');
  const addresses = oneParam(url, 'ip').split(',').map(value => value.trim().split('/')[0]);
  const ip = addresses.find(value => !value.includes(':'));
  const ipv6 = addresses.find(value => value.includes(':'));
  if (!ip && !ipv6) throw new Error('awg_address_missing');
  const dns = oneParam(url, 'dns').split(',').map(value => value.trim());
  const mtu = oneParam(url, 'mtu', false);
  return {
    name,
    type: 'wireguard',
    server,
    port: awgInteger(url.port, 1, 65535, 'awg_port_invalid'),
    'private-key': awgKey(oneParam(url, 'privateKey')),
    'public-key': awgKey(oneParam(url, 'publicKey')),
    'pre-shared-key': awgKey(oneParam(url, 'presharedKey')),
    ...(ip ? {ip} : {}),
    ...(ipv6 ? {ipv6} : {}),
    dns,
    'remote-dns-resolve': true,
    'persistent-keepalive': awgInteger(oneParam(url, 'keepalive'), 0, 65535, 'awg_keepalive_invalid'),
    ...(mtu ? {mtu: awgInteger(mtu, 576, 65535, 'awg_mtu_invalid')} : {}),
    udp: true,
    'amnezia-wg-option': obfs,
  };
}
