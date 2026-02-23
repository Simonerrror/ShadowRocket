# HAPP Routing Build Report

## Source
- Config: `/Users/sergio/Documents/30_HOBBY_AI/shadorock/ShadowRocket/shadowrocket.conf`
- Commit: `402d3afda1f8372f967d677a2bad6eaf14aa24a3`

## Processed
- Rules in `[Rule]`: 14
- RULE-SET entries parsed: 165
- Converted lines: 164
- Dropped lines: 10

## Output
- Deeplink mode: `onadd`
- JSON length (compact): 779
- Deeplink length: 1061
- DirectSites: 2
- ProxySites: 1
- BlockSites: 0
- DirectIp: 3
- ProxyIp: 1
- BlockIp: 0

## DNS source
- Remote DNS source: `dns-server` -> `76.76.2.0`
- Domestic DNS source: `fallback-dns-server` -> `1.1.1.1`

## Dropped USER-AGENT
- none

## Dropped DST-PORT
- none

## Dropped IP-ASN
- telegram.list:46: IP-ASN,211157,no-resolve
- telegram.list:47: IP-ASN,44907,no-resolve
- telegram.list:48: IP-ASN,59930,no-resolve
- telegram.list:49: IP-ASN,62014,no-resolve
- telegram.list:50: IP-ASN,62041,no-resolve

## Dropped composite AND
- shadowrocket.conf:44: AND,((PROTOCOL,UDP),(DEST-PORT,443)),REJECT-DROP
- shadowrocket.conf:45: AND,((PROTOCOL,UDP),(DEST-PORT,853)),REJECT-NO-DROP

## Other dropped reasons
- excluded_happ_ruleset: 3
