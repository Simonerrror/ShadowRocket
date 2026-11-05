import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {shadowrocketName} from '../../clash/src/protocol-converters.mjs';

test('protocol markers are canonical, final and never repeated',()=>{
  const examples=[
    ['Germany','AWG','Germany AWG'],['Germany AWG2','AWG2','Germany AWG2'],
    ['Germany AVG','AWG','Germany AWG'],['Germany AWG3.1 AWG','AWG3.1','Germany AWG3.1'],
    ['Germany TT tt','TT','Germany TT'],['Germany_NV','TT','Germany TT'],
    ['Finland Naive NV','NV','Finland NV'],['Finland - NV','NV','Finland NV'],
    ['Newton','NV','Newton NV'],['TT','TT','Узел TT'],
  ];
  for(const [input,protocol,expected] of examples) {
    assert.equal(shadowrocketName(input,protocol),expected);
    assert.equal(shadowrocketName(expected,protocol),expected);
  }
});

test('canonical protocol suffixes match both maintained Shadowrocket AUTO-SPEED filters',()=>{
  for(const name of ['shadowrocket.conf','shadowrocket_custom.conf']) {
    const conf=readFileSync(new URL('../../../'+name,import.meta.url),'utf8');
    const expression=conf.match(/^AUTO-SPEED = .*policy-regex-filter=(.*),interval=/m)[1];
    const filter=new RegExp(expression.replace(/^\(\?i\)/,''),'i');
    for(const protocol of ['AWG','AWG2','AWG3.1','TT','NV']) assert.equal(filter.test(shadowrocketName('Germany',protocol)),true);
  }
});
