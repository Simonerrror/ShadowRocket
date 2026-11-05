import {test} from 'node:test';
import assert from 'node:assert/strict';
import {trustTunnelNodes} from '../../clash/src/trusttunnel-export.mjs';
import {ttProxies} from '../../clash/src/protocol-converters.mjs';

const proxy={type:'trusttunnel',name:'Тест TT',server:'tt.example.test',port:443,
  username:'synthetic-user',password:'synthetic-password',sni:'front.example.test',alpn:['h2'],
  'skip-cert-verify':false,udp:true,'client-fingerprint':'chrome','health-check':true};
function fields(link) {
  const data=Buffer.from(link.slice(6),'base64url'); let pos=0;
  const integer=()=>{const size=1<<(data[pos]>>6);let result=data[pos++]&63;for(let i=1;i<size;i++)result=result*256+data[pos++];return result;};
  const result=new Map();while(pos<data.length){const tag=integer(),length=integer();result.set(tag,data.subarray(pos,pos+length));pos+=length;}
  return result;
}

test('full Mihomo exports TT only, preserves connection fields and reports nonwire controls',()=>{
  const source=JSON.stringify({dns:{nameserver:['https://dns.example.test/dns-query']},
    proxies:[{type:'vless',name:'Other'},proxy],rules:['MATCH,DIRECT'],
    'proxy-providers':{remote:{type:'http',url:'https://provider.example.test/sub'}}});
  const result=trustTunnelNodes(source);
  assert.equal(result.nodes.length,1);
  const node=result.nodes[0];assert.equal(node.name,'Тест TT');assert.ok(node.link.startsWith('tt://?'));
  const decoded=fields(node.link);
  assert.equal(decoded.get(0)[0],1);
  assert.equal(decoded.get(1).toString(),'front.example.test');
  assert.equal(decoded.get(2).toString(),'tt.example.test:443');
  assert.equal(decoded.get(3).toString(),'front.example.test');
  assert.equal(decoded.get(5).toString(),'synthetic-user');
  assert.equal(decoded.get(6).toString(),'synthetic-password');
  assert.equal(decoded.has(7),false);
  assert.equal(decoded.get(12).toString(),'Тест TT');
  assert.match(result.notes.join(' '),/client-fingerprint/);
  assert.match(result.notes.join(' '),/health-check/);
  assert.match(result.notes.join(' '),/udp/);
  assert.equal(result.skipped,1);
  assert.match(result.notes.join(' '),/провайдер/);
  const restored=ttProxies([node.link])[0];
  for(const field of ['name','server','port','username','password','sni','skip-cert-verify']) assert.deepEqual(restored[field],proxy[field]);
});

test('single TT mapping exports IPv6, QUIC, long UTF-8 values and explicit certificate/IPv6 flags',()=>{
  const password='пароль'.repeat(30);
  const {nodes}=trustTunnelNodes(JSON.stringify({...proxy,server:'2001:db8::1',quic:true,'skip-cert-verify':true,'has-ipv6':false,password}));
  const decoded=fields(nodes[0].link);
  assert.equal(decoded.get(2).toString(),'[2001:db8::1]:443');
  assert.equal(decoded.get(6).toString(),password);
  assert.equal(decoded.get(4)[0],0);assert.equal(decoded.get(7)[0],1);assert.equal(decoded.get(9)[0],2);
});

test('YAML aliases and merge defaults in a full config are resolved locally',()=>{
  const result=trustTunnelNodes(`defaults: &tt\n  type: trusttunnel\n  server: tt.example.test\n  port: 443\n  username: synthetic\n  password: synthetic\nproxies:\n  - <<: *tt\n    name: One\n  - <<: *tt\n    name: Two\n    port: 444\n`);
  assert.deepEqual(result.nodes.map(node=>node.name),['One TT','Two TT']);
  assert.deepEqual(result.nodes.map(node=>ttProxies([node.link])[0].port),[443,444]);
});

test('malformed, incomplete or unrepresentable TT is rejected without credentials in diagnostics',()=>{
  const marker='synthetic-private-marker';
  const bad=[
    'proxies: [ '+marker, JSON.stringify({proxies:[{type:'vless'}]}),
    JSON.stringify({...proxy,password:''}),JSON.stringify({...proxy,port:70000}),
    JSON.stringify({...proxy,server:'bad/host'}),JSON.stringify({...proxy,server:'[tt.example.test'}),JSON.stringify({...proxy,'skip-cert-verify':marker}),
    JSON.stringify({...proxy,alpn:['http/1.1']}),JSON.stringify({...proxy,alpn:['h2','http/1.1']}),
    JSON.stringify({...proxy,certificate:marker}),JSON.stringify({...proxy,'dialer-proxy':marker}),
    JSON.stringify({...proxy,fingerprint:marker}),JSON.stringify({...proxy,udp:'true'}),
    JSON.stringify({...proxy,'has-ipv6':marker}), 'x'.repeat(2*1024*1024+1),
    'type: trusttunnel\ntype: trusttunnel\npassword: '+marker,
  ];
  for(const text of bad)assert.throws(()=>trustTunnelNodes(text),error=>{
    assert.equal(error.message.includes(marker),false);assert.equal(error.message.includes(proxy.password),false);return true;
  });
});

test('TT source names become one final TT suffix in metadata and TLV',()=>{
  for(const name of ['Germany','Germany TT','Germany tt TT','Germany NV','Germany AWG2']) {
    const node=trustTunnelNodes(JSON.stringify({...proxy,name})).nodes[0];
    assert.equal(node.name,'Germany TT');
    assert.equal(fields(node.link).get(12).toString(),'Germany TT');
  }
});
