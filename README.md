# ShadowRocket: конфиг и правила маршрутизации

Готовые конфиги для Shadowrocket, Clash Verge Rev (Mihomo) и XKeen (Xray),
построенные на manifest-driven distillate-пайплайне в `distillate/` с публикацией
consumer-списков в `rules/`. Проект поддерживает автообновление по URL и разделённую
маршрутизацию (Google/Gemini/YouTube, Microsoft и curated community/AI bundles).

Текущая ветка предназначена для source-изменений. Публичные raw URL продолжают
раздаваться из release-ветки `main`, поэтому ссылки вида
`https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/...` не меняются.

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
- `clash_config.yaml` — локальный YAML для Clash Verge Rev на общей базе Shadowrocket с локальными extras для voice/telegram.
- `XKeen/05_routing.json` — публикуемый Xray-routing для XKeen; в source-ветке он не хранится и собирается из базового `shadowrocket.conf`.
- `distillate/` — канонический manifest, overlays и filters; generated `upstream/text/dat/summary` публикуются только в release-ветку.
- `rules/` — вручную поддерживаемые rule-list'ы source-ветки и публикуемые generated consumer-списки release-ветки.

## Быстрый старт (Shadowrocket)

1. **Добавьте конфиг по ссылке** (Shadowrocket → Add Config/Добавить конфиг → URL):
   ```
   https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/shadowrocket.conf
   ```
   > В конфиге указан `update-url`, поэтому он будет обновляться автоматически.
2. **Добавьте подписку** на сервера в Shadowrocket (URL от вашего провайдера).
3. **Проверьте группы прокси**:
   - `AUTO-MAIN` — автоматический выбор по URL-тесту (только VLESS, исключает RU/BY/UA).
   - `AUTO-WL` — автоматический выбор только среди `WL`-узлов вне RU/BY/UA.
   - `WL` — ручной выбор узлов, чьё имя содержит `WL`.
   - `MANUAL-PROXY` — ручной выбор всех VLESS-узлов, включая RU/BY/UA.
   - `GOOGLE` — отдельный ручной выбор для Google/Gemini/YouTube (NL VLESS + UAE VLESS).
   - `PROXY` — главный переключатель (Select): по умолчанию выбран `AUTO-WL`; вручную можно переключаться между `AUTO-WL`, `AUTO-MAIN`, `WL`, `MANUAL-PROXY` и `DIRECT`.

Кастомный профиль для GFN/NVIDIA (с `always-real-ip`):
```
https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/shadowrocket_custom.conf
```

## Clash Verge Rev (Windows)

> Используется локальный `clash_config.yaml`, который следует общей логике `shadowrocket.conf`,
> но дополнительно хранит локальные Clash-only наборы `voice_ports` и `telegram`.
> Для автопроверки серверов секции `proxy-providers.Main-Sub.health-check` и `proxy-groups.AUTO-MAIN`
> используют `https://abs.twimg.com/favicon.ico` (интервал 780; для `AUTO-MAIN` tolerance 200).
> В него нужно вручную вставить ссылку на вашу подписку.

1. **Скачайте Clash Verge Rev**:  
   https://github.com/clash-verge-rev/clash-verge-rev/releases  
   Установите приложение.
2. **Включите режим TUN**. Если появится сообщение о нехватке драйвера:
   - нажмите на значок «гаечного ключа» рядом с тумблером TUN;
   - установите драйвер и дождитесь завершения.
3. **Подготовьте конфиг**:
   - скачайте файл `clash_config.yaml` из репозитория;
   - откройте его в редакторе и вставьте ссылку на свою подписку в соответствующее поле;
   - скрипт сборки больше не используется — конфиг редактируется вручную.
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
| `clash_config.yaml` | Локальный конфиг для Clash Verge Rev |
| `XKeen/05_routing.json` | Routing-конфиг для XKeen / Xray в release-ветке `main` |
| `distillate/` | Канонический manifest, overlays и filters; generated артефакты не коммитятся в source-ветку |
| `rules/` | Source rule-list'ы и публикуемые generated consumer-списки |
| `modules/` | Готовые модули для Shadowrocket |
| `scripts/` | Вспомогательные скрипты |

## Логика `shadowrocket.conf`

### [General]
- Базовые сетевые настройки: DNS — `77.88.8.8` и `8.8.8.8`, fallback — `tls://77.88.8.8` и `tls://8.8.8.8`, IPv6 выключен.
- `update-url` указывает на конфиг в репозитории.

### [Proxy Group]
- **AUTO-MAIN** — URL-тест с фильтром по имени (только VLESS, исключаем RU/BY/UA):
  `url=https://abs.twimg.com/favicon.ico`, `interval=780`, `tolerance=200`, `timeout=7`.
- **AUTO-WL** — URL-тест только по `WL`-узлам вне RU/BY/UA:
  `url=https://abs.twimg.com/favicon.ico`, `interval=780`, `tolerance=200`, `timeout=7`.
- **WL** — ручной выбор узлов по regex `(?i).*WL.*`.
- **MANUAL-PROXY** — ручной выбор всех VLESS-узлов, включая RU/BY/UA.
- **GOOGLE** — ручной выбор из отфильтрованного списка для Google/Gemini/YouTube (NL VLESS + UAE VLESS + узлы с `WL` в имени).
- **PROXY** — Select-группа; по умолчанию выбран AUTO-WL, вручную можно переключаться между AUTO-WL/AUTO-MAIN/WL/MANUAL-PROXY/DIRECT.

### [Rule]
Порядок важен: правила обрабатываются сверху вниз.

1. **Ручные overlays**
   - `distillate/overlays/whitelist_direct.add.list` — принудительно DIRECT.
   - Точечное DIRECT-исключение для Path of Exile (`DOMAIN-SUFFIX,pathofexile.com`, `DOMAIN-SUFFIX,poecdn.com`, плюс `DOMAIN-KEYWORD,pathofexile`) также ведётся через `whitelist_direct`.
   - Для точечных исключений локальных web-ui через внешние alias-домены (например, `73001ed9a665c420ee07c76a.netcraze.io`) используйте `whitelist_direct`.
   - `distillate/overlays/greylist_proxy.add.list` — принудительно PROXY.
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

Branch model:
- `main` — release/publish-ветка с неизменными public raw URL.
- `source/main` — shared source-of-truth.
- `custom/sergio` — personal source-ветка для GFN/NVIDIA и single-user изменений.

Подробности: [docs/branch-model.md](/Users/sergio/Documents/30_HOBBY_AI/shadorock/ShadowRocket/docs/branch-model.md)

- Конфиг обновляется автоматически через `update-url`.
- Канонический источник истины находится в `distillate/manifest.json`.
- `scripts/publish_release.py` собирает source-ветку во временный release workspace и публикует результат обратно в `main` только при содержательном diff.
- `scripts/sync_lists.py` подтягивает upstream-листы в локальный `distillate/upstream/*`, затем обновляет generated `distillate/text/*`, `distillate/summary.json` и `rules/*.list` для публикации.
- `scripts/build_distillate.py` работает только с уже закешированными файлами из `distillate/upstream/*` и собирает generated `distillate/text/*` плюс `distillate/dat/geosite.dat` и `distillate/dat/geoip.dat`.
- `scripts/build_xkeen_routing.py` читает порядок `[Rule]` из базового `shadowrocket.conf` и собирает `XKeen/05_routing.json` в том же порядке, резолвя связанные `rules/*.list`.
- `scripts/build_happ_routing.py` не ходит в BM7: он берет агрегаты `sr-direct`/`sr-proxy` и `motivato_block` из `distillate/text/*`, затем собирает `HAPP/DEFAULT.*` (`роут-MotivatoPotato`) с детерминированным `LastUpdated`.
- Антирекламный список собирается в том же distillate-пайплайне из OISD + HaGeZi, но публикуется чанками `rules/anti_advertising.01.list`, `.02.list`, `.03.list` и далее по мере необходимости. Количество чанков выбирается автоматически так, чтобы вес каждого был не больше примерно 7 МБ. Он не включается в compiled `geosite.dat` и не используется в HAPP. Для него предполагается отдельный модуль Shadowrocket.
- На этапе сборки из `anti_advertising` дополнительно вычищаются домены, содержащие `nvidia`/`geforce`/`geforcenow`/`nvidiagrid`, чтобы anti-ad модуль не ломал GeForce NOW и связанные NVIDIA API.
- Там же вычищаются official suffix'ы Discord (`discord.com`, `discord.gg`, `discordapp.com`, `discordapp.net` и смежные), чтобы upstream anti-ad не зацепил клиентские API, gateway и служебные поддомены Discord.

Fallback policy:
- если очередной upstream-лист недоступен, publish workflow использует последний snapshot из release-ветки `main`;
- сборка `distillate`, XKeen и HAPP продолжается на этой локальной копии;
- удаление cache-файла из-за временной недоступности upstream не допускается.

Локальная последовательность сборки:
```bash
python3 scripts/sync_lists.py --no-pull
python3 scripts/build_distillate.py
python3 scripts/build_xkeen_routing.py
python3 scripts/build_happ_routing.py
```

GitHub Actions:
- `.github/workflows/publish-release.yml` публикует shared артефакты из `source/main` по расписанию/вручную и обновляет custom release paths из `custom/sergio` по push/вручную.

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
Модуль подключает все доступные anti-ad чанки репозитория; в release-ветке список `RULE-SET` подставляется автоматически по фактически собранным файлам:
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
