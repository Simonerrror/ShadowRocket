import {test} from 'node:test';
import assert from 'node:assert/strict';
import {convertConf} from '../converter.mjs';

const key = n => btoa(String.fromCharCode(...Array(32).fill(n)));
const profile = `[Interface]
PrivateKey = ${key(1)}
Address = 10.8.0.2/32, fd00::2/128
DNS = 1.1.1.1, 2606:4700:4700::1111
MTU = 1280
Jc = 4
Jmin = 40
Jmax = 70
S1 = 12
S2 = 13
S3 = 14
S4 = 15
H1 = 1-3
H2 = 4
H3 = 5
H4 = 6
I1 = <t>
I2 = <r 15>
I3 = <rc 10>
I4 = <rd 4>
I5 = <b 0x1234>
[Peer]
PublicKey = ${key(2)}
PresharedKey = ${key(3)}
AllowedIPs = 0.0.0.0/0, ::/0
Endpoint = vpn.example.test:51820
PersistentKeepalive = 25
`;

test('AWG2 link preserves keys, IPs and obfuscation with a Unicode title', () => {
  const link = new URL(convertConf('\uFEFF' + profile.replaceAll('\n', '\r\n'), 'Тест_nl.conf'));
  assert.equal(link.protocol, 'wg:');
  assert.equal(link.host, 'vpn.example.test:51820');
  assert.equal(link.searchParams.get('privateKey'), key(1));
  assert.equal(link.searchParams.get('publicKey'), key(2));
  assert.equal(link.searchParams.get('presharedKey'), key(3));
  assert.equal(link.searchParams.get('ip'), '10.8.0.2/32, fd00::2/128');
  assert.equal(link.searchParams.get('dns'), '1.1.1.1, 2606:4700:4700::1111');
  assert.equal(link.searchParams.get('keepalive'), '25');
  assert.equal(link.searchParams.get('mtu'), '1280');
  assert.equal(link.searchParams.get('obfs'), 'amneziawg');
  assert.deepEqual(JSON.parse(link.searchParams.get('obfsParam')), {
    jc:'4', jmin:'40', jmax:'70', s1:'12', s2:'13', s3:'14', s4:'15',
    h1:'1-3', h2:'4', h3:'5', h4:'6', i1:'<t>', i2:'<r 15>', i3:'<rc 10>', i4:'<rd 4>', i5:'<b 0x1234>',
  });
  assert.equal(decodeURIComponent(link.hash.slice(1)), '🇳🇱 Тест_nl AWG');
});

test('AWG1 retains its fields without invented AWG2 fields', () => {
  const legacy = profile.replace(/^S[34] = .*\n|^I[1-5] = .*\n/gm, '').replace('H1 = 1-3', 'H1 = 3');
  const link = new URL(convertConf(legacy, 'legacy.conf'));
  assert.deepEqual(JSON.parse(link.searchParams.get('obfsParam')), {
    jc:'4', jmin:'40', jmax:'70', s1:'12', s2:'13', h1:'3', h2:'4', h3:'5', h4:'6',
  });
  assert.equal(decodeURIComponent(link.hash.slice(1)), 'legacy AWG');
});

test('AWG3.1 preserves extended fields and normalizes boolean flags', () => {
  const extra = `HeaderProtectionKey = ${key(4)}\nContentPaddingAddition = 8-24\nRekeyAfterTime = 120-240\nRekeyTimeout = 4\nRejectAfterTime = 300\nKeepaliveTimeout = 25-35\nMaxHandshakeAttempts = 5-8\nRandomTrailers = on\nDisableCookies = off\n`;
  const link = new URL(convertConf(profile.replace('[Peer]', extra + '[Peer]')));
  const obfs = JSON.parse(link.searchParams.get('obfsParam'));
  assert.equal(obfs.header_protection_key, key(4));
  assert.equal(obfs.content_padding_addition, '8-24');
  assert.equal(obfs.rekey_after_time, '120-240');
  assert.equal(obfs.rekey_timeout, '4');
  assert.equal(obfs.reject_after_time, '300');
  assert.equal(obfs.keepalive_timeout, '25-35');
  assert.equal(obfs.max_handshake_attempts, '5-8');
  assert.equal(obfs.random_trailers, 'true');
  assert.equal(obfs.disable_cookies, 'false');
  assert.ok(decodeURIComponent(link.hash).endsWith(' AWG'));
});

test('optional peer fields and DNS stay absent; IPv6 endpoint is supported', () => {
  const text = profile.replace(/^(DNS|PresharedKey|PersistentKeepalive) = .*\n/gm, '')
    .replace('vpn.example.test:51820', '[2001:db8::1]:443');
  const link = new URL(convertConf(text));
  assert.equal(link.host, '[2001:db8::1]:443');
  for (const field of ['dns', 'presharedKey', 'keepalive']) assert.equal(link.searchParams.has(field), false);
});

test('invalid or unrepresentable input fails without echoing the supplied value', () => {
  const marker = 'synthetic-secret-marker';
  const cases = [
    '', '[Peer]\n' + profile, profile + '[Peer]\n', profile + '[Other]\n',
    profile.replace('Jc = 4', 'Jc = 4294967296'),
    profile.replace('Jc = 4', 'Jc = 4\nJc = 4'),
    profile.replace('Jc = 4', `Jc = ${marker}`),
    profile.replace('MTU = 1280', `FutureField = ${marker}`),
    profile.replace('S4 = 15\n', ''), profile.replace('Jmax = 70', 'Jmax = 30'),
    profile.replace('H1 = 1-3', 'H1 = 4-1'),
    profile.replace('I1 = <t>', 'I1 = <r 65536>'),
    profile.replace(key(1), marker),
    profile.replace('10.8.0.2/32', '999.1.1.1/32'),
    profile.replace('1.1.1.1, 2606:4700:4700::1111', 'dns.example.test'),
    profile.replace('0.0.0.0/0, ::/0', '10.0.0.0/8'),
    profile.replace('0.0.0.0/0, ::/0', '0.0.0.0/0, 0.0.0.0/0'),
    profile.replace('vpn.example.test:51820', 'vpn.example.test:0'),
    profile.replace('vpn.example.test:51820', 'evil.test/path:443'),
    profile.replace('vpn.example.test:51820', '[not-ipv6]:443'),
    profile.replace('[Peer]', 'RandomTrailers = perhaps\n[Peer]'),
    profile.replace('S1 = 12', 'S1 = 1').replace('[Peer]', `HeaderProtectionKey = ${key(4)}\n[Peer]`),
    profile.replace('Jc = 4', 'Jc = ${MISSING}'), 'x'.repeat(65537),
  ];
  for (const text of cases) assert.throws(() => convertConf(text), error => {
    assert.equal(error.message.includes(marker), false);
    assert.equal(error.message.includes(key(1)), false);
    return true;
  });
});

test('AWG filename markers are normalized to one final AWG suffix',()=>{
  for(const name of ['Germany AWG','Germany AWG2','Germany AWG3.1 AWG','Germany TT','Germany AVG']) {
    const title=decodeURIComponent(new URL(convertConf(profile,name+'.conf')).hash.slice(1));
    assert.equal(title,'Germany AWG');
  }
});
