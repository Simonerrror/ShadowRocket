#!/usr/bin/env python3
"""Build the offline Shadowrocket converter with the shared reviewed toolchain."""
import subprocess
import tempfile
from pathlib import Path

from build_clash_page import csp_hash

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'site/awg'
OUTPUT = ROOT / 'docs/awg/index.html'


def build_page() -> str:
    shared = ROOT / 'site/clash'
    esbuild = shared / 'node_modules/esbuild/bin/esbuild'
    if not esbuild.is_file():
        raise RuntimeError('Install the reviewed exact dependencies from site/clash/package-lock.json')
    with tempfile.TemporaryDirectory(prefix='shadowrocket-page-') as directory:
        bundle = Path(directory) / 'app.js'
        subprocess.run([str(esbuild), str(SOURCE / 'app.mjs'), '--bundle', '--minify',
                        '--format=iife', '--platform=browser', '--target=es2022',
                        '--legal-comments=inline', f'--outfile={bundle}', '--log-level=warning'], check=True)
        license_text = (shared / 'node_modules/yaml/LICENSE').read_text()
        javascript = '/*! yaml 2.9.1 (ISC)\n' + license_text + '*/\n' + bundle.read_text()
    css = (ROOT / 'site/clash/style.css').read_text() + (SOURCE / 'style.css').read_text()
    html = (SOURCE / 'index.html').read_text()
    if '</script' in javascript.lower() or '</style' in css.lower():
        raise ValueError('Unexpected closing tag in inline resources')
    for marker in ('<!-- STYLES -->', '<!-- SCRIPT -->'):
        if html.count(marker) != 1:
            raise ValueError('Expected one inline resource marker')
    return (html.replace("script-src 'self'", f"script-src 'sha256-{csp_hash(javascript)}'")
            .replace("style-src 'self'", f"style-src 'sha256-{csp_hash(css)}'")
            .replace('<!-- STYLES -->', f'<style>{css}</style>')
            .replace('<!-- SCRIPT -->', f'<script type="module">{javascript}</script>'))


def main() -> None:
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(build_page(), encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
