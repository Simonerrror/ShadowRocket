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
- `shadowrocket_whitelist.conf` — custom-only аварийный whitelist-профиль: direct allowlist/RU напрямую, всё остальное в один выбранный `PROXY`.
- `sr_wl_tests.conf` — custom-only тестовый профиль для пользовательских routing-гипотез.
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
   - `AUTO-MAIN` — автофоллбэк по health-check: берёт первый живой узел вне RU/BY/UA.
   - `AUTO-WL` — автофоллбэк только среди `WL`-узлов вне RU/BY/UA; берёт первый живой узел по порядку списка.
   - `WL` — ручной выбор только среди узлов, где есть `WL`.
   - `MANUAL-PROXY` — ручной выбор всех узлов, включая RU/BY/UA.
   - `GOOGLE` — автофоллбэк для Google/Gemini/YouTube по Gemini OK allowlist.
   - `OPENAI` — автофоллбэк для OpenAI/ChatGPT по USA, Finland, Poland, Germany и UAE-узлам.
   - `PROXY` — главный переключатель (Select): по умолчанию выбран `AUTO-WL`; вручную можно переключаться между `AUTO-WL`, `AUTO-MAIN`, `WL`, `MANUAL-PROXY` и `DIRECT`.

Кастомный профиль для GFN/NVIDIA (с `always-real-ip`, приватным DoH/DoT Mullvad + Quad9 и `dns-direct-system = false`):
```
https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/shadowrocket_custom.conf
```

Кастомный SR-профиль для GFN/NVIDIA с приватными DoH/DoT без Google/Yandex/Cloudflare DNS (Mullvad + Quad9, `dns-direct-system = false`):
```
https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/shadowrocket_custom_private_dns.conf
```

Аварийный whitelist-only профиль, когда не нужны отдельные Google/OpenAI/Microsoft группы:
```
https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/shadowrocket_whitelist.conf
```
В нём остаются только локальные исключения, `whitelist_direct.list`, `.ru/.рф/.su` и `GEOIP,RU,DIRECT`; весь Google, OpenAI и любой другой не-direct трафик уходит в один выбранный `PROXY`.

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
| `shadowrocket_whitelist.conf` | Custom-only аварийный whitelist-профиль: direct allowlist/RU напрямую, всё остальное через один `PROXY` |
| `sr_wl_tests.conf` | Custom-only тестовый профиль для пользовательских сценариев |
| `distillate/` | Канонический manifest, overlays и generated артефакты |
| `rules/` | Вручную поддерживаемые и generated consumer-списки |
| `modules/` | Готовые модули для Shadowrocket |
| `scripts/` | Вспомогательные скрипты |

Практическое правило сопровождения:
- вручную редактируются `shadowrocket.conf`, `shadowrocket_custom.conf`, `shadowrocket_custom_private_dns.conf`, `shadowrocket_whitelist.conf`, `sr_wl_tests.conf`, `distillate/manifest.json`, `distillate/overlays/*`, `distillate/filters/*`, `rules/adobe_telemetry_custom.list`, `rules/russia_extended.list`, `rules/voice_ports.list`, `modules/GFN-AM.module`, `modules/anti_advertising_custom.header`, `modules/instagram-meta.module`, `modules/instagram-meta-full-fix.sgmodule`;
- generated-артефакты (`clash_config.yaml`, `HAPP/DEFAULT.*`, `distillate/text/**`, `distillate/dat/**`, `distillate/summary.json`, `rules/google-all.list`, `rules/microsoft.list`, `rules/domains_community.list`, `rules/telegram.list`, `rules/instagram_meta.list`, `rules/whitelist_direct.list`, `rules/greylist_proxy.list`, `rules/anti_advertising_light.list`, `rules/anti_advertising_medium.list`, `rules/anti_advertising_pro.list`, `rules/anti_advertising_pro_plus.list`, `rules/anti_advertising*.[0-9][0-9].list`, `modules/anti_advertising*.module`) не поддерживаются вручную;
- `rules/anti_advertising.list` — frozen legacy snapshot для старых ссылок; supported anti-ad API — chunk-файлы и модули.
- custom anti-ad модули собираются из `modules/anti_advertising_custom.header`: GFN/NVIDIA DIRECT-prefix и Adobe telemetry blocklist добавляются перед выбранным anti-ad tier автоматически.

## Логика `shadowrocket.conf`

### [General]
- Базовые сетевые настройки: DNS — `https://dns.mullvad.net/dns-query` и `https://dns.quad9.net/dns-query`, fallback — `tls://dns.mullvad.net` и `tls://dns.quad9.net`, IPv6 выключен.
- `update-url` указывает на конфиг в репозитории.

### [Proxy Group]
- **AUTO-MAIN** — fallback-группа с health-check по имени (исключаем RU/BY/UA):
  `url=https://abs.twimg.com/favicon.ico`, `interval=780`, `timeout=7`.
- **AUTO-WL** — fallback-группа только по `WL`-узлам вне RU/BY/UA:
  `url=https://abs.twimg.com/favicon.ico`, `interval=180`, `timeout=7`.
- **WL** — ручной выбор узлов по regex `(?i).*WL.*`.
- **MANUAL-PROXY** — ручной выбор всех узлов, включая RU/BY/UA.
- **GOOGLE** — fallback-группа для Google/Gemini/YouTube по Gemini OK allowlist:
  `url=https://abs.twimg.com/favicon.ico`, `interval=300`, `timeout=7`.
- **OPENAI** — fallback-группа для OpenAI/ChatGPT по USA, Finland, Poland, Germany и UAE-узлам:
  `url=https://abs.twimg.com/favicon.ico`, `interval=300`, `timeout=7`.
- **PROXY** — Select-группа; по умолчанию выбран AUTO-WL, вручную можно переключаться между AUTO-WL/AUTO-MAIN/WL/MANUAL-PROXY/DIRECT.
  В fallback-группах первичным считается первый живой узел в порядке подписки после применения regex-фильтра.

### [Rule]
Порядок важен: правила обрабатываются сверху вниз.

1. **Ручные overlays**
   - `distillate/overlays/whitelist_direct.add.list` — принудительно DIRECT.
   - Точечное DIRECT-исключение для Path of Exile (`DOMAIN-SUFFIX,pathofexile.com`, `DOMAIN-SUFFIX,poecdn.com`, плюс `DOMAIN-KEYWORD,pathofexile` и `DOMAIN-KEYWORD,pasthofexile`) также ведётся через `whitelist_direct`.
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

GitHub Actions:
- `.github/workflows/sync-lists.yml` запускается вручную или по weekly cron и обновляет vendored upstream, `distillate/*`, `rules/*.list`, anti-ad module refs, `clash_config.yaml` и `HAPP/*`.
- `.github/workflows/build-happ-routing.yml` запускается по push/вручную и пересобирает `clash_config.yaml` и `HAPP/*` из уже закоммиченного `distillate/` и `shadowrocket.conf`.

Политика изменений:
- `shadowrocket_custom.conf`, `shadowrocket_custom_private_dns.conf`, `shadowrocket_whitelist.conf`, `sr_wl_tests.conf` и `modules/anti_advertising_custom.module` считаются `custom-only` и содержат single-user/GFN/test-profile логику.
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
