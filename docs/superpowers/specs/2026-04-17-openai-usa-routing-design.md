# OpenAI USA Routing Design

Date: 2026-04-17
Scope: ShadowRocket custom-only routing for OpenAI/ChatGPT traffic
Status: Draft for review

## Goal

Add a dedicated OpenAI ruleset to the custom profile so OpenAI and ChatGPT traffic is routed through a USA-only VLESS fallback group, following the same high-level pattern already used for the Google bundle.

## Constraints

- Do not add new service domains manually when an existing vendored source already exists.
- Keep the change minimal and preserve rule order.
- Treat this as `custom-only` behavior for routing, but keep the generated OpenAI ruleset itself publishable because it comes from the shared distillate pipeline.
- Do not modify `shadowrocket.conf` routing for this task.
- Rebuild generated artifacts required by repository policy after changing distillate inputs and custom routing config.

## Current State

- The repository already vendors the Blackmatrix7 OpenAI pack in `distillate/upstream/bm7/OpenAI.list`.
- The category `openai` already exists in `distillate/manifest.json`.
- Distillate already produces `distillate/text/domain/openai.txt` and `distillate/text/ip/openai.txt`.
- There is currently no legacy published file `rules/openai.list`.
- There is currently no dedicated `OPENAI` proxy group in `shadowrocket_custom.conf`.
- There is currently no explicit `RULE-SET` for OpenAI traffic in either Shadowrocket profile.

## Chosen Approach

Use a dedicated generated ruleset plus a dedicated custom-only proxy group:

1. Extend the existing `openai` category in `distillate/manifest.json` with:
   - `bucket: "proxy"`
   - `legacy_rule_path: "rules/openai.list"`
2. Rebuild distillate outputs so `rules/openai.list` is generated from the existing vendored Blackmatrix7 source.
3. Add a new `OPENAI` fallback group to `shadowrocket_custom.conf`.
4. Limit that group to USA VLESS nodes via `policy-regex-filter`.
5. Add a `RULE-SET` entry in `shadowrocket_custom.conf` that routes `rules/openai.list` to the `OPENAI` group.
6. Place the new rule alongside the Google bundle rule and above the broader community bundle so OpenAI matches the dedicated route first.

## Why This Approach

- It reuses the repository's current distillate model instead of adding hand-maintained lists.
- It matches the existing Google routing shape, which keeps the config easier to reason about.
- It isolates the USA preference to the custom profile, which aligns with the repository's `custom-only` guidance.
- It avoids touching shared routing behavior before there is evidence the change should apply to all users.

## Proxy Group Design

The new custom-only group will be:

- Name: `OPENAI`
- Type: `fallback`
- Target nodes: only policies whose names match USA VLESS naming
- Behavior: automatic fallback within USA-only VLESS nodes
- Intended purpose: improve stability for OpenAI/ChatGPT traffic on weak internet by preferring a constrained set of geographically appropriate routes

The regex should be conservative and match both common name orders:

- `.*USA.*Vless.*`
- `.*Vless.*USA.*`

Case-insensitive matching will be used.

## Rule Placement

The `RULE-SET` for OpenAI should be added in `shadowrocket_custom.conf`:

- after manual admin sets
- near the Google bundle rule
- before `domains_community`

This ensures OpenAI traffic is matched by the dedicated USA route before it can fall through to broader proxy bundles.

## Files Expected To Change During Implementation

- `distillate/manifest.json`
- `shadowrocket_custom.conf`
- generated outputs from distillate:
  - `rules/openai.list`
  - `distillate/text/domain/openai.txt`
  - `distillate/text/ip/openai.txt`
  - `distillate/dat/*`
  - `distillate/summary.json`
  - `HAPP/DEFAULT.*`

`clash_config.yaml` is not expected to change because this task does not modify `shadowrocket.conf`, which is its source of truth.

## Verification Plan

After implementation:

1. Run `python3 scripts/build_distillate.py`
2. Run `python3 scripts/build_happ_routing.py`
3. Inspect `rules/openai.list` to confirm the generated list exists and contains OpenAI entries
4. Inspect `shadowrocket_custom.conf` to confirm:
   - `OPENAI` group exists
   - the new `RULE-SET` points to `rules/openai.list`
   - the rule is ordered above `domains_community`
5. Confirm `clash_config.yaml` remains untouched

## Risks

- If policy names do not consistently contain `USA` and `Vless`, the fallback group may resolve to zero nodes.
- Some OpenAI-adjacent dependencies in the upstream list are broad third-party domains; routing them through USA-only VLESS is intentional for this task, but it may also affect adjacent telemetry or payment flows tied to OpenAI sessions.
- The shared generated file `rules/openai.list` becomes part of the published artifact set, even though the dedicated routing behavior remains custom-only.

## Follow-Up

After this change, additional service-specific server groups can be added using the same pattern if more targeted routing is needed.
