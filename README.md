# ShadowRocket: конфиг и правила маршрутизации

Готовые конфиги для Shadowrocket и Clash Verge Rev (Mihomo), построенные на manifest-driven
distillate-пайплайне в `distillate/` с публикацией consumer-списков в `rules/`.
Проект поддерживает автообновление по URL и разделённую маршрутизацию (Google/Gemini/YouTube,
Microsoft и curated community/AI bundles).

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
- `clash_config.yaml` — локальный YAML для Clash Verge Rev, повторяющий логику Shadowrocket.
- `distillate/` — канонический manifest, локальные overlays и собранные text/`mrs`/`srs`/`dat`.
- `rules/` — публикуемые consumer-списки для Shadowrocket/Clash, генерируются из `distillate/`.

## Быстрый старт (Shadowrocket)

1. **Добавьте конфиг по ссылке** (Shadowrocket → Add Config/Добавить конфиг → URL):
   ```
   https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/shadowrocket.conf
   ```
   > В конфиге указан `update-url`, поэтому он будет обновляться автоматически.
2. **Добавьте подписку** на сервера в Shadowrocket (URL от вашего провайдера).
3. **Проверьте группы прокси**:
   - `AUTO-MAIN` — автоматический выбор по URL-тесту (только VLESS, исключает RU/BY/UA).
   - `MANUAL-PROXY` — ручной выбор из тех же серверов, что и `AUTO-MAIN`.
   - `GOOGLE` — отдельный ручной выбор для Google/Gemini/YouTube (NL VLESS + UAE VLESS).
   - `PROXY` — главный переключатель (Select): `AUTO-MAIN`, `MANUAL-PROXY` или `DIRECT`.

Кастомный профиль для GFN/NVIDIA (с `always-real-ip`):
```
https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/shadowrocket_custom.conf
```

## Clash Verge Rev (Windows)

> Используется локальный `clash_config.yaml`, который повторяет логику `shadowrocket.conf`.
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
| `distillate/` | Канонический manifest, overlays и собранные артефакты |
| `rules/` | Генерируемые consumer-списки для Shadowrocket/Clash |
| `modules/` | Готовые модули для Shadowrocket |
| `scripts/` | Вспомогательные скрипты |

## Логика `shadowrocket.conf`

### [General]
- Базовые сетевые настройки: DNS — `77.88.8.8` и `8.8.8.8`, fallback — `tls://77.88.8.8` и `tls://8.8.8.8`, IPv6 выключен.
- `update-url` указывает на конфиг в репозитории.

### [Proxy Group]
- **AUTO-MAIN** — URL-тест с фильтром по имени (только VLESS, исключаем RU/BY/UA):
  `url=https://abs.twimg.com/favicon.ico`, `interval=780`, `tolerance=200`, `timeout=7`.
- **MANUAL-PROXY** — ручной выбор из тех же серверов, что и AUTO-MAIN.
- **GOOGLE** — ручной выбор из отфильтрованного списка для Google/Gemini/YouTube (NL VLESS + UAE VLESS).
- **PROXY** — Select-группа для ручного выбора между AUTO-MAIN/MANUAL-PROXY/DIRECT.

### [Rule]
Порядок важен: правила обрабатываются сверху вниз.

1. **Ручные overlays**
   - `distillate/overlays/whitelist_direct.add.list` — принудительно DIRECT.
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

- Конфиг обновляется автоматически через `update-url`.
- Канонический источник истины находится в `distillate/manifest.json`.
- `scripts/sync_lists.py` раз в неделю подтягивает upstream-листы в `distillate/upstream/*`, затем обновляет `distillate/text/*`, `distillate/summary.json` и публикуемые `rules/*.list`.
- `scripts/build_distillate.py` работает только с уже закешированными файлами из `distillate/upstream/*` и собирает канонические `distillate/text/*` плюс `distillate/dat/geosite.dat` и `distillate/dat/geoip.dat`.
- `scripts/build_happ_routing.py` не ходит в BM7: он берет агрегаты `sr-direct`/`sr-proxy` и `motivato_block` из `distillate/text/*`, затем собирает локальный `HAPP/DEFAULT.*` (`роут-MotivatoPotato`).
- Антирекламный список `rules/anti_advertising.list` собирается в том же distillate-пайплайне из OISD + HaGeZi, но не включается в compiled `geosite.dat` и не используется в HAPP. Для него предполагается отдельный модуль Shadowrocket.

Fallback policy:
- если weekly sync не может скачать очередной upstream-лист, последний закоммиченный файл в `distillate/upstream/*` сохраняется;
- сборка `distillate` и HAPP продолжается на этой локальной копии;
- удаление cache-файла из-за временной недоступности upstream не допускается.

Локальная последовательность сборки:
```bash
python3 scripts/sync_lists.py --no-pull
python3 scripts/build_distillate.py
python3 scripts/build_happ_routing.py
```

GitHub Actions:
- `.github/workflows/sync-lists.yml` запускается вручную или по weekly cron и обновляет vendored upstream + `distillate/*` + `rules/*.list`.
- `.github/workflows/build-happ-routing.yml` запускается по push/вручную и собирает только `HAPP/*` из уже закоммиченного `distillate/`.

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
Модуль подключает единый сгенерированный список репозитория:
```
https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/anti_advertising.list
```
Как добавить модуль в Shadowrocket:
1. Откройте **Config → Modules**.
2. В правом верхнем углу нажмите **Add/Добавить**.
3. Вставьте ссылку на модуль и подтвердите загрузку.
4. Нажмите на загруженный модуль, чтобы активировать его.

Модуль работает в дополнение к любому активному конфигу и не заменяет его.
