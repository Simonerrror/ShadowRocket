# WeChat DIRECT Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional Shadowrocket module that routes WeChat and its required image/content CDN hosts directly.

**Architecture:** Keep the bypass isolated in one manually maintained `custom-only` module so no base profile or generated artifact changes. Cover first-party WeChat suffixes, two shared image-CDN suffixes, the WeChat-specific `wx.gtimg.com` suffix, and two exact shared-infrastructure hosts; protect the intended scope with unit tests and document module ordering relative to anti-advertising rules.

**Tech Stack:** Shadowrocket module syntax, Python `unittest`, Markdown

---

## File map

- Create `modules/wechat_direct.module`: module metadata and the approved `DIRECT` rules.
- Modify `tests/test_shadowrocket_profiles.py`: structural, allowlist, and scope-regression tests for the module and README.
- Modify `README.md`: public module URL, activation steps, and anti-advertising priority guidance.
- Modify `AGENTS.md`: classify the new module as manually maintained and `custom-only`.

### Task 1: Protect and add the WeChat routing module

**Files:**

- Create: `modules/wechat_direct.module`
- Modify: `tests/test_shadowrocket_profiles.py`

- [ ] **Step 1: Write the failing module tests**

Add the module constant after `TAILSCALE_MODULE`:

```python
WECHAT_MODULE = REPO_ROOT / "modules" / "wechat_direct.module"
```

Add these tests to `ShadowrocketProfilesTests`:

```python
    def test_wechat_direct_module_has_approved_rules(self) -> None:
        content = WECHAT_MODULE.read_text(encoding="utf-8")
        rules = section_lines(WECHAT_MODULE, "Rule")
        expected_rules = [
            "DOMAIN-SUFFIX,wechat.com,DIRECT",
            "DOMAIN-SUFFIX,wechatapp.com,DIRECT",
            "DOMAIN-SUFFIX,wechatlegal.net,DIRECT",
            "DOMAIN-SUFFIX,wechatpay.com,DIRECT",
            "DOMAIN-SUFFIX,weixin.com,DIRECT",
            "DOMAIN-SUFFIX,weixin.qq.com,DIRECT",
            "DOMAIN-SUFFIX,weixinbridge.com,DIRECT",
            "DOMAIN-SUFFIX,servicewechat.com,DIRECT",
            "DOMAIN-SUFFIX,qpic.cn,DIRECT",
            "DOMAIN-SUFFIX,qlogo.cn,DIRECT",
            "DOMAIN-SUFFIX,wx.gtimg.com,DIRECT",
            "DOMAIN,miniapp.gtimg.cn,DIRECT",
            "DOMAIN,res.wx.qq.com,DIRECT",
        ]

        self.assertIn("#!name=WeChat Direct", content)
        self.assertIn("[Rule]", content)
        self.assertEqual(expected_rules, rules)

    def test_wechat_direct_module_excludes_broad_tencent_and_ip_rules(self) -> None:
        rules = section_lines(WECHAT_MODULE, "Rule")

        self.assertNotIn("DOMAIN-SUFFIX,qq.com,DIRECT", rules)
        self.assertNotIn("DOMAIN-SUFFIX,gtimg.com,DIRECT", rules)
        self.assertNotIn("DOMAIN-SUFFIX,gtimg.cn,DIRECT", rules)
        self.assertNotIn("DOMAIN-SUFFIX,tencent.com,DIRECT", rules)
        self.assertFalse(any(rule.startswith(("IP-CIDR,", "IP-CIDR6,")) for rule in rules))
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

```bash
python3 -m unittest tests.test_shadowrocket_profiles.ShadowrocketProfilesTests.test_wechat_direct_module_has_approved_rules tests.test_shadowrocket_profiles.ShadowrocketProfilesTests.test_wechat_direct_module_excludes_broad_tencent_and_ip_rules -v
```

Expected: both tests error with `FileNotFoundError` for
`modules/wechat_direct.module`.

- [ ] **Step 3: Create the minimal module**

Create `modules/wechat_direct.module` with exactly:

```ini
#!url=https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/modules/wechat_direct.module
#!name=WeChat Direct
#!desc=Route WeChat and its required content CDN hosts directly.

[Rule]
DOMAIN-SUFFIX,wechat.com,DIRECT
DOMAIN-SUFFIX,wechatapp.com,DIRECT
DOMAIN-SUFFIX,wechatlegal.net,DIRECT
DOMAIN-SUFFIX,wechatpay.com,DIRECT
DOMAIN-SUFFIX,weixin.com,DIRECT
DOMAIN-SUFFIX,weixin.qq.com,DIRECT
DOMAIN-SUFFIX,weixinbridge.com,DIRECT
DOMAIN-SUFFIX,servicewechat.com,DIRECT
DOMAIN-SUFFIX,qpic.cn,DIRECT
DOMAIN-SUFFIX,qlogo.cn,DIRECT
DOMAIN-SUFFIX,wx.gtimg.com,DIRECT
DOMAIN,miniapp.gtimg.cn,DIRECT
DOMAIN,res.wx.qq.com,DIRECT
```

- [ ] **Step 4: Run the focused test and verify it passes**

Run the command from Step 2 again.

Expected: `Ran 2 tests` and `OK`.

- [ ] **Step 5: Commit the tested module**

```bash
git add modules/wechat_direct.module tests/test_shadowrocket_profiles.py
git commit -m "feat: add WeChat direct module"
```

### Task 2: Document installation and ownership

**Files:**

- Modify: `tests/test_shadowrocket_profiles.py`
- Modify: `README.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: Write the failing README test**

Add this constant after the module constants:

```python
README = REPO_ROOT / "README.md"
```

Add this test to `ShadowrocketProfilesTests`:

```python
    def test_readme_documents_wechat_direct_module(self) -> None:
        content = README.read_text(encoding="utf-8")

        self.assertIn("modules/wechat_direct.module", content)
        self.assertIn(
            "https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/modules/wechat_direct.module",
            content,
        )
        self.assertIn("выше anti-advertising", content)
```

- [ ] **Step 2: Run the README test and verify it fails**

Run:

```bash
python3 -m unittest tests.test_shadowrocket_profiles.ShadowrocketProfilesTests.test_readme_documents_wechat_direct_module -v
```

Expected: `FAIL` because `modules/wechat_direct.module` is not yet mentioned in
the README.

- [ ] **Step 3: Update the README**

In `README.md`:

1. Add this bullet after the Tailscale module in `Что внутри`:

```markdown
- `modules/wechat_direct.module` — отдельный custom-only модуль DIRECT для WeChat и его CDN без широкого обхода всего Tencent/QQ.
```

2. Add `modules/wechat_direct.module` to the manually maintained file list in
`Структура репозитория`.

3. Add this block after the Tailscale module explanation and before
`## Логика shadowrocket.conf`:

````markdown
### WeChat напрямую

Если при активном VPN в WeChat не загружаются сообщения, изображения или
мини-программы, подключите отдельный модуль:

```text
https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/modules/wechat_direct.module
```

В Shadowrocket откройте **Config → Modules → Add**, вставьте URL и включите
модуль. Если одновременно используется anti-advertising модуль, расположите
`WeChat Direct` выше anti-advertising, чтобы DIRECT-правила применялись раньше
блокирующих правил. Модуль направляет напрямую только домены WeChat и нужные
CDN; весь Tencent/QQ он не обходит.
````

- [ ] **Step 4: Record ownership in AGENTS.md**

In `AGENTS.md`:

- add `modules/wechat_direct.module` to the manually editable ownership list;
- state in the change-policy section that it is `custom-only`.

- [ ] **Step 5: Run the README test and verify it passes**

Run the command from Step 2 again.

Expected: `Ran 1 test` and `OK`.

- [ ] **Step 6: Commit documentation and its test**

```bash
git add AGENTS.md README.md tests/test_shadowrocket_profiles.py
git commit -m "docs: explain WeChat direct module"
```

### Task 3: Verify the repository and hand off the manual check

**Files:**

- Verify: `modules/wechat_direct.module`
- Verify: `tests/test_shadowrocket_profiles.py`
- Verify: `README.md`
- Verify: `AGENTS.md`

- [ ] **Step 1: Run the full unit-test suite**

Run:

```bash
python3 -m unittest discover -s tests -v
```

Expected: all tests pass with `OK`.

- [ ] **Step 2: Compile all Python scripts and tests**

Run:

```bash
python3 -m compileall -q scripts tests
```

Expected: exit code `0` with no output.

- [ ] **Step 3: Check patch hygiene and repository state**

Run:

```bash
git diff --check
git status --short --branch
```

Expected: `git diff --check` exits `0`; status shows no uncommitted changes and
the local branch ahead of `origin/main`.

- [ ] **Step 4: Perform the user-side Shadowrocket check**

After the commits are published to the raw GitHub URL:

1. Add and enable `wechat_direct.module`.
2. Place `WeChat Direct` above any anti-advertising module.
3. Keep the VPN active and fully reload WeChat.
4. Confirm that messages, avatars, images, and mini-program content load.
5. If content still fails, export the Shadowrocket connection log and capture
the failing hostname for a targeted follow-up rule.
