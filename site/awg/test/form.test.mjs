import {test} from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';

// Exercise the real browser entry point with the DOM boundary substituted.
const source = readFileSync(new URL('../app.mjs', import.meta.url), 'utf8');
const app = source.replace(/^import .+;\n/gm, '');
function mount({clipboardFailure=false}={}) {
  const nodes = new Map();
  for (const id of ['form','config-file','result','output','status','open-sr','copy','download','download-offline','convert','vpn-text','node-select','notes']) {
    const handlers = {};
    nodes.set(id, {value:'',textContent:'',replaceChildren(...items) { this.options=items; },focus() {},select() {},hidden:id === 'result',files:[],href:undefined,
      addEventListener:(event,fn) => { handlers[event] = fn; },
      removeAttribute(name) { delete this[name]; },
      handlers,
    });
  }
  const form = nodes.get('form');
  form.reset = () => { nodes.get('vpn-text').value = ''; nodes.get('config-file').files = []; form.handlers.reset(); };
  const downloads = [];
  const document = {
    documentElement:{outerHTML:'<html>pristine tool</html>'},
    querySelector:() => form, getElementById:id => nodes.get(id),
    body:{append() {}}, createElement:() => ({click() {},remove() {}}),
  };
  const windowEvents = {}, clipboard=[], navigations=[];
  const context = vm.createContext({
    document, window:{location:{assign:uri=>navigations.push(uri)},addEventListener:(event,fn) => { windowEvents[event] = fn; }},
    TextDecoder, Blob, File, URL:{createObjectURL:blob => { downloads.push(blob); return 'blob:synthetic'; },revokeObjectURL() {}},
    setTimeout:fn => fn(), navigator:{clipboard:{writeText:async text => { if(clipboardFailure) throw new Error(); clipboard.push(text); }}},
    convertFiles:async (files,pasted='') => { const nodes=[]; files=[...files]; if(pasted.trim()) files.push(new File([pasted.trim()],'pasted.vpn')); for(const file of files) { const text=new TextDecoder().decode(await file.arrayBuffer()); if(text === 'bad') throw new Error('Некорректный формат профиля.'); nodes.push({name:file.name,link:'wg://vpn.example.test:443?privateKey=synthetic#' + encodeURIComponent(file.name)}); } return {nodes,notes:[]}; },
  });
  vm.runInContext(app, context);
  const select = (text, name='test.conf', buffer) => {
    nodes.get('config-file').files = [{name,size:text.length,arrayBuffer:buffer ?? (async () => new TextEncoder().encode(text).buffer)}];
    nodes.get('config-file').handlers.change();
  };
  return {nodes,form,select,downloads,windowEvents,clipboard,navigations};
}
const submit = state => state.form.handlers.submit({preventDefault() {}});

test('successful conversion exposes an app link; replacing input or clearing removes it', async () => {
  const state = mount(); state.select('valid', 'Тест.conf'); await submit(state);
  const {nodes} = state;
  assert.equal(nodes.get('result').hidden, false);
  assert.equal(nodes.get('open-sr').href, 'shadowrocket://add/' + nodes.get('output').value);
  assert.equal(nodes.get('open-sr').href.slice('shadowrocket://add/'.length), 'wg://vpn.example.test:443?privateKey=synthetic#%D0%A2%D0%B5%D1%81%D1%82.conf');
  state.select('bad');
  assert.equal(nodes.get('open-sr').href, undefined);
  assert.equal(nodes.get('output').value, '');
  await submit(state);
  assert.equal(nodes.get('result').hidden, true);
  assert.equal(nodes.get('open-sr').href, undefined);
});

test('reset during a pending read cannot restore the cleared result', async () => {
  const state = mount(); let finish;
  state.select('valid','test.conf', () => new Promise(resolve => { finish = resolve; }));
  const pending = submit(state); state.form.reset();
  finish(new TextEncoder().encode('valid').buffer); await pending;
  assert.equal(state.nodes.get('result').hidden, true);
  assert.equal(state.nodes.get('output').value, '');
  assert.equal(state.nodes.get('open-sr').href, undefined);
});

test('offline download after conversion contains the pristine tool, no result or app link', async () => {
  const state = mount(); state.select('valid'); await submit(state);
  state.nodes.get('download-offline').handlers.click();
  assert.equal(await state.downloads[0].text(), '<!doctype html>\n<html>pristine tool</html>');
  state.windowEvents.pagehide();
  assert.equal(state.nodes.get('output').value, '');
  assert.equal(state.nodes.get('open-sr').href, undefined);
});

test('one batch button copies every profile before opening SR once', async () => {
  const state=mount(); state.select('first','first.conf');
  state.nodes.get('config-file').files.push({name:'second.vpn',arrayBuffer:async()=>new TextEncoder().encode('second').buffer});
  await submit(state);
  assert.equal(state.nodes.get('output').value.split('\n').length,2);
  let prevented=false;
  await state.nodes.get('open-sr').handlers.click({preventDefault(){prevented=true;}});
  assert.equal(prevented,true);
  assert.deepEqual(state.clipboard,[state.nodes.get('output').value]);
  assert.deepEqual(state.navigations,['shadowrocket://']);
});

test('clipboard refusal does not launch SR with a partial batch', async () => {
  const state=mount({clipboardFailure:true}); state.select('first','first.conf');
  state.nodes.get('config-file').files.push({name:'second.conf',arrayBuffer:async()=>new TextEncoder().encode('second').buffer});
  await submit(state);
  await state.nodes.get('open-sr').handlers.click({preventDefault(){}});
  assert.equal(state.navigations.length,0);
  assert.match(state.nodes.get('status').textContent,/вручную/);
  assert.equal(state.nodes.get('output').value.split('\n').length,2);
});

test('pasted .vpn works without files and joins the same batch as selected files', async () => {
  const state=mount();
  state.nodes.get('vpn-text').value='  pasted-vpn  ';
  await submit(state);
  assert.equal(state.nodes.get('result').hidden,false);
  assert.match(state.nodes.get('output').value,/#pasted.vpn$/);
  state.select('file','file.conf');
  await submit(state);
  assert.equal(state.nodes.get('output').value.split('\n').length,2);
});

test('editing pasted text invalidates output; clearing removes text and links', async () => {
  const state=mount(); state.select('file'); await submit(state);
  state.nodes.get('vpn-text').value='bad';
  state.nodes.get('vpn-text').handlers.input();
  assert.equal(state.nodes.get('output').value,'');
  assert.equal(state.nodes.get('open-sr').href,undefined);
  await submit(state);
  assert.equal(state.nodes.get('result').hidden,true);
  state.form.reset();
  assert.equal(state.nodes.get('vpn-text').value,'');
});

test('choosing one node changes the direct app link, clipboard and downloaded TXT',async()=>{
  const state=mount(); state.select('first','first.conf');
  state.nodes.get('config-file').files.push({name:'second.yaml',arrayBuffer:async()=>new TextEncoder().encode('second').buffer});
  await submit(state);
  const all=state.nodes.get('output').value.split('\n');
  state.nodes.get('node-select').value='1';state.nodes.get('node-select').handlers.change();
  assert.equal(state.nodes.get('output').value,all[1]);
  assert.equal(state.nodes.get('open-sr').href,'shadowrocket://add/'+all[1]);
  await state.nodes.get('copy').handlers.click();assert.deepEqual(state.clipboard,[all[1]]);
  state.nodes.get('download').handlers.click();assert.equal(await state.downloads[0].text(),all[1]+'\n');
  state.nodes.get('node-select').value='all';state.nodes.get('node-select').handlers.change();
  assert.equal(state.nodes.get('output').value,all.join('\n'));
  assert.equal(state.nodes.get('open-sr').href,'shadowrocket://');
});
