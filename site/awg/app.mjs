import {convertFiles} from './inputs.mjs';

// Capture the pristine standalone document before the user selects a file.
const offlineHTML = '<!doctype html>\n' + document.documentElement.outerHTML;
const form = document.querySelector('form');
const fileInput = document.getElementById('config-file');
const vpnText = document.getElementById('vpn-text');
const result = document.getElementById('result');
const output = document.getElementById('output');
const status = document.getElementById('status');
const openSR = document.getElementById('open-sr');
const submitButton = document.getElementById('convert');
const nodeSelect = document.getElementById('node-select');
const notes = document.getElementById('notes');
let revision = 0, nodes = [];
const selectedNodes = () => nodeSelect.value === 'all' ? nodes : [nodes[Number(nodeSelect.value)]].filter(Boolean);
function renderSelection() {
  const selected = selectedNodes();
  output.value = selected.map(node=>node.link).join('\n');
  if (!selected.length) { openSR.removeAttribute('href'); return; }
  openSR.href = selected.length === 1 ? 'shadowrocket://add/' + selected[0].link : 'shadowrocket://';
  openSR.textContent = selected.length === 1 ? 'Открыть узел в Shadowrocket ↗' : 'Добавить весь набор в Shadowrocket ↗';
  status.textContent = `Выбрано узлов: ${selected.length} из ${nodes.length}.`;
}
function clear() {
  revision += 1; nodes = []; nodeSelect.replaceChildren(); notes.textContent = ''; submitButton.disabled = false;
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
vpnText.addEventListener('input', clear);
form.addEventListener('reset', clear);
window.addEventListener('pagehide', () => { form.reset(); });
form.addEventListener('submit', async event => {
  event.preventDefault(); clear();
  const current = revision;
  submitButton.disabled = true;
  status.textContent = 'Преобразую файлы…';
  try {
    const converted = await convertFiles([...fileInput.files], vpnText.value);
    if (current !== revision) return;
    nodes = converted.nodes;
    const option = (value, text) => { const el=document.createElement('option'); el.value=value; el.textContent=text; return el; };
    nodeSelect.replaceChildren(option('all',`Весь набор (${nodes.length})`),...nodes.map((node,index)=>option(String(index),node.name)));
    nodeSelect.value = 'all';
    notes.textContent = converted.notes.join(' ');
    renderSelection();
    result.hidden = false;
    status.textContent = `Готово узлов: ${nodes.length}. Выберите один узел или весь набор.`;
  } catch (error) { if (current === revision) status.textContent = error.message; }
  finally { if (current === revision) submitButton.disabled = false; }
});
async function copyOutput() {
  const current = revision;
  if (!output.value) return false;
  try {
    await navigator.clipboard.writeText(output.value);
    if (current !== revision) return false;
    status.textContent = `Скопировано узлов: ${selectedNodes().length}.`;
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
  if (!selectedNodes().length) { event.preventDefault(); return; }
  if (selectedNodes().length === 1) return; // Direct node URI, no clipboard permission needed.
  event.preventDefault();
  if (await copyOutput()) window.location.assign('shadowrocket://');
});
nodeSelect.addEventListener('change', () => { revision += 1; renderSelection(); });
document.getElementById('copy').addEventListener('click', copyOutput);
document.getElementById('download').addEventListener('click', () => {
  if (output.value) download(output.value + '\n', 'shadowrocket-nodes.txt', 'text/plain;charset=utf-8');
});
document.getElementById('download-offline').addEventListener('click', () => {
  download(offlineHTML, 'shadowrocket-converter-offline.html', 'text/html;charset=utf-8');
});
