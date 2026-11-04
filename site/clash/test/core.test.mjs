import test from 'node:test';
import assert from 'node:assert/strict';
import {readdirSync, readFileSync} from 'node:fs';
import {dirname, resolve, sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {parse} from 'yaml';
import {buildConfig, defaultDns} from '../src/config.mjs';

const siteRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const sourceRoot = resolve(siteRoot, 'src');
const options = {
  subscriptions: 'https://one.example.test/sub?key=synthetic\nhttps://two.example.test/mihomo',
  dns: 'https://dns.example.test/dns-query',
};

test('public generator modules have no imports that escape the site tree', () => {
  for (const name of readdirSync(sourceRoot).filter(name => name.endsWith('.mjs'))) {
    const file = resolve(sourceRoot, name);
    const source = readFileSync(file, 'utf8');
    const imports = [...source.matchAll(/\bfrom\s*['"]([^'"]+)['"]|^\s*import\s*['"]([^'"]+)['"]/gm)]
      .map(match => match[1] || match[2]);
    for (const specifier of imports.filter(value => value.startsWith('.'))) {
      const imported = resolve(dirname(file), specifier);
      assert.ok(imported === siteRoot || imported.startsWith(`${siteRoot}${sep}`), `${name} imports outside the public site`);
    }
  }
});

test('fresh public baseline produces one automatic Режим url-test pool', () => {
  const config = parse(buildConfig(options));
  const groups = config['proxy-groups'];
  assert.equal(groups.length, 1);
  assert.equal(groups[0].name, 'Режим');
  assert.equal(groups[0].type, 'url-test');
  assert.deepEqual(groups[0].use, ['Sub-1', 'Sub-2']);
  assert.equal(groups[0].url, 'https://www.youtube.com/favicon.ico');
  assert.equal(groups[0].interval, 180);
  assert.equal(groups[0].tolerance, 100);
  assert.equal(config['proxy-groups'].some(group => group.name === 'Обычные'), false);
  assert.ok(config.rules.includes('MATCH,Режим'));
  assert.ok(config.rules.includes('RULE-SET,torrent_block,REJECT'));
});

test('subscriptions use separate providers and retain the shared public routing rules', () => {
  const config = parse(buildConfig(options));
  assert.deepEqual(Object.keys(config['proxy-providers']), ['Sub-1', 'Sub-2']);
  assert.equal(config['proxy-providers']['Sub-1'].url, 'https://one.example.test/sub?key=synthetic');
  assert.equal(config['proxy-providers']['Sub-2'].url, 'https://two.example.test/mihomo');
  assert.equal(config['proxy-providers']['Sub-2'].override['additional-prefix'], '[2] ');
  assert.ok(config.rules.includes('RULE-SET,whitelist_direct,DIRECT'));
});

test('default and custom DNS stay public/user supplied and Smart DNS is optional', () => {
  const config = parse(buildConfig({subscriptions: options.subscriptions}));
  const template = parse(readFileSync(new URL('../../../clash_config.yaml', import.meta.url), 'utf8'));
  assert.deepEqual(config.dns, template.dns);
  assert.deepEqual(config.rules, template.rules);
  assert.deepEqual(config['proxy-providers']['Sub-1']['health-check'], template['proxy-providers']['Main-Sub']['health-check']);
  assert.deepEqual(config.dns.nameserver, defaultDns);
  assert.equal(config.dns['nameserver-policy'], undefined);
  assert.equal(config.hosts, undefined);

  const smart = parse(buildConfig({
    ...options,
    smartDns: 'https://smart.example.test/dns-query',
    relay: '203.0.113.9',
  }));
  assert.equal(smart.dns['nameserver-policy']['+.gemini.google.com'], 'https://smart.example.test/dns-query#Режим');
  assert.equal(smart.hosts['+.gemini.google.com'], '203.0.113.9');
  assert.ok(smart.rules.includes('DOMAIN-SUFFIX,gemini.google.com,Режим'));
  assert.ok(smart.rules.indexOf('DOMAIN-SUFFIX,gemini.google.com,Режим') < smart.rules.indexOf('RULE-SET,whitelist_direct,DIRECT'));
});

test('invalid URLs and relay addresses fail without reflecting private input', () => {
  for (const subscriptions of ['', 'javascript:alert(1)', 'https://user:pass@example.test/sub', 'https://example.test/sub#fragment']) {
    assert.throws(() => buildConfig({...options, subscriptions}));
  }
  assert.throws(() => buildConfig({...options, dns: 'http://dns.example.test/query'}));
  assert.throws(() => buildConfig({...options, relay: '127.0.0.1'}));
  assert.throws(() => buildConfig({...options, smartDns: 'https://smart.example.test/query', relay: '999.1.1.1'}));
  assert.throws(() => buildConfig({...options, links: 'vless://synthetic-password@node.example.test:443?unknown=1'}), error => {
    assert.equal(error.message.includes('synthetic-password'), false);
    return true;
  });
});

test('Clash Mi adds only its own listener and public rule snapshots', async () => {
  const {buildMiConfig} = await import('../src/clashmi-config.mjs');
  const flclash = parse(buildConfig(options));
  const clashMi = parse(buildMiConfig(options));
  assert.equal(flclash.port, 7890);
  assert.equal(flclash['socks-port'], 7891);
  assert.equal(flclash['mixed-port'], undefined);
  assert.equal(clashMi.port, 0);
  assert.equal(clashMi['socks-port'], 0);
  assert.equal(clashMi['mixed-port'], 7890);
  for (const provider of Object.values(flclash['rule-providers'])) {
    assert.equal(provider.payload, undefined);
    assert.equal(provider.proxy, undefined);
  }
  for (const provider of Object.values(clashMi['rule-providers'])) {
    assert.ok(provider.payload.length > 0);
    assert.equal(provider.proxy, 'Режим');
  }
});
