# ShadowRocket: конфиг и правила маршрутизации

Готовые конфиги для Shadowrocket и Clash Verge Rev (Mihomo),
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
- `distillate/` — канонический manifest, локальные overlays и собранные text/`dat`.
- `rules/` — вручную поддерживаемые rule-list'ы и generated consumer-списки.
- `HAPP/RU-VPN.*` — дополнительный HAPP-профиль: российские домены/IP через proxy, остальное напрямую.
- `modules/tailscale_direct.module` — отдельный модуль DIRECT для Tailscale tailnet (`100.64.0.0/10`, `100.100.100.100`, `ts.net`, `tailscale.com`).
- `modules/wechat_direct.module` — отдельный custom-only модуль DIRECT для WeChat и его CDN без широкого обхода всего Tencent/QQ.
- Источники истины разделены: `shadowrocket.conf` отвечает за порядок routing-правил и proxy-groups базового профиля, а `distillate/manifest.json` вместе с `distillate/overlays/*` и `distillate/filters/*` отвечает за состав и сборку большинства consumer-списков.

## Быстрый старт (Shadowrocket)

1. **Добавьте конфиг по ссылке** (Shadowrocket → Add Config/Добавить конфиг → URL):
   ```
   https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/shadowrocket.conf
   ```
   > В конфиге указан `update-url`, поэтому он будет обновляться автоматически.
2. **Добавьте подписку** на сервера в Shadowrocket (URL от вашего провайдера).
   В `_custom` профилях локальные группы берут только `WL`-узлы и дополнительно исключают `Russia`, чтобы авто-выбор не цеплял РФ-узлы из подписки.
3. **Проверьте группы прокси**:
   - `MANUAL-PROXY` — ручной выбор `WL`-узлов подписки.
   - `AUTO-SPEED` — `url-test`: выбирает самый быстрый живой `WL`-узел.
   - `AUTO-STABILITY` — `fallback`: берёт первый живой `WL`-узел в порядке подписки.
   - `GOOGLE` — отдельный ручной выбор узла для Google/Gemini/YouTube.
   - В основном профиле четыре группы используют простой `policy-regex-filter=WL`. В `_custom` профилях применяется `(?i)^(?!.*Russia).*WL.*$`, чтобы дополнительно исключить РФ-ноды.
   - `PROXY` — главный переключатель (Select): по умолчанию выбран `AUTO-STABILITY`; вручную можно переключаться между `MANUAL-PROXY`, `AUTO-SPEED`, `AUTO-STABILITY` и `DIRECT`.

Кастомный профиль для GFN/NVIDIA (с `always-real-ip`, тем же DNS-набором, что и основной профиль, и `dns-direct-system = false`):
```
https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/shadowrocket_custom.conf
```

Кастомный SR-профиль для GFN/NVIDIA с приватными DoH/DoT без plain DNS (Mullvad + Quad9, `dns-direct-system = false`):
```
https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/shadowrocket_custom_private_dns.conf
```

Аварийный whitelist-only профиль, когда не нужны отдельные Google/Microsoft группы:
```
https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/shadowrocket_whitelist.conf
```
В нём остаются только локальные исключения, `whitelist_direct.list`, `.ru/.рф/.su` и `GEOIP,RU,DIRECT`; весь Google и любой другой non-direct трафик уходит в `PROXY`. После импорта выберите в группе `PROXY` любой доступный узел с маркером `WL`: публичный профиль не закрепляет имя конкретного часто меняющегося узла.

Дополнительный HAPP-профиль для доступа к российским ресурсам через
российский VPN-узел:
```
https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/HAPP/RU-VPN.DEEPLINK
```
`RU-VPN` направляет `geosite:category-ru` и `geoip:ru` через выбранный proxy,
а весь несовпавший трафик — напрямую. Профиль выбирает трафик, но не страну
сервера: перед активацией выберите узел с проверенным российским выходным IP.

## Clash Verge Rev (Windows)

> `clash_config.yaml` больше не поддерживается вручную отдельно: он генерируется из
> `shadowrocket.conf` через `scripts/build_clash_config.py`.
> Для автопроверки серверов `proxy-providers.Main-Sub.health-check`, `proxy-groups.AUTO-SPEED`,
> `proxy-groups.AUTO-STABILITY` используется `https://abs.twimg.com/favicon.ico`
> (`AUTO-SPEED`: интервал 300, tolerance 200; `AUTO-STABILITY`: интервал 780).

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
| `distillate/` | Канонический manifest, overlays и generated артефакты |
| `rules/` | Вручную поддерживаемые и generated consumer-списки |
| `modules/` | Готовые модули для Shadowrocket |
| `scripts/` | Вспомогательные скрипты |

Практическое правило сопровождения:
- вручную редактируются `shadowrocket.conf`, `shadowrocket_custom.conf`, `shadowrocket_custom_private_dns.conf`, `shadowrocket_whitelist.conf`, `distillate/manifest.json`, `distillate/overlays/*`, `distillate/filters/*`, `rules/adobe_telemetry_custom.list`, `rules/russia_extended.list`, `rules/voice_ports.list`, `modules/GFN-AM.module`, `modules/tailscale_direct.module`, `modules/wechat_direct.module`;
- generated-артефакты (`clash_config.yaml`, `HAPP/DEFAULT.*`, `distillate/text/**`, `distillate/dat/**`, `distillate/summary.json`, `rules/google-all.list`, `rules/microsoft.list`, `rules/domains_community.list`, `rules/openai.list`, `rules/telegram.list`, `rules/whitelist_direct.list`, `rules/greylist_proxy.list`, `rules/anti_advertising.list`, `rules/anti_advertising*.[0-9][0-9].list`) не поддерживаются вручную;
- `modules/anti_advertising.module` и `modules/anti_advertising_custom.module` semi-generated: ручной заголовок сохраняется, а ссылки на anti-ad chunks переписываются сборкой.
- Tailscale DIRECT вынесен из custom-профиля в отдельный модуль `modules/tailscale_direct.module`.

### WeChat напрямую

Если при активном VPN в WeChat не загружаются сообщения, изображения или
мини-программы, подключите отдельный модуль:

```text
https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/modules/wechat_direct.module
```

В Shadowrocket откройте **Config → Modules → Add**, вставьте URL и включите
модуль. Если одновременно используется anti-advertising модуль, расположите
`WeChat Direct` выше anti-advertising, чтобы DIRECT-правила применялись раньше
блокирующих правил. Модуль направляет напрямую только домены WeChat и нужные
CDN; весь Tencent/QQ он не обходит.

## Логика `shadowrocket.conf`

### [General]
- Базовые сетевые настройки: DNS — `9.9.9.9`, `149.112.112.112`, `77.88.8.8`; fallback использует тот же набор, IPv6 выключен.
- Основной и custom-профиль используют общий DNS/skip/bypass каркас; `shadowrocket_custom_private_dns.conf` остаётся отдельной DoH/DoT альтернативой.
- GFN/NVIDIA `always-real-ip` остаётся custom-only и не переносится в основной профиль.
- `update-url` указывает на конфиг в репозитории.

### [Proxy Group]
- **MANUAL-PROXY** — ручной выбор `WL`-узлов подписки вне РФ; `_custom` профили используют `policy-regex-filter=(?i)^(?!.*Russia).*WL.*$`.
- **AUTO-SPEED** — `url-test`-группа для выбора самого быстрого живого узла из подписки:
  `url=https://abs.twimg.com/favicon.ico`, `interval=300`, `tolerance=200`, `timeout=7`.
- **AUTO-STABILITY** — `fallback`-группа для выбора первого живого узла в порядке подписки:
  `url=https://abs.twimg.com/favicon.ico`, `interval=780`, `timeout=7`.
- **GOOGLE** — отдельная `select`-группа для ручного выбора узла под Google/Gemini/YouTube; `_custom` профили наполняют её `WL`-узлами вне РФ.
- **PROXY** — Select-группа; по умолчанию выбран `AUTO-STABILITY`, вручную можно переключаться между `MANUAL-PROXY`/`AUTO-SPEED`/`AUTO-STABILITY`/`DIRECT`.
  В `AUTO-STABILITY` первичным считается первый живой узел в порядке уже фильтрованной подписки.

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
- сборка `distillate` и HAPP продолжается на этой локальной копии;
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
- `.github/workflows/sync-lists.yml` запускается по weekly cron или вручную через **Run workflow**. Read-only job получает плавающие публичные данные BM7/OISD/HaGeZi, собирает их закреплёнными версиями компиляторов, проверяет тесты и допустимый размер diff; отдельная write-job публикует только generated allowlist.
- Для проверенного резкого изменения количества правил ручной запуск поддерживает `allow_large_diff`; пустые обязательные категории, неверный формат и запрещённые пути этот флаг не разрешает.
- При ошибке или аномалии workflow создаёт GitHub issue со ссылкой на run, поэтому уведомление приходит через стандартные GitHub notifications/email.
- `.github/workflows/build-happ-routing.yml` — read-only проверка cached rebuild и тестов; она ничего не коммитит.

Политика изменений:
- `shadowrocket_custom.conf`, `shadowrocket_custom_private_dns.conf`, `shadowrocket_whitelist.conf` и `modules/anti_advertising_custom.module` считаются `custom-only` и содержат single-user/GFN логику.
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
