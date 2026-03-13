# HAPP Routing: DEFAULT

## Быстрые ссылки

- DEFAULT (`роут-MotivatoPotato`), deeplink:  
  [DEFAULT.DEEPLINK](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/HAPP/DEFAULT.DEEPLINK)
- DEFAULT (`роут-MotivatoPotato`), JSON:  
  [DEFAULT.JSON](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/HAPP/DEFAULT.JSON)
- Local geodata:
  [default_geoip.dat](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/HAPP/default_geoip.dat)  
  [default_geosite.dat](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/HAPP/default_geosite.dat)

## Пакет

- `HAPP/DEFAULT.JSON` строится локально из `distillate/`.
- Имя профиля: `роут-MotivatoPotato`.
- `BlockSites` указывает на `geosite:motivato-block`.
- `Geoipurl` и `Geositeurl` указывают на `default_*` файлы в этом репозитории.

## Source Of Truth

- Routing logic: `/Users/sergio/Documents/30_HOBBY_AI/shadorock/ShadowRocket/scripts/build_happ_routing.py`
- Distillate builder: `/Users/sergio/Documents/30_HOBBY_AI/shadorock/ShadowRocket/scripts/build_distillate.py`
- Manifest и overlays: `/Users/sergio/Documents/30_HOBBY_AI/shadorock/ShadowRocket/distillate/manifest.json`

## Block Logic

- `motivato_telemetry_ru` собирается из BM7 `Privacy` + `EasyPrivacy` по локальному exact allowlist.
- `motivato_telemetry_ms` собирается из тех же BM7 privacy-pack'ов по отдельному allowlist Microsoft telemetry.
- `motivato_torrent` хранится локально как overlay, seed-нутый из hydra `torrent`, но дальше живёт в репозитории.
- `motivato_ads` содержит только `ad.mail.ru` и `alt-ad.mail.ru`.
- `motivato_block` агрегирует все четыре источника и публикуется в `geosite.dat`.

## Ручная проверка

```bash
python3 /Users/sergio/Documents/30_HOBBY_AI/shadorock/ShadowRocket/scripts/build_distillate.py
python3 /Users/sergio/Documents/30_HOBBY_AI/shadorock/ShadowRocket/scripts/build_happ_routing.py
```

```bash
python3 - <<'PY'
import json
from pathlib import Path
p = Path("/Users/sergio/Documents/30_HOBBY_AI/shadorock/ShadowRocket/HAPP/DEFAULT.JSON")
data = json.loads(p.read_text(encoding="utf-8"))
assert data["Name"] == "роут-MotivatoPotato"
assert data["BlockSites"] == ["geosite:motivato-block"]
assert data["Geositeurl"].endswith("/HAPP/default_geosite.dat")
print("OK")
PY
```

## CI

- `/.github/workflows/sync-lists.yml` обновляет vendored upstream и `distillate/*`.
- `/.github/workflows/build-happ-routing.yml` собирает локальный `DEFAULT` из уже закоммиченного `distillate/`.
