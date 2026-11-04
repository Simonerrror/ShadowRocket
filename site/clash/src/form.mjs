import {unpackProfileZip} from './archive.mjs';
export function mountForm(targets) {
const form=document.querySelector('form'), status=document.querySelector('#status');
const field=id=>document.getElementById(id);
const submitters=[...form.querySelectorAll('button[type=submit]')];
const setBusy=value=>submitters.forEach(button=>{button.disabled=value;});
let generation=0;
async function files(input) {
  const selected=[...input.files];
  if(selected.length>100) throw new Error('Допускается не более 100 файлов.');
  const totalLimit=16*1024*1024;
  if(selected.reduce((sum,file)=>sum+file.size,0)>totalLimit) throw new Error('Общий размер набора больше 16 МиБ.');
  const result=[];
  let total=0;
  for(const f of selected) {
    const limit=/\.zip$/i.test(f.name)?8*1024*1024:/\.conf$/i.test(f.name)?65536:2*1024*1024;
    if(f.size>limit) throw new Error('Файл слишком большой: .conf до 64 КиБ, остальные профили до 2 МиБ, ZIP до 8 МиБ.');
    const profiles=/\.zip$/i.test(f.name)?await unpackProfileZip(await f.arrayBuffer()):[{name:f.name,text:await f.text()}];
    for(const profile of profiles) {
      total+=new TextEncoder().encode(profile.text).length;
      if(total>totalLimit) throw new Error('Общий размер набора больше 16 МиБ.');
      result.push(profile);
    }
    if(result.length>100) throw new Error('Допускается не более 100 файлов.');
  }
  const grouped={awgFiles:[],wgFiles:[],ovpnFiles:[],mihomoFiles:[]};
  for(const f of result) {
    if(/\.conf$/i.test(f.name)) grouped[/^\s*Jc\s*=/im.test(f.text)?'awgFiles':'wgFiles'].push(f);
    else if(/\.ovpn$/i.test(f.name)) grouped.ovpnFiles.push(f);
    else if(/\.(?:ya?ml|json)$/i.test(f.name)) grouped.mihomoFiles.push(f);
    else throw new Error('Выберите .conf, .ovpn, Mihomo YAML/JSON или ZIP с этими файлами.');
  }
  return grouped;
}
form.addEventListener('submit',async event=>{
  event.preventDefault(); const current=++generation; status.textContent='Собираю конфиг…';
  const target=targets[event.submitter?.value||'flclash'];
  if(!target){status.textContent='Выберите FlClash или Clash Mi.';return;}
  const {build,client,filename}=target;
  setBusy(true);
  try {
    const options={subscriptions:[field('subscription-main').value,field('subscription-hysteria').value].filter(Boolean).join('\n'),dns:field('dns').value,smartDns:field('smart-dns').value,relay:field('relay').value,links:field('links').value};
    Object.assign(options,await files(field('protocol-files')));
    if(current!==generation) return;
    const config=build(options);
    const url=URL.createObjectURL(new Blob([config],{type:'application/yaml;charset=utf-8'}));
    const link=document.createElement('a'); link.href=url; link.download=filename; document.body.append(link); link.click(); link.remove();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
    status.textContent=`Готово. Импортируйте ${filename} в ${client} как локальный профиль.`;
  } catch (error) {if(current===generation) status.textContent=error.message;}
  finally {if(current===generation) setBusy(false);}
});
// Only our validation messages are shown; parser exceptions may contain private input.
form.addEventListener('reset',()=>{generation++; setBusy(false); status.textContent='Поля и выбранные файлы очищены.';});
window.addEventListener('pagehide',()=>form.reset());
for(const id of ['protocol-files']) field(id).addEventListener('change',()=>{field(id+'-status').textContent=`Выбрано файлов: ${field(id).files.length}`;});
form.addEventListener('reset',()=>{for(const id of ['protocol-files']) field(id+'-status').textContent='Файлы не выбраны.';});
}
