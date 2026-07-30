# WeChat DIRECT module design

## Goal

Add an optional `custom-only` Shadowrocket module that sends WeChat control
traffic and the CDN domains needed for images and other embedded content
directly, avoiding the profile's VPN proxy.

## Scope

The module will be stored as `modules/wechat_direct.module` and will contain
only `[Rule]` entries with the `DIRECT` policy.

Core WeChat suffixes:

- `wechat.com`
- `wechatapp.com`
- `wechatlegal.net`
- `wechatpay.com`
- `weixin.com`
- `weixin.qq.com`
- `weixinbridge.com`
- `servicewechat.com`

Content delivery suffixes:

- `qpic.cn`
- `qlogo.cn`
- `wx.gtimg.com`

Targeted content hosts outside those suffixes:

- `miniapp.gtimg.cn`
- `res.wx.qq.com`

The CDN suffixes are shared infrastructure, so some non-WeChat images hosted
there may also bypass the proxy. This is accepted to make WeChat media loading
reliable without routing all Tencent traffic directly.

## Explicit exclusions

- Do not add broad `DIRECT` rules for `qq.com`, `gtimg.com`, `tencent.com`, or
  Tencent IP ranges.
- Do not modify the base, custom, private-DNS, or whitelist profiles.
- Do not add IP rules because the service and CDN address ranges can change.
- Do not alter generated rule lists or the distillate pipeline.

## Interaction with the anti-advertising module

The current anti-advertising lists contain entries under `weixin.qq.com`,
`qpic.cn`, `gtimg.cn`, and `wechatapp.com`. The WeChat module must be enabled
with higher rule priority than the anti-advertising module so its `DIRECT`
rules win for the listed suffixes and hosts. The README will document this
requirement.

The design intentionally does not bypass all `gtimg.cn` or `qq.com`:
`miniapp.gtimg.cn` and `res.wx.qq.com` are exact host rules. If Shadowrocket
logs later show a missing WeChat CDN hostname, it should be added as a targeted
rule based on that evidence.

## Documentation

Update the README to:

- list `modules/wechat_direct.module`;
- provide its raw GitHub URL;
- explain how to enable it;
- state that it must have higher priority than the anti-advertising module.

## Verification

Add repository tests that verify:

- the module metadata and `[Rule]` section exist;
- every approved suffix and exact host is routed to `DIRECT`;
- broad Tencent suffixes and IP rules are absent;
- the README includes the module URL and priority note.

Run the full repository unit-test and Python compile checks required by
`AGENTS.md`. The remaining manual check is to enable the module in Shadowrocket,
reload WeChat, and confirm that messages, avatars, images, and mini-program
content load while the VPN remains active.
