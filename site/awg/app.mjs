import {convertFiles} from './inputs.mjs';

// Capture the pristine standalone document before the user selects a file.
const offlineHTML = '<!doctype html>\n' + document.documentElement.outerHTML;
const form = document.querySelector('form');
const fileInput = document.getElementById('config-file');
const result = document.getElementById('result');
const output = document.getElementById('output');
const status = document.getElementById('status');
const openSR = document.getElementById('open-sr');
const submitButton = document.getElementById('convert');
let revision = 0, links = [];
function clear() {
  revision += 1; links = []; submitButton.disabled = false;
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
  submitButton.disabled = true;
  status.textContent = 'Преобразую файлы…';
  try {
    const converted = await convertFiles([...fileInput.files]);
    if (current !== revision) return;
    links = converted;
    output.value = links.join('\n');
    openSR.href = links.length === 1 ? 'shadowrocket://add/' + links[0] : 'shadowrocket://';
    openSR.textContent = links.length === 1 ? 'Открыть в Shadowrocket ↗' : 'Добавить весь набор в Shadowrocket ↗';
    result.hidden = false;
    status.textContent = `Готово профилей: ${links.length}. Можно передать весь набор в Shadowrocket.`;
  } catch (error) { if (current === revision) status.textContent = error.message; }
  finally { if (current === revision) submitButton.disabled = false; }
});
async function copyOutput() {
  const current = revision;
  if (!output.value) return false;
  try {
    await navigator.clipboard.writeText(output.value);
    if (current !== revision) return false;
    status.textContent = `Скопировано профилей: ${links.length}.`;
    return true;
  } catch {
    if (current === revision) {
      output.focus(); output.select();
      status.textContent = 'Браузер не разрешил копирование. Скопируйте весь выделенный список вручную и вставьте в SR.';
    }
    return false;
  }
}
openSR.addEventListener('click', async event => {
  if (!links.length) { event.preventDefault(); return; }
  if (links.length === 1) return; // Direct node URI, no clipboard permission needed.
  event.preventDefault();
  if (await copyOutput()) window.location.assign('shadowrocket://');
});
document.getElementById('copy').addEventListener('click', copyOutput);
document.getElementById('download').addEventListener('click', () => {
  if (output.value) download(output.value + '\n', 'shadowrocket-awg.txt', 'text/plain;charset=utf-8');
});
document.getElementById('download-offline').addEventListener('click', () => {
  download(offlineHTML, 'awg-shadowrocket-offline.html', 'text/html;charset=utf-8');
});
