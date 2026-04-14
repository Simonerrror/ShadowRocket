# XKeen

Публичного tracked routing-файла для XKeen больше нет. Эта директория теперь
используется только для local/private-пайплайна: генератор читает локальный
`XKeen/sub/sub.txt`, отбирает только `AUTO-WL`-подобные `VLESS`-узлы (`WL`,
без `RU/BY/UA`) и собирает приватные наборы `03/04/05`.

```bash
python3 scripts/build_xkeen_local.py \
  --subscription XKeen/sub/sub.txt \
  --output-dir XKeen/local \
  --singles-dir XKeen/singles
```

Он создаёт:

1. `XKeen/local/03_inbounds.json`
2. `XKeen/local/04_outbounds.json`
3. `XKeen/local/05_routing.json`
4. `XKeen/singles/<node-slug>/03_inbounds.json`
5. `XKeen/singles/<node-slug>/04_outbounds.json`
6. `XKeen/singles/<node-slug>/05_routing.json`
7. `XKeen/diagnostics/germany-y-split/03_inbounds.json`
8. `XKeen/diagnostics/germany-y-split/04_outbounds.json`
9. `XKeen/diagnostics/germany-y-split/05_routing.json`

Private routing для XKeen не копирует `shadowrocket.conf`. Основной private pipeline
теперь использует XKeen-native community-style routing:

1. `routing` wrapper вместо голой секции правил
2. `inboundTag: ["redirect", "tproxy"]` на рабочих правилах
3. direct-матчи через `regexp`-suffix'ы и `ext:geosite_v2fly.dat` / `ext:geoip_zkeenip.dat`
4. proxy-матчи через `ext:geosite_zkeen.dat`
5. финальный proxy fallback

В multi-node профиле proxy-трафик идёт через `balancerTag` `xkeen-auto-wl`, а
локальные outbound'ы получают детерминированные теги с префиксом `xkeen-wl-`.

В `XKeen/singles/*` генератор создаёт одиночные профили без балансира: в каждой
папке `04_outbounds.json` содержит ровно один VLESS outbound, а `05_routing.json`
маршрутизирует proxy-трафик в `outboundTag` `xkeen-single`.

Отдельно `XKeen/diagnostics/germany-y-split/` собирается как community-style тестовый профиль:
- `03_inbounds.json` и `04_outbounds.json` повторяют обычный single-node набор;
- `05_routing.json` использует секцию `routing` в форме, близкой к online XKeen generator;
- direct-правила берутся из `regexp`-suffix'ов и `ext:geosite_v2fly.dat` / `ext:geoip_zkeenip.dat`;
- proxy-правила используют `ext:geosite_zkeen.dat`.

В [XKeen/example](/Users/sergio/Documents/30_HOBBY_AI/shadorock/ShadowRocket/XKeen/example) лежит
базовый пример набора конфигов. Если ваша схема использует отдельный DNS-блок,
добавляйте `02_dns.json` между `01_log.json` и `03_inbounds.json`.

Установка private local набора:

```bash
python3 scripts/build_xkeen_local.py \
  --subscription XKeen/sub/sub.txt \
  --output-dir XKeen/local \
  --singles-dir XKeen/singles \
  --diagnostics-dir XKeen/diagnostics
```

1. При необходимости скопируйте `XKeen/example/02_dns.json` в `/opt/etc/xray/configs/02_dns.json`.
2. Скопируйте `XKeen/local/03_inbounds.json` в `/opt/etc/xray/configs/03_inbounds.json`.
3. Скопируйте `XKeen/local/04_outbounds.json` в `/opt/etc/xray/configs/04_outbounds.json`.
4. Скопируйте `XKeen/local/05_routing.json` в `/opt/etc/xray/configs/05_routing.json`.
5. Перезапустите XKeen: `xkeen -restart`.

Установка single-node набора для отладки:

1. Выберите папку в `XKeen/singles/`, например `XKeen/singles/germany-y/`.
2. При необходимости скопируйте `XKeen/example/02_dns.json` в `/opt/etc/xray/configs/02_dns.json`.
3. Скопируйте `03_inbounds.json`, `04_outbounds.json`, `05_routing.json` из выбранной папки в `/opt/etc/xray/configs/`.
4. Перезапустите XKeen: `xkeen -restart`.

Установка diagnostic набора для `Germany(Y)`:

1. Откройте `XKeen/diagnostics/germany-y-split/`.
2. Если на роутере остался предыдущий `02_dns.json` от неудачного теста, удалите или переименуйте его.
3. Скопируйте `03_inbounds.json`, `04_outbounds.json`, `05_routing.json` в `/opt/etc/xray/configs/`.
4. Перезапустите XKeen: `xkeen -restart`.
5. Сравните поведение RU-сайтов с обычным `XKeen/singles/germany-y/`.
