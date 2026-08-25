# HAPP Routing: DEFAULT

## Быстрые ссылки

- DEFAULT (`роут-MotivatoPotato`), открыть сразу в HAPP:
  [potato-link.motivato-potato.workers.dev](https://potato-link.motivato-potato.workers.dev/)
- RU-VPN, открыть сразу в HAPP:
  [potato-link.motivato-potato.workers.dev/ru](https://potato-link.motivato-potato.workers.dev/ru)
- DEFAULT (`роут-MotivatoPotato`), deeplink:  
  [DEFAULT.DEEPLINK](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/HAPP/DEFAULT.DEEPLINK)
- DEFAULT (`роут-MotivatoPotato`), JSON:  
  [DEFAULT.JSON](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/HAPP/DEFAULT.JSON)
- RU-VPN, deeplink:
  [RU-VPN.DEEPLINK](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/HAPP/RU-VPN.DEEPLINK)
- RU-VPN, JSON:
  [RU-VPN.JSON](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/HAPP/RU-VPN.JSON)
- Local geodata:
  [distillate/dat/geoip.dat](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/distillate/dat/geoip.dat)  
  [distillate/dat/geosite.dat](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/distillate/dat/geosite.dat)

Ссылки `potato-link` отвечают HTTP-редиректом на соответствующий deeplink,
поэтому обычный тап должен сразу открыть импорт в HAPP. Raw-ссылки остаются
запасным вариантом для клиентов, блокирующих переходы на пользовательские
схемы.

## Пакет

- `HAPP/DEFAULT.JSON` хранится и обновляется в этой же ветке вместе с generated distillate-артефактами.
- Имя профиля: `роут-MotivatoPotato`.
- `BlockSites` указывает на `geosite:motivato-block`.
- `Geoipurl` и `Geositeurl` указывают напрямую на `distillate/dat/*`.
- Дополнительный профиль `RU-VPN` отправляет `geosite:category-ru` и
  `geoip:ru` через выбранный proxy, а весь несовпавший трафик — напрямую.
- `category-ru` включает `.ru`, `.рф`, `.su` и известные российские сервисы
  в международных доменных зонах.

## RU-VPN

Перед активацией `RU-VPN` выберите в HAPP сервер с проверенным российским
выходным IP. Профиль выбирает российский трафик, но не меняет страну
выбранного сервера.

Ручная проверка после импорта:

1. Российский IP-check или geo-restricted российский сервис должен видеть
   российский VPN-адрес.
2. Зарубежный IP-check должен видеть обычный прямой адрес устройства.
3. Переключение обратно на `роут-MotivatoPotato` должно возвращать прежнюю
   маршрутизацию.

## Source Of Truth

- Routing logic: `scripts/build_happ_routing.py`
- Distillate builder: `scripts/build_distillate.py`
- Manifest и overlays: `distillate/manifest.json`

## Block Logic

- `motivato_telemetry_ru` собирается из BM7 `Privacy` + `EasyPrivacy` по локальному exact allowlist.
- `motivato_telemetry_ms` собирается из тех же BM7 privacy-pack'ов по отдельному allowlist Microsoft telemetry.
- `motivato_torrent` хранится локально как поддерживаемый overlay и входит в `sr-direct`.
- `motivato_ads` содержит только `ad.mail.ru` и `alt-ad.mail.ru`.
- `motivato_block` агрегирует telemetry и advertising источники и публикуется в `geosite.dat`.

## Ручная проверка

```bash
python3 scripts/build_distillate.py
python3 scripts/build_happ_routing.py --build-stamp "$(git log -1 --format=%ct)"
```

```bash
python3 - <<'PY'
import json
from pathlib import Path
p = Path("HAPP/DEFAULT.JSON")
data = json.loads(p.read_text(encoding="utf-8"))
assert data["Name"] == "роут-MotivatoPotato"
assert data["BlockSites"] == ["geosite:motivato-block"]
assert data["Geositeurl"].endswith("/distillate/dat/geosite.dat")
print("OK")
PY
```

```bash
python3 - <<'PY'
import base64
import json
from pathlib import Path

profile = json.loads(Path("HAPP/RU-VPN.JSON").read_text(encoding="utf-8"))
deeplink = Path("HAPP/RU-VPN.DEEPLINK").read_text(encoding="utf-8").strip()
decoded = json.loads(base64.b64decode(deeplink.rsplit("/", 1)[1]))
assert decoded == profile
assert profile["GlobalProxy"] == "false"
assert profile["ProxySites"] == ["geosite:category-ru"]
assert profile["ProxyIp"] == ["geoip:ru"]
print("OK")
PY
```

## CI

- `/.github/workflows/sync-lists.yml` обновляет vendored upstream, distillate, XKeen и HAPP.
- `/.github/workflows/build-happ-routing.yml` пересобирает оба профиля при изменениях в конфиге или сборочных входах.
- `/.github/workflows/deploy-potato-link.yml` проверяет и публикует оба
  кликабельных редиректа после изменения deeplink.
