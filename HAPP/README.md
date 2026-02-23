# HAPP Routing: установка, соответствия и семантика

## Быстрые ссылки

- Deeplink (текстовый файл для копирования):  
  [DEFAULT.DEEPLINK](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/HAPP/DEFAULT.DEEPLINK)
- JSON профиль:  
  [DEFAULT.JSON](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/HAPP/DEFAULT.JSON)
- Локально собранные geo-файлы:  
  [geoip.dat](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/HAPP/geoip.dat)  
  [geosite.dat](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/HAPP/geosite.dat)
- Отчет сборки:  
  [REPORT.md](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/HAPP/REPORT.md)

## Нормативные defaults (зафиксировано)

- `RemoteDNSType = DoH`
- `RemoteDNSDomain = https://adfree.dns.nextdns.io/dns-query`
- `RemoteDNSIP = 76.76.2.0` (из первого `dns-server` в `shadowrocket.conf`)
- `DomesticDNSType = DoU`
- `DomesticDNSIP = 77.88.8.8` (Яндекс)
- `FakeDNS = true`
- `DomainStrategy = IPIfNonMatch`
- `RouteOrder = block-direct-proxy`
- `UseChunkFiles = false`
- `GlobalProxy = true` (все, что не попало в geosite/geoip-матчинг, уходит в proxy-контур)
- `DnsHosts` содержит bootstrap-записи для NextDNS/Cloudflare
- `Geoipurl` и `Geositeurl` берутся из `Loyalsoldier` release URL
- timestamp обновляется на каждой сборке (`LastUpdated = unix time`)

## Что является source of truth

- Базовые параметры сети и порядок правил: `/Users/sergio/Documents/30_HOBBY_AI/shadorock/ShadowRocket/shadowrocket.conf`.
- Источники доменных/IP списков: `/Users/sergio/Documents/30_HOBBY_AI/shadorock/ShadowRocket/rules/*.list`.
- Логика трансформации в HAPP: `/Users/sergio/Documents/30_HOBBY_AI/shadorock/ShadowRocket/scripts/build_happ_routing.py`.
- Фактические dropped-экземпляры после сборки: `/Users/sergio/Documents/30_HOBBY_AI/shadorock/ShadowRocket/HAPP/REPORT.md`.

## Матрица соответствий полей HAPP профиля

| Ключ HAPP | Как формируется | Источник в SR/rules | Где в коде | Примечание |
| --- | --- | --- | --- | --- |
| `Name` | Константа `"ShadowRocket-HAPP"` | Не из SR | `build_profile` | Меняется только правкой скрипта |
| `GlobalProxy` | Константа `"true"` | Семантика `FINAL,PROXY` | `build_profile` | Default outbound через proxy |
| `UseChunkFiles` | Константа `"false"` | Не из SR | `build_profile` | Отключено из-за размеров/поведения |
| `RemoteDns` | `--remote-dns-ip` или первый `dns-server` | `shadowrocket.conf` `[General]` | `extract_remote_dns_ip` + `build_profile` | Сейчас `76.76.2.0` |
| `DomesticDns` | `--domestic-dns-ip` (дефолт `77.88.8.8`) | Не из SR напрямую | `parse_args` + `build_profile` | Яндекс DNS |
| `RemoteDNSType` | `--remote-dns-type` (дефолт `DoH`) | Не из SR напрямую | `parse_args` + `build_profile` | Для `force-remote-dns` семантики |
| `RemoteDNSDomain` | `--remote-dns-domain` (дефолт NextDNS DoH URL) | Не из SR напрямую | `parse_args` + `build_profile` | `https://adfree.dns.nextdns.io/dns-query` |
| `RemoteDNSIP` | Повторяет `RemoteDns` | `dns-server` | `build_profile` | Bootstrap IP remote DNS |
| `DomesticDNSType` | `--domestic-dns-type` (дефолт `DoU`) | Не из SR напрямую | `parse_args` + `build_profile` | Домашний контур через DoU |
| `DomesticDNSDomain` | Константа `""` | Не из SR | `build_profile` | Не используется |
| `DomesticDNSIP` | Повторяет `DomesticDns` | Не из SR напрямую | `build_profile` | Bootstrap IP domestic DNS |
| `Geoipurl` | Константа URL Loyalsoldier | Внешний источник geo | `DEFAULT_GEOIP_URL` + `build_profile` | `releases/latest/download/geoip.dat` |
| `Geositeurl` | Константа URL Loyalsoldier | Внешний источник geo | `DEFAULT_GEOSITE_URL` + `build_profile` | `releases/latest/download/geosite.dat` |
| `LastUpdated` | `str(int(time.time()))` | Не из SR | `build_profile` | Unix timestamp сборки |
| `DnsHosts` | Константа `DEFAULT_DNS_HOSTS` | Не из SR | `DEFAULT_DNS_HOSTS` + `build_profile` | NextDNS + Cloudflare bootstrap |
| `RouteOrder` | `--route-order` (дефолт `block-direct-proxy`) | Не из SR напрямую | `parse_args` + `build_profile` | Приоритет block перед direct/proxy |
| `DirectSites` | `["geosite:private","geosite:sr-direct"]` | `DIRECT` site-правила | `write_geosite_inputs` + `build_profile` | `sr-direct` строится из поддерживаемых типов |
| `DirectIp` | `["geoip:private","geoip:ru","geoip:sr-direct"] + direct_geo` | `DIRECT` IP/GEOIP | `build_profile` | Дедупликация с сохранением порядка |
| `ProxySites` | `["geosite:sr-proxy"]` | `PROXY/GOOGLE` site-правила | `write_geosite_inputs` + `build_profile` | `GOOGLE` трактуется как proxy |
| `ProxyIp` | `["geoip:sr-proxy"] + proxy_geo` | `PROXY/GOOGLE` IP/GEOIP | `build_profile` | Дедупликация с сохранением порядка |
| `BlockSites` | `["geosite:sr-block"]` при наличии block site | `REJECT*` site-правила | `write_geosite_inputs` + `build_profile` | Обычно пусто в текущем профиле |
| `BlockIp` | `["geoip:sr-block"] + block_geo` при наличии block ip | `REJECT*` IP/GEOIP | `build_profile` | Обычно пусто в текущем профиле |
| `DomainStrategy` | Константа `"IPIfNonMatch"` | Семантика порядка rule matching | `build_profile` | Сначала домены, потом IP fallback |
| `FakeDNS` | Константа `"true"` | Не из SR напрямую | `build_profile` | DNS-перехват включен |

## Как правила Shadowrocket превращаются в HAPP

1. Читается секция `[Rule]` в исходном порядке.
2. Для `RULE-SET` берется локальный `rules/<name>.list` по имени из URL.
3. Action маппится: `DIRECT -> direct`, `PROXY/GOOGLE -> proxy`, `REJECT* -> block`.
4. Поддерживаемые типы: `DOMAIN-SUFFIX`, `DOMAIN`, `DOMAIN-KEYWORD`, `IP-CIDR`, `IP-CIDR6`, `GEOIP`.
5. Неподдерживаемые типы помечаются как dropped и попадают в `REPORT.md`.
6. В bucket-ах `direct/proxy/block` выполняется дедупликация с сохранением порядка.
7. Собираются локальные `geosite.dat` и `geoip.dat`.
8. Формируются `DEFAULT.JSON` и `DEFAULT.DEEPLINK`.

## Неподдерживаемые правила (реестр дропов)

| Тип | Где встречается сейчас | Почему дропается | Влияние | Workaround |
| --- | --- | --- | --- | --- |
| `USER-AGENT` | `rules/google-all.list`, `rules/microsoft.list` | Нет поддержки в HAPP-модели скрипта | Потеря UA-матчинга | Держать в SR/Clash, в HAPP опираться на domain/ip |
| `DST-PORT` | `rules/voice_ports.list` | Нет поддержки port-правил в конвертере | Потеря портового роутинга | Сохранять портовые правила в SR/Clash |
| `IP-ASN` | `rules/telegram.list` | Нет ASN-матчинга в конвертере | Потеря ASN-сегментации | Замена на `IP-CIDR`/`GEOIP` по необходимости |
| `AND` (composite) | Сейчас в активном `shadowrocket.conf` отсутствует | Композитные выражения не поддержаны | Потеря сложных комбинированных условий | Разносить на поддерживаемые типы или оставлять в SR/Clash |

Фактические строки dropped и счетчики всегда смотри в `/Users/sergio/Documents/30_HOBBY_AI/shadorock/ShadowRocket/HAPP/REPORT.md`.

## Ручная проверка соответствий

1. Пересобрать артефакты:

```bash
python3 /Users/sergio/Documents/30_HOBBY_AI/shadorock/ShadowRocket/scripts/build_happ_routing.py
```

2. Проверить ключи и обязательные defaults:

```bash
python3 - <<'PY'
import json
from pathlib import Path

p = Path("/Users/sergio/Documents/30_HOBBY_AI/shadorock/ShadowRocket/HAPP/DEFAULT.JSON")
data = json.loads(p.read_text(encoding="utf-8"))

assert data["RouteOrder"] == "block-direct-proxy"
assert data["FakeDNS"] == "true"
assert data["UseChunkFiles"] == "false"
assert data["RemoteDNSType"] == "DoH"
assert data["RemoteDNSDomain"] == "https://adfree.dns.nextdns.io/dns-query"
assert data["DomesticDNSType"] == "DoU"
assert data["GlobalProxy"] == "true"
assert data["DirectSites"], "DirectSites is empty"
assert data["ProxySites"], "ProxySites is empty"
print("OK: defaults and required route buckets")
PY
```

3. Проверить dropped-разделы в отчете:

```bash
rg -n "## Dropped USER-AGENT|## Dropped DST-PORT|## Dropped IP-ASN|## Dropped composite AND" \
  /Users/sergio/Documents/30_HOBBY_AI/shadorock/ShadowRocket/HAPP/REPORT.md
```

## Сценарии приёмки

1. `RULE-SET,.../google-all.list,GOOGLE` попадает в proxy bucket (`GOOGLE` трактуется как proxy).
2. `GEOIP,RU,DIRECT` попадает в `DirectIp`.
3. В `shadowrocket.conf` отсутствуют QUIC/DoT блокировки через inline `AND` (совместимость с Hysteria2).
4. `DEFAULT.JSON` отражает defaults из раздела "Нормативные defaults".
5. Изменения роутинга синхронно отражены в `shadowrocket.conf` и `clash_config.yaml`.

## Как добавить в Happ

1. Открой на устройстве с Happ ссылку `DEFAULT.DEEPLINK` (выше).
2. Скопируй строку `happ://routing/onadd/...` целиком.
3. Вставь ее в адресную строку Safari и открой.
4. Подтверди открытие в Happ и добавление маршрутизации.

## Если deeplink не открылся

1. Убедись, что Happ установлен и обновлен.
2. Попробуй открыть deeplink еще раз через Safari (не через встроенный вебвью).
3. Используй JSON-вариант `DEFAULT.JSON` для ручного импорта в Happ.

## Локальная пересборка

```bash
python3 /Users/sergio/Documents/30_HOBBY_AI/shadorock/ShadowRocket/scripts/build_happ_routing.py
```
