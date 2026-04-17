# OpenAI USA Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dedicated generated OpenAI ruleset and route it through a USA-only VLESS fallback group in the custom Shadowrocket profile.

**Architecture:** Reuse the existing `openai` distillate category, publish it as `rules/openai.list`, then wire a new `OPENAI` proxy group and `RULE-SET` only in `shadowrocket_custom.conf`. Generated artifacts are refreshed through the existing build scripts so HAPP and distillate stay consistent.

**Tech Stack:** JSON manifest, Shadowrocket config, Python build scripts

---

### Task 1: Publish the OpenAI legacy ruleset

**Files:**
- Modify: `distillate/manifest.json`
- Verify: `rules/openai.list`

- [ ] **Step 1: Add legacy publication metadata to the existing `openai` category**

Set the `openai` category to publish into the proxy bucket and generate `rules/openai.list`.

- [ ] **Step 2: Rebuild distillate outputs**

Run: `python3 scripts/build_distillate.py`
Expected: exit code `0` and refreshed generated outputs including `rules/openai.list`

- [ ] **Step 3: Inspect the generated ruleset**

Run: `sed -n '1,80p' rules/openai.list`
Expected: generated header plus OpenAI-related DOMAIN / DOMAIN-SUFFIX / IP-CIDR entries

### Task 2: Route OpenAI through USA-only VLESS nodes in the custom profile

**Files:**
- Modify: `shadowrocket_custom.conf`

- [ ] **Step 1: Add the `OPENAI` fallback proxy group**

Create a new fallback group near `GOOGLE` that matches USA VLESS nodes with a case-insensitive regex for both `USA ... Vless` and `Vless ... USA`.

- [ ] **Step 2: Add the OpenAI ruleset entry in `[Rule]`**

Point `rules/openai.list` to the `OPENAI` group and place it near the Google rule, before `domains_community`.

- [ ] **Step 3: Inspect the custom profile**

Run: `sed -n '1,140p' shadowrocket_custom.conf`
Expected: `OPENAI` group exists and the new `RULE-SET` is ordered before `domains_community`

### Task 3: Refresh dependent artifacts and verify final state

**Files:**
- Refresh: `HAPP/DEFAULT.JSON`
- Refresh: `HAPP/DEFAULT.DEEPLINK`
- Refresh: `distillate/text/**`
- Refresh: `distillate/dat/**`
- Refresh: `distillate/summary.json`

- [ ] **Step 1: Rebuild HAPP artifacts**

Run: `python3 scripts/build_happ_routing.py`
Expected: exit code `0`

- [ ] **Step 2: Confirm generated outputs are present**

Run: `rg -n "\"name\": \"openai\"|rules/openai.list|OPENAI = fallback|RULE-SET,https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/openai.list" distillate/summary.json shadowrocket_custom.conf`
Expected: summary includes `openai` metadata, custom profile includes `OPENAI` group and `RULE-SET`

- [ ] **Step 3: Check git diff for scope**

Run: `git diff -- distillate/manifest.json shadowrocket_custom.conf rules/openai.list distillate/text/domain/openai.txt distillate/text/ip/openai.txt distillate/summary.json HAPP/DEFAULT.JSON HAPP/DEFAULT.DEEPLINK`
Expected: diff is limited to the intended OpenAI routing and generated artifact updates
