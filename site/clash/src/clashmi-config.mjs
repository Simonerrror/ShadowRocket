import {parse,stringify} from 'yaml';
import {buildConfig} from './config.mjs';
import {ruleSnapshots} from '../generated/clashmi-rules.mjs';

export function buildMiConfig(options) {
  const config=parse(buildConfig(options));
  config.port=0;
  config['socks-port']=0;
  config['mixed-port']=7890;
  for(const [name,provider] of Object.entries(config['rule-providers'])) {
    if(!ruleSnapshots[name]?.length)throw new Error('Отсутствует публичный снимок правил Clash Mi.');
    provider.payload=[...ruleSnapshots[name]];
    provider.proxy='Режим';
  }
  return '# CLASH MI / MIHOMO CONFIG\n'+stringify(config,{lineWidth:0});
}
