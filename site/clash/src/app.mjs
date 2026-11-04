import {buildConfig} from './config.mjs';
import {buildMiConfig} from './clashmi-config.mjs';
import {mountForm} from './form.mjs';
mountForm({
  flclash:{build:buildConfig,client:'FlClash / Mihomo',filename:'flclash-personal.yaml'},
  clashmi:{build:buildMiConfig,client:'Clash Mi',filename:'clashmi-personal.yaml'},
});

// Save the same standalone tool without serializing any entered values.
document.getElementById('download-offline').addEventListener('click', () => {
  const copy = document.documentElement.cloneNode(true);
  for (const input of copy.querySelectorAll('input')) input.removeAttribute('value');
  for (const area of copy.querySelectorAll('textarea')) area.textContent = '';
  for (const node of copy.querySelectorAll('#status, #protocol-files-status')) node.textContent = '';
  const url = URL.createObjectURL(new Blob(['<!doctype html>\n' + copy.outerHTML], {type:'text/html;charset=utf-8'}));
  const link = document.createElement('a');
  link.href = url; link.download = 'clash-offline-generator.html';
  document.body.append(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
