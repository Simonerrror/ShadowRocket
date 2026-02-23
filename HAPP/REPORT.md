# HAPP Routing Build Report

## Source
- Config: `/home/runner/work/ShadowRocket/ShadowRocket/shadowrocket.conf`
- Commit: `c8db06502255e9458af0ad77734a07e1e8addc51`

## Processed
- Rules in `[Rule]`: 14
- RULE-SET entries parsed: 1796
- Converted lines: 1775
- Dropped lines: 27

## Output
- Deeplink mode: `onadd`
- JSON length (compact): 783
- Deeplink length: 1065
- DirectSites: 2
- ProxySites: 1
- BlockSites: 0
- DirectIp: 3
- ProxyIp: 1
- BlockIp: 0

## Dropped USER-AGENT
- google-all.list:946: USER-AGENT,%E4%BA%91%E7%AB%AF%E7%A1%AC%E7%9B%98*
- google-all.list:947: USER-AGENT,*YouTubeMusic*
- google-all.list:948: USER-AGENT,*com.google.Drive*
- google-all.list:949: USER-AGENT,*com.google.ios.youtubemusic*
- google-all.list:950: USER-AGENT,*youtube*
- google-all.list:951: USER-AGENT,Google.Drive*
- google-all.list:952: USER-AGENT,YouTube*
- google-all.list:953: USER-AGENT,YouTubeMusic*
- google-all.list:954: USER-AGENT,com.google.ios.youtube*
- google-all.list:955: USER-AGENT,com.google.ios.youtubemusic*
- microsoft.list:678: USER-AGENT,Microsoft*
- microsoft.list:679: USER-AGENT,OneDrive*
- microsoft.list:680: USER-AGENT,OneDriveiOSApp*

## Dropped DST-PORT
- voice_ports.list:5: DST-PORT,3478,PROXY
- voice_ports.list:6: DST-PORT,3480,PROXY
- voice_ports.list:7: DST-PORT,3484,PROXY
- voice_ports.list:10: DST-PORT,5222,PROXY
- voice_ports.list:12: DST-PORT,596-599,PROXY
- voice_ports.list:15: DST-PORT,1400,PROXY
- voice_ports.list:18: DST-PORT,19302​–19309,PROXY

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
- none
