#!/usr/bin/env python3
"""Build the browser-only AWG converter without third-party dependencies."""
from pathlib import Path

from build_clash_page import csp_hash

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'site/awg'
OUTPUT = ROOT / 'docs/awg/index.html'


def build_page() -> str:
    converter = (SOURCE / 'converter.mjs').read_text().replace('export function convertConf', 'function convertConf')
    app = (SOURCE / 'app.mjs').read_text().replace("import {convertConf} from './converter.mjs';\n", '')
    javascript = converter + '\n' + app
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
