# HAPP Routing: DEFAULT + BONUS

## Быстрые ссылки

- DEFAULT (upstream roscom, as-is), deeplink:  
  [DEFAULT.DEEPLINK](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/HAPP/DEFAULT.DEEPLINK)
- DEFAULT (upstream roscom, as-is), JSON:  
  [DEFAULT.JSON](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/HAPP/DEFAULT.JSON)
- BONUS (локальная аугментация), deeplink:  
  [BONUS.DEEPLINK](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/HAPP/BONUS.DEEPLINK)
- BONUS (локальная аугментация), JSON:  
  [BONUS.JSON](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/HAPP/BONUS.JSON)
- BONUS geodata:  
  [bonus_geoip.dat](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/HAPP/bonus_geoip.dat)  
  [bonus_geosite.dat](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/HAPP/bonus_geosite.dat)
- Отчет сборки BONUS:  
  [REPORT.md](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/HAPP/REPORT.md)

## Пакеты

### DEFAULT

- `HAPP/DEFAULT.JSON` копируется из upstream без трансформации:
  `https://raw.githubusercontent.com/hydraponique/roscomvpn-routing/main/HAPP/DEFAULT.JSON`.
- Этот пакет используется как стабильный baseline.

### BONUS

- `HAPP/BONUS.JSON` строится локально из `shadowrocket.conf` + `rules/*.list`.
- `Geoipurl` и `Geositeurl` указывают на `raw.githubusercontent` с `bonus_*` файлами.
- Имя профиля: `роутинг+`.

## Source of truth

- DEFAULT JSON: upstream roscom routing JSON (см. ссылку выше).
- BONUS routing logic: `/Users/sergio/Documents/30_HOBBY_AI/shadorock/ShadowRocket/scripts/build_happ_routing.py`.
- Правила: `/Users/sergio/Documents/30_HOBBY_AI/shadorock/ShadowRocket/shadowrocket.conf` и `/Users/sergio/Documents/30_HOBBY_AI/shadorock/ShadowRocket/rules/*.list`.
- Отчет dropped/статистики: `/Users/sergio/Documents/30_HOBBY_AI/shadorock/ShadowRocket/HAPP/REPORT.md`.

## Pipeline parity (BONUS)

### Geosite

- База: `hydraponique/roscomvpn-geosite` (`data/`).
- Компилятор: `v2fly/domain-list-community` (`go run ./ ...`), то есть поведение true generator из `main.go`.
- Поверх базы добавляются локальные `sr-direct`, `sr-proxy`, `sr-block`.
- Выход: `HAPP/bonus_geosite.dat`.

### GeoIP

- Движок: `v2fly/geoip`.
- Parity логика hydraponique:
  - `config.json`, `ipset_ops.py`, `CUSTOM-LIST-ADD.txt`, `CUSTOM-LIST-DEL.txt` берутся из `hydraponique/roscomvpn-geoip`;
  - качаются те же внешние входные листы, что в их workflow;
  - строится `tmp/text/final.txt` через `ipset_ops.py --mode diff`;
  - генерируется итоговый dat с `direct/private`.
- Затем добавляются локальные `sr-direct`, `sr-proxy`, `sr-block` (если есть CIDR).
- Выход: `HAPP/bonus_geoip.dat`.

## Матрица ключей BONUS

| Ключ | Как формируется |
| --- | --- |
| `Name` | Константа `роутинг+` |
| `GlobalProxy` | Константа `true` |
| `UseChunkFiles` | Константа `false` |
| `RemoteDns` | Первый `dns-server` из `[General]` или `--remote-dns-ip` |
| `DomesticDns` | `--domestic-dns-ip` (дефолт `77.88.8.8`) |
| `RemoteDNSType` | `--remote-dns-type` (дефолт `DoH`) |
| `DomesticDNSType` | `--domestic-dns-type` (дефолт `DoU`) |
| `Geoipurl` | `.../HAPP/bonus_geoip.dat` |
| `Geositeurl` | `.../HAPP/bonus_geosite.dat` |
| `RouteOrder` | `--route-order` (дефолт `block-direct-proxy`) |
| `DirectSites/ProxySites/BlockSites` | Из parsed SR rules + curated geosite tags |
| `DirectIp/ProxyIp/BlockIp` | Из parsed SR IP rules + local/direct CIDR ranges |
| `DomainStrategy` | Константа `IPIfNonMatch` |
| `FakeDNS` | Константа `true` |

## Неподдерживаемые правила (BONUS)

| Тип | Где встречается | Статус |
| --- | --- | --- |
| `USER-AGENT` | `rules/google-all.list`, `rules/microsoft.list` | dropped |
| `DST-PORT` | `rules/voice_ports.list` | dropped |
| `IP-ASN` | `rules/telegram.list` | dropped |
| `AND` composite | inline `shadowrocket.conf` (если есть) | dropped |

Фактические строки всегда смотри в `HAPP/REPORT.md`.

## Ручная проверка

1. Пересборка:

```bash
python3 /Users/sergio/Documents/30_HOBBY_AI/shadorock/ShadowRocket/scripts/build_happ_routing.py
```

2. Проверка, что DEFAULT не трансформируется:

```bash
curl -fsSL https://raw.githubusercontent.com/hydraponique/roscomvpn-routing/main/HAPP/DEFAULT.JSON > /tmp/upstream-default.json
diff -u /tmp/upstream-default.json /Users/sergio/Documents/30_HOBBY_AI/shadorock/ShadowRocket/HAPP/DEFAULT.JSON
```

3. Проверка BONUS geodata и ссылок:

```bash
python3 - <<'PY'
import json
from pathlib import Path
p = Path("/Users/sergio/Documents/30_HOBBY_AI/shadorock/ShadowRocket/HAPP/BONUS.JSON")
data = json.loads(p.read_text(encoding="utf-8"))
assert data["Geoipurl"].endswith("/HAPP/bonus_geoip.dat")
assert data["Geositeurl"].endswith("/HAPP/bonus_geosite.dat")
print("OK")
PY
```

4. Проверка dropped разделов:

```bash
rg -n "## Dropped USER-AGENT|## Dropped DST-PORT|## Dropped IP-ASN|## Dropped composite AND" \
  /Users/sergio/Documents/30_HOBBY_AI/shadorock/ShadowRocket/HAPP/REPORT.md
```

## CI

- Сборка вызывается через `/.github/workflows/build-happ-routing.yml`.
- Workflow синхронизирует rules, пересобирает HAPP артефакты и коммитит изменения в `main`, если есть diff.
