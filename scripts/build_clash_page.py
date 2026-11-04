#!/usr/bin/env python3
"""Build a self-contained Clash generator from public sources only."""

from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from build_clash_config import DEFAULT_CONF, DEFAULT_SUBSCRIPTION_URL, build_config, parse_rule_lines, provider_name_from_url


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "site/clash"
OUTPUT = ROOT / "docs/clash/index.html"
PUBLIC_RULES = "https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/"


def csp_hash(text: str) -> str:
    return base64.b64encode(hashlib.sha256(text.encode()).digest()).decode()


def main() -> None:
    # Always derive the baseline from the public source and a placeholder.
    # Never read a user's configured profile or any sibling private directory.
    baseline, _ = build_config(DEFAULT_CONF, DEFAULT_SUBSCRIPTION_URL)
    generated = SOURCE / "generated"
    generated.mkdir(exist_ok=True)
    (generated / "baseline.mjs").write_text("export const baseline = " + json.dumps(baseline, ensure_ascii=False) + ";\n")
    snapshots = {}
    for line in parse_rule_lines(DEFAULT_CONF):
        fields = [part.strip() for part in line.split(",")]
        if fields[0] != "RULE-SET":
            continue
        url = fields[1]
        if not url.startswith(PUBLIC_RULES):
            raise ValueError("Rule snapshots must use the owning public repository")
        path = ROOT / "rules" / Path(urlparse(url).path).name
        payload = [rule.strip() for rule in path.read_text(encoding="utf-8-sig").splitlines()
                   if rule.strip() and not rule.lstrip().startswith("#")]
        if not payload:
            raise ValueError("A public rule snapshot must not be empty")
        snapshots[provider_name_from_url(url)] = payload
    (generated / "clashmi-rules.mjs").write_text("export const ruleSnapshots = " + json.dumps(snapshots, ensure_ascii=False) + ";\n")

    esbuild = SOURCE / "node_modules/esbuild/bin/esbuild"
    if not esbuild.is_file():
        raise RuntimeError("Install the reviewed exact build dependencies with npm ci --ignore-scripts --prefix site/clash")
    with tempfile.TemporaryDirectory(prefix="clash-page-") as directory:
        bundle = Path(directory) / "app.js"
        subprocess.run([str(esbuild), str(SOURCE / "src/app.mjs"), "--bundle", "--minify",
                        "--format=iife", "--platform=browser", "--target=es2022",
                        "--legal-comments=inline", f"--outfile={bundle}", "--log-level=warning"], check=True)
        license_text = (SOURCE / "node_modules/yaml/LICENSE").read_text()
        javascript = "/*! yaml 2.9.1 (ISC)\n" + license_text + "*/\n" + bundle.read_text()
    css = (SOURCE / "style.css").read_text()
    html = (SOURCE / "index.html").read_text()
    html = html.replace("script-src 'self'", f"script-src 'sha256-{csp_hash(javascript)}'")
    html = html.replace("style-src 'self'", f"style-src 'sha256-{csp_hash(css)}'")
    resources = '<link rel="stylesheet" href="./style.css"><script type="module" src="./app.mjs"></script>'
    if html.count(resources) != 1 or html.count("</body>") != 1:
        raise ValueError("Unexpected generator HTML template")
    html = html.replace(resources, f"<style>{css}</style>").replace("</body>", f'<script type="module">{javascript}</script></body>')
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(html, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
