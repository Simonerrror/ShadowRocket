# HAPP Routing: DEFAULT

## Быстрые ссылки

- DEFAULT (`роут-MotivatoPotato`), deeplink:  
  [DEFAULT.DEEPLINK](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/HAPP/DEFAULT.DEEPLINK)
- DEFAULT (`роут-MotivatoPotato`), JSON:  
  [DEFAULT.JSON](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/HAPP/DEFAULT.JSON)
- Local geodata:
  [distillate/dat/geoip.dat](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/distillate/dat/geoip.dat)  
  [distillate/dat/geosite.dat](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/distillate/dat/geosite.dat)

## Пакет

- `HAPP/DEFAULT.JSON` публикуется из release-ветки `main`, а в source-ветках не коммитится.
- Имя профиля: `роут-MotivatoPotato`.
- `BlockSites` указывает на `geosite:motivato-block`.
- `Geoipurl` и `Geositeurl` указывают напрямую на `distillate/dat/*`.

## Source Of Truth

- Routing logic: `scripts/build_happ_routing.py`
- Distillate builder: `scripts/build_distillate.py`
- Manifest и overlays: `distillate/manifest.json`

## Block Logic

- `motivato_telemetry_ru` собирается из BM7 `Privacy` + `EasyPrivacy` по локальному exact allowlist.
- `motivato_telemetry_ms` собирается из тех же BM7 privacy-pack'ов по отдельному allowlist Microsoft telemetry.
- `motivato_torrent` хранится локально как поддерживаемый overlay и дальше живёт в репозитории.
- `motivato_ads` содержит только `ad.mail.ru` и `alt-ad.mail.ru`.
- `motivato_block` агрегирует все четыре источника и публикуется в `geosite.dat`.

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

## CI

- `/.github/workflows/publish-release.yml` собирает `DEFAULT` из `source/main` и публикует его в release-ветку `main`.
