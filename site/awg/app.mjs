import {convertConf} from './converter.mjs';

// Capture the pristine standalone document before the user selects a file.
const offlineHTML = '<!doctype html>\n' + document.documentElement.outerHTML;
const form = document.querySelector('form');
const fileInput = document.getElementById('config-file');
const result = document.getElementById('result');
const output = document.getElementById('output');
const status = document.getElementById('status');
const openSR = document.getElementById('open-sr');
let revision = 0;
function clear() {
  revision += 1;
  output.value = ''; openSR.removeAttribute('href'); result.hidden = true; status.textContent = '';
}
function download(text, filename, type) {
  const url = URL.createObjectURL(new Blob([text], {type}));
  const link = document.createElement('a');
  link.href = url; link.download = filename;
  document.body.append(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
fileInput.addEventListener('change', clear);
form.addEventListener('reset', clear);
window.addEventListener('pagehide', () => { form.reset(); });
form.addEventListener('submit', async event => {
  event.preventDefault(); clear();
  const current = revision;
  const file = fileInput.files[0];
  if (!file) { status.textContent = 'Выберите файл .conf.'; return; }
  if (!/\.conf$/i.test(file.name) || file.size > 65536) {
    status.textContent = 'Нужен файл .conf размером до 64 КиБ.'; return;
  }
  let text;
  try { text = new TextDecoder('utf-8', {fatal:true}).decode(await file.arrayBuffer()); }
  catch { if (current === revision) status.textContent = 'Не удалось прочитать UTF-8 файл .conf.'; return; }
  if (current !== revision) return;
  try {
    output.value = convertConf(text, file.name);
    openSR.href = 'shadowrocket://add/' + output.value;
    result.hidden = false;
    status.textContent = 'Ссылка готова. Откройте её в Shadowrocket или скопируйте.';
  } catch (error) { status.textContent = error.message; }
});
document.getElementById('copy').addEventListener('click', async () => {
  const current = revision;
  if (!output.value) return;
  try {
    await navigator.clipboard.writeText(output.value);
    if (current === revision) status.textContent = 'Ссылка скопирована.';
  } catch {
    if (current !== revision) return;
    output.focus(); output.select();
    status.textContent = 'Браузер не разрешил копирование. Скопируйте выделенную ссылку вручную.';
  }
});
document.getElementById('download').addEventListener('click', () => {
  if (output.value) download(output.value + '\n', 'shadowrocket-awg.txt', 'text/plain;charset=utf-8');
});
document.getElementById('download-offline').addEventListener('click', () => {
  download(offlineHTML, 'awg-shadowrocket-offline.html', 'text/html;charset=utf-8');
});
