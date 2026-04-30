# ShadowRocket: конфиг и правила маршрутизации

Готовые конфиги для Shadowrocket, Clash Verge Rev (Mihomo) и XKeen (Xray),
построенные на manifest-driven distillate-пайплайне в `distillate/` с публикацией
consumer-списков в `rules/`. Проект поддерживает автообновление по URL и разделённую
маршрутизацию (Google/Gemini/YouTube, Microsoft и curated community/AI bundles).

## Содержание

- [Что внутри](#что-внутри)
- [Быстрый старт (Shadowrocket)](#быстрый-старт-shadowrocket)
- [Clash Verge Rev (Windows)](#clash-verge-rev-windows)
- [Структура репозитория](#структура-репозитория)
- [Логика `shadowrocket.conf`](#логика-shadowrocketconf)
- [Обновление](#обновление)
- [Расширение правил](#расширение-правил)

## Что внутри

- `shadowrocket.conf` — основной конфиг для Shadowrocket с автообновлением.
- `shadowrocket_custom.conf` — кастомный конфиг для GFN/NVIDIA (отдельный `update-url`, без изменения основного).
- `clash_config.yaml` — generated YAML для Clash Verge Rev (Mihomo), собранный из `shadowrocket.conf`.
- `XKeen/local/03_inbounds.json`, `XKeen/local/04_outbounds.json`, `XKeen/local/05_routing.json` — локальные private-артефакты для XKeen, собираемые из `XKeen/sub/sub.txt` и не публикуемые в репозитории.
- `XKeen/singles/*` — локальные single-node профили XKeen для ручной отладки отдельных узлов.
- `XKeen/diagnostics/*` — локальные диагностические профили XKeen для точечной проверки routing на одном узле.
- `distillate/` — канонический manifest, локальные overlays и собранные text/`dat`.
- `rules/` — вручную поддерживаемые rule-list'ы и generated consumer-списки.
- Источники истины разделены: `shadowrocket.conf` отвечает за порядок routing-правил и proxy-groups базового профиля, а `distillate/manifest.json` вместе с `distillate/overlays/*` и `distillate/filters/*` отвечает за состав и сборку большинства consumer-списков.

## Быстрый старт (Shadowrocket)

1. **Добавьте конфиг по ссылке** (Shadowrocket → Add Config/Добавить конфиг → URL):
   ```
   https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/shadowrocket.conf
   ```
   > В конфиге указан `update-url`, поэтому он будет обновляться автоматически.
2. **Добавьте подписку** на сервера в Shadowrocket (URL от вашего провайдера).
3. **Проверьте группы прокси**:
   - `AUTO-MAIN` — автофоллбэк по health-check: берёт первый живой VLESS-узел вне RU/BY/UA.
   - `AUTO-WL` — автофоллбэк только среди `WL`-узлов с `VLESS` вне RU/BY/UA; берёт первый живой узел по порядку списка.
   - `WL` — ручной выбор только среди узлов, где одновременно есть `WL` и `VLESS`.
   - `MANUAL-PROXY` — ручной выбор всех VLESS-узлов, включая RU/BY/UA.
   - `GOOGLE` — автофоллбэк для Google/Gemini/YouTube (NL VLESS + UAE VLESS + WL VLESS) с health-check через Google Sheets.
   - `OPENAI` — автофоллбэк для OpenAI/ChatGPT по USA, Finland, Poland и Germany VLESS-узлам.
   - `PROXY` — главный переключатель (Select): по умолчанию выбран `AUTO-WL`; вручную можно переключаться между `AUTO-WL`, `AUTO-MAIN`, `WL`, `MANUAL-PROXY` и `DIRECT`.

Кастомный профиль для GFN/NVIDIA (с `always-real-ip`, `dns-server = 194.242.2.2, 76.76.2.0`, `fallback-dns-server = tls://dns.mullvad.net, tls://freedns.controld.com`):
```
https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/shadowrocket_custom.conf
```

Кастомный SR-профиль для GFN/NVIDIA с приватными DoH/DoT без Google/Yandex/Cloudflare DNS (Mullvad + Quad9):
```
https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/shadowrocket_custom_private_dns.conf
```

## Clash Verge Rev (Windows)

> `clash_config.yaml` больше не поддерживается вручную отдельно: он генерируется из
> `shadowrocket.conf` через `scripts/build_clash_config.py`.
> Для автопроверки серверов `proxy-providers.Main-Sub.health-check`, `proxy-groups.AUTO-MAIN`
> и `proxy-groups.GOOGLE` используется `https://abs.twimg.com/favicon.ico`
> (`AUTO-MAIN`: интервал 780, tolerance 200; `GOOGLE`: интервал 300).

1. **Скачайте Clash Verge Rev**:  
   https://github.com/clash-verge-rev/clash-verge-rev/releases  
   Установите приложение.
2. **Включите режим TUN**. Если появится сообщение о нехватке драйвера:
   - нажмите на значок «гаечного ключа» рядом с тумблером TUN;
   - установите драйвер и дождитесь завершения.
3. **Подготовьте конфиг**:
   - скачайте файл `clash_config.yaml` из репозитория;
   - откройте его в редакторе и вставьте ссылку на свою подписку в соответствующее поле;
   - если меняете routing-логику локально, пересоберите YAML через `python3 scripts/build_clash_config.py`.
4. **Создайте профиль**:
   - Профили → Новый;
   - Тип: **Local**;
   - Название: **GeoRU**;
   - Выбрать файл → укажите отредактированный `clash_config.yaml`.
5. **Проверьте работу**:
   - переключите тумблер TUN (вкл/выкл);
   - откройте вкладку **Тест**;
   - в списке ожидаются «красные» записи:
     - `bahamut anime`
     - два китайских узла
     - `youtube premium`
   - все остальные — зелёные (значит конфиг настроен правильно).

Важно: так как конфиг содержит ссылку на вашу подписку, публиковать его онлайн для автообновления нельзя.  
При этом списки доменов и IP-диапазонов продолжают обновляться автоматически.

## Структура репозитория

| Путь | Назначение |
| --- | --- |
| `shadowrocket.conf` | Основной конфиг для Shadowrocket |
| `shadowrocket_custom.conf` | Кастомный конфиг Shadowrocket для GFN/NVIDIA |
| `shadowrocket_custom_private_dns.conf` | Кастомный конфиг Shadowrocket для GFN/NVIDIA с приватными DoH/DoT |
| `clash_config.yaml` | Generated-конфиг для Clash Verge Rev |
| `XKeen/local/*` | Локальные private-артефакты XKeen из подписки |
| `XKeen/singles/*` | Локальные single-node профили XKeen |
| `XKeen/diagnostics/*` | Локальные диагностические профили XKeen |
| `distillate/` | Канонический manifest, overlays и generated артефакты |
| `rules/` | Вручную поддерживаемые и generated consumer-списки |
| `modules/` | Готовые модули для Shadowrocket |
| `scripts/` | Вспомогательные скрипты |

Практическое правило сопровождения:
- вручную редактируются `shadowrocket.conf`, `shadowrocket_custom.conf`, `shadowrocket_custom_private_dns.conf`, `distillate/manifest.json`, `distillate/overlays/*`, `distillate/filters/*`, `rules/adobe_telemetry_custom.list`, `rules/russia_extended.list`, `rules/voice_ports.list`, `modules/GFN-AM.module`;
- generated-артефакты (`clash_config.yaml`, `HAPP/DEFAULT.*`, `distillate/text/**`, `distillate/dat/**`, `distillate/summary.json`, `rules/google-all.list`, `rules/microsoft.list`, `rules/domains_community.list`, `rules/telegram.list`, `rules/whitelist_direct.list`, `rules/greylist_proxy.list`, `rules/anti_advertising*.list`) не поддерживаются вручную;
- `modules/anti_advertising.module` и `modules/anti_advertising_custom.module` semi-generated: их ручные заголовки и локальные исключения сохраняются, но `RULE-SET` на anti-ad чанки переписываются сборкой.

## Логика `shadowrocket.conf`

### [General]
- Базовые сетевые настройки: DNS — `194.242.2.2` и `76.76.2.0`, fallback — `tls://dns.mullvad.net` и `tls://freedns.controld.com`, IPv6 выключен.
- `update-url` указывает на конфиг в репозитории.

### [Proxy Group]
- **AUTO-MAIN** — fallback-группа с health-check по имени (только VLESS, исключаем RU/BY/UA):
  `url=https://abs.twimg.com/favicon.ico`, `interval=780`, `timeout=7`.
- **AUTO-WL** — fallback-группа только по `WL`-узлам с `VLESS` вне RU/BY/UA:
  `url=https://abs.twimg.com/favicon.ico`, `interval=180`, `timeout=7`.
- **WL** — ручной выбор узлов по regex `(?i)(?:.*WL.*Vless.*|.*Vless.*WL.*)`.
- **MANUAL-PROXY** — ручной выбор всех VLESS-узлов, включая RU/BY/UA.
- **GOOGLE** — fallback-группа для Google/Gemini/YouTube (NL VLESS + UAE VLESS + узлы, где одновременно есть `WL` и `VLESS`):
  `url=https://abs.twimg.com/favicon.ico`, `interval=300`, `timeout=7`.
- **OPENAI** — fallback-группа для OpenAI/ChatGPT по USA, Finland, Poland и Germany VLESS-узлам:
  `url=https://abs.twimg.com/favicon.ico`, `interval=300`, `timeout=7`.
- **PROXY** — Select-группа; по умолчанию выбран AUTO-WL, вручную можно переключаться между AUTO-WL/AUTO-MAIN/WL/MANUAL-PROXY/DIRECT.
  В fallback-группах первичным считается первый живой узел в порядке подписки после применения regex-фильтра.

### [Rule]
Порядок важен: правила обрабатываются сверху вниз.

1. **Ручные overlays**
   - `distillate/overlays/whitelist_direct.add.list` — принудительно DIRECT.
   - Точечное DIRECT-исключение для Path of Exile (`DOMAIN-SUFFIX,pathofexile.com`, `DOMAIN-SUFFIX,poecdn.com`, плюс `DOMAIN-KEYWORD,pathofexile` и `DOMAIN-KEYWORD,pasthofexile`) также ведётся через `whitelist_direct`.
   - Для точечных исключений локальных web-ui через внешние alias-домены (например, `73001ed9a665c420ee07c76a.netcraze.io`) используйте `whitelist_direct`.
   - `distillate/overlays/greylist_proxy.add.list` — принудительно PROXY.
   - X/Twitter redirect и статика (`t.co`, `x.com`, `twitter.com`, `twimg.com`) закрепляются через `greylist_proxy`, чтобы короткие ссылки и связанные ресурсы не выпадали из принудительного PROXY-маршрута.
2. **Google/Gemini/YouTube**
   - Категория `google_all` собирается из BM7 `Google`/`GoogleDrive`/`GoogleEarth`/`GoogleFCM`/`GoogleSearch`/`GoogleVoice`/`YouTube`/`YouTubeMusic`/`Gemini`.
   - Домены и IP направляются в группу `GOOGLE` с `force-remote-dns` для доменных списков.
3. **Microsoft/Office 365/Teams/OneDrive**
   - Категория `microsoft` собирается из BM7 `Microsoft` и уходит в `PROXY`.
4. **Community bundle**
   - Категория `domains_community` собирается из BM7 `Telegram`/`GitHub`/`Steam`/`Riot`/`Origin`/`EA`/`Epic`/`Twitch`/`Pinterest` и уходит в `PROXY`.
5. **Direct для РФ**
   - Домены `.ru/.рф/.su` и GEOIP RU идут напрямую.
6. **FINAL**
   - Всё остальное — в `PROXY`.

### [Host] / [URL Rewrite]
- Статический `localhost`.
- Редиректы для `nnmclub.to` и `yandex.ru`.

## Обновление

- Конфиг обновляется автоматически через `update-url`.
- Канонические источники истины разделены: `shadowrocket.conf` задаёт routing order и базовые proxy-groups, `distillate/manifest.json` задаёт состав категорий и generation rule-list'ов.
- `scripts/sync_lists.py` раз в неделю подтягивает upstream-листы в `distillate/upstream/*`, затем обновляет `distillate/text/*`, `distillate/summary.json`, `rules/*.list`, anti-ad module refs и публикуемые артефакты.
- `scripts/build_distillate.py` работает только с уже закешированными файлами из `distillate/upstream/*` и собирает `distillate/text/*` плюс `distillate/dat/geosite.dat` и `distillate/dat/geoip.dat`.
- `scripts/build_clash_config.py` читает `[General]`, `[Proxy Group]` и `[Rule]` из базового `shadowrocket.conf` и пересобирает `clash_config.yaml` для Mihomo.
  Он переносит все поддерживаемые rule/group mapping'и, а неподдерживаемые для Clash детали (`force-remote-dns`, `policy-select-name`, `timeout`) оставляет в предупреждениях сборки.
- `scripts/build_xkeen_local.py` читает локальный `XKeen/sub/sub.txt`, выбирает только `VLESS`-узлы уровня `AUTO-WL` (с `WL`, без `RU/BY/UA`) и собирает private `XKeen/local/03_inbounds.json`, `XKeen/local/04_outbounds.json`, `XKeen/local/05_routing.json` плюс `XKeen/singles/*/03/04/05`.
- Private routing для XKeen теперь по умолчанию использует XKeen-native community-style схему: `routing` wrapper, `inboundTag`, direct-правила через `regexp`-suffix'ы и `ext:geosite_v2fly.dat` / `ext:geoip_zkeenip.dat`, proxy-правила через `ext:geosite_zkeen.dat`, и финальный proxy fallback.
- Тот же скрипт отдельно собирает `XKeen/diagnostics/germany-y-split/*`: это точечный diagnostic clone одного рабочего single-node профиля для быстрых проверок перед раскаткой на весь набор.
- `scripts/build_happ_routing.py` не ходит в BM7: он берет агрегаты `sr-direct`/`sr-proxy` и `motivato_block` из `distillate/text/*`, затем собирает `HAPP/DEFAULT.*` (`роут-MotivatoPotato`) с детерминированным `LastUpdated`.
- Антирекламный список собирается в том же distillate-пайплайне из OISD + HaGeZi, но публикуется чанками `rules/anti_advertising.01.list`, `.02.list`, `.03.list` и далее по мере необходимости. Количество чанков выбирается автоматически так, чтобы вес каждого был не больше примерно 7 МБ. Он не включается в compiled `geosite.dat` и не используется в HAPP. Для него предполагается отдельный модуль Shadowrocket.
- На этапе сборки из `anti_advertising` дополнительно вычищаются домены, содержащие `nvidia`/`geforce`/`geforcenow`/`nvidiagrid`, чтобы anti-ad модуль не ломал GeForce NOW и связанные NVIDIA API.
- Там же вычищаются official suffix'ы Discord (`discord.com`, `discord.gg`, `discordapp.com`, `discordapp.net` и смежные), чтобы upstream anti-ad не зацепил клиентские API, gateway и служебные поддомены Discord.

Fallback policy:
- если очередной upstream-лист недоступен, последний закоммиченный snapshot в `distillate/upstream/*` сохраняется;
- сборка `distillate`, XKeen и HAPP продолжается на этой локальной копии;
- удаление cache-файла из-за временной недоступности upstream не допускается.

Правило безопасного локального запуска:
- не запускайте `scripts/sync_lists.py` без необходимости refresh vendored upstream: по умолчанию он делает `git pull --rebase`;
- для обычной локальной пересборки используйте `python3 scripts/build_distillate.py` на уже закешированных `distillate/upstream/*`;
- если нужен локальный sync без обновления ветки, используйте `python3 scripts/sync_lists.py --no-pull`.

Локальная последовательность сборки:
```bash
python3 scripts/sync_lists.py --no-pull
python3 scripts/build_distillate.py
python3 scripts/build_clash_config.py
python3 scripts/build_happ_routing.py
```

Локальный private build для XKeen:
```bash
python3 scripts/build_xkeen_local.py \
  --subscription XKeen/sub/sub.txt \
  --output-dir XKeen/local \
  --singles-dir XKeen/singles \
  --diagnostics-dir XKeen/diagnostics
```
Этот шаг не публикует подписку: роутер использует локальные `XKeen/local/03_inbounds.json`, `XKeen/local/04_outbounds.json`, `XKeen/local/05_routing.json` или один из профилей в `XKeen/singles/*`.

Отдельный diagnostic build для `Germany(Y)` после этого появится в `XKeen/diagnostics/germany-y-split/`.

GitHub Actions:
- `.github/workflows/sync-lists.yml` запускается вручную или по weekly cron и обновляет vendored upstream, `distillate/*`, `rules/*.list`, anti-ad module refs, `clash_config.yaml` и `HAPP/*`.
- `.github/workflows/build-happ-routing.yml` запускается по push/вручную и пересобирает `clash_config.yaml` и `HAPP/*` из уже закоммиченного `distillate/` и `shadowrocket.conf`.

Политика изменений:
- `shadowrocket_custom.conf` и `modules/anti_advertising_custom.module` считаются `custom-only` и содержат single-user/GFN логику.
- `XKeen/local/*`, `XKeen/singles/*`, `XKeen/diagnostics/*` и `XKeen/sub/*` считаются `custom-only` и живут вне публичного release-контура.
- Если улучшение полезно всем, его нужно переносить и в основной конфиг, и в кастомные файлы.
- При изменении generated `rules/*.list` меняйте `distillate/manifest.json`, `distillate/overlays/*` или `distillate/filters/*`, а не итоговые generated-файлы.
- При изменении `shadowrocket.conf` пересобирайте `clash_config.yaml` и `HAPP/DEFAULT.*`.
- При изменении `distillate/manifest.json`, `distillate/overlays/*`, `distillate/filters/*` или vendored upstream пересобирайте `distillate/*`, generated `rules/*.list`, anti-ad module refs и `HAPP/*`.

## Расширение правил

Если нужно добавить сервис — добавьте новую категорию в `distillate/manifest.json`,
при необходимости создайте `distillate/overlays/*.list`, затем при необходимости подключите
сгенерированный `rules/*.list` в секции `[Rule]`.
Для анти-рекламы можно использовать модуль `modules/anti_advertising.module` по ссылке:
```
https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/modules/anti_advertising.module
```
Или кастомный модуль с локальными исключениями для GFN/NVIDIA:
```
https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/modules/anti_advertising_custom.module
```
В кастомный модуль также отдельно добавлен Adobe telemetry blocklist из `a-dove-is-dumb`; он применяется только там и не затрагивает основной anti-ad модуль.
Модуль подключает все доступные anti-ad чанки репозитория; список `RULE-SET` подставляется автоматически по фактически собранным файлам:
``` 
https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/anti_advertising.01.list
https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/anti_advertising.02.list
https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/anti_advertising.03.list
```
Как добавить модуль в Shadowrocket:
1. Откройте **Config → Modules**.
2. В правом верхнем углу нажмите **Add/Добавить**.
3. Вставьте ссылку на модуль и подтвердите загрузку.
4. Нажмите на загруженный модуль, чтобы активировать его.

Модуль работает в дополнение к любому активному конфигу и не заменяет его.
