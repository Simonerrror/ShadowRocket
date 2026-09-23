# Сборка и сопровождение

## Структура репозитория

| Путь | Назначение |
| --- | --- |
| `shadowrocket.conf` | Основной конфиг для Shadowrocket |
| `shadowrocket_custom.conf` | Прежний адрес профиля; новые установки используют основной конфиг |
| `clash_config.yaml` | Generated-конфиг для Clash Verge Rev |
| `shadowrocket_whitelist.conf` | Custom-only аварийный whitelist-профиль: direct allowlist/RU напрямую, всё остальное через один `PROXY` |
| `INCY/DEFAULT.*`, `INCY/RU-VPN.*` | Generated routing-профили и `incy://` deeplink для INCY |
| `distillate/` | Канонический manifest, overlays и generated артефакты |
| `rules/` | Вручную поддерживаемые и generated consumer-списки |
| `modules/` | Готовые модули для Shadowrocket |
| `scripts/` | Вспомогательные скрипты |

Практическое правило сопровождения:
- вручную редактируются `shadowrocket.conf`, `shadowrocket_custom.conf`, `shadowrocket_whitelist.conf`, `distillate/manifest.json`, `distillate/overlays/*`, `distillate/filters/*`, `rules/russia_extended.list`, `rules/voice_ports.list`, `modules/GFN-AM.module`, `modules/tailscale_tailnet.module`, `modules/wechat_direct.module`, `modules/tailscale_direct.module`;
- generated-артефакты (`clash_config.yaml`, `HAPP/DEFAULT.*`, `INCY/DEFAULT.*`, `INCY/RU-VPN.*`, `distillate/text/**`, `distillate/dat/**`, `distillate/summary.json`, `rules/google-all.list`, `rules/microsoft.list`, `rules/domains_community.list`, `rules/openai.list`, `rules/telegram.list`, `rules/whitelist_direct.list`, `rules/torrent_block.list`, `rules/greylist_proxy.list`, `rules/anti_advertising.list`, `rules/anti_advertising*.[0-9][0-9].list`) не поддерживаются вручную;
- `modules/anti_advertising.module` semi-generated: ручной заголовок сохраняется, а ссылки на anti-ad chunks переписываются сборкой.
- Tailscale вынесен из общих профилей в отдельный модуль `modules/tailscale_tailnet.module`. Модуль использует встроенную политику `TAILSCALE`; `100.64.0.0/10` не добавляется в `tun-excluded-routes`.

Основной и custom-профиль остаются отдельными ручными исходниками. Shared-изменения
вносятся в оба файла с сохранением custom-only настроек. `distillate/`, полный
anti-ad-список и его чанки в `rules/` сохраняются как входы сборки и публикуемые артефакты.

## Обновление

- Конфиг обновляется автоматически через `update-url`.
- Канонические источники истины разделены: `shadowrocket.conf` задаёт routing order и базовые proxy-groups, `distillate/manifest.json` задаёт состав категорий и generation rule-list'ов.
- Weekly workflow запускает `scripts/sync_lists.py --no-pull`: скрипт подтягивает upstream-листы в `distillate/upstream/*`, затем обновляет `distillate/text/*`, `distillate/summary.json`, `rules/*.list`, anti-ad module refs. Остальные артефакты собираются следующими шагами workflow.
- `scripts/build_distillate.py --skip-compiled` пересобирает текстовые артефакты из кэша `distillate/upstream/*` без сетевого обновления. Без `--skip-compiled` скрипт также загружает закреплённые исходники Go-компиляторов и их зависимости для сборки `geosite.dat` и `geoip.dat`.
- `scripts/build_clash_config.py` читает `[General]`, `[Proxy Group]` и `[Rule]` из базового `shadowrocket.conf` и пересобирает `clash_config.yaml` для Mihomo.
  Он переносит все поддерживаемые rule/group mapping'и, а неподдерживаемые для Clash детали (`force-remote-dns`, `policy-select-name`, `timeout`) оставляет в предупреждениях сборки.
- `scripts/build_happ_routing.py` не ходит в BM7: он берет агрегаты `sr-direct`/`sr-proxy` и `motivato_block` из `distillate/text/*`, затем собирает `HAPP/DEFAULT.*` (`роут-MotivatoPotato`) с детерминированным `LastUpdated`.
- `scripts/build_incy_routing.py` использует те же агрегаты и семантические профили, адаптирует только поле `useChunkFiles: false` и собирает `INCY/DEFAULT.*` и `INCY/RU-VPN.*` с тем же `LastUpdated`.
- Антирекламный список собирается в том же distillate-пайплайне из OISD + HaGeZi, но публикуется чанками `rules/anti_advertising.01.list`, `.02.list`, `.03.list` и далее по мере необходимости. Количество чанков выбирается автоматически так, чтобы вес каждого был не больше примерно 7 МБ. Он не включается в compiled `geosite.dat` и не используется в HAPP. Для него предполагается отдельный модуль Shadowrocket.
- На этапе сборки из `anti_advertising` дополнительно вычищаются домены, содержащие `nvidia`/`geforce`/`geforcenow`/`nvidiagrid`, чтобы anti-ad модуль не ломал GeForce NOW и связанные NVIDIA API.
- Там же вычищаются official suffix'ы Discord (`discord.com`, `discord.gg`, `discordapp.com`, `discordapp.net` и смежные), чтобы upstream anti-ad не зацепил клиентские API, gateway и служебные поддомены Discord.

Fallback policy:
- если очередной upstream-лист недоступен, последний закоммиченный snapshot в `distillate/upstream/*` сохраняется;
- сборка `distillate` и HAPP продолжается на этой локальной копии;
- удаление cache-файла из-за временной недоступности upstream не допускается.

Правило безопасного локального запуска:
- не запускайте `scripts/sync_lists.py` без необходимости refresh vendored upstream: по умолчанию он делает `git pull --rebase`;
- для локальной пересборки без загрузки компиляторов используйте `python3 scripts/build_distillate.py --skip-compiled` на уже закешированных `distillate/upstream/*`;
- если нужен локальный sync без обновления ветки, используйте `python3 scripts/sync_lists.py --no-pull`.

### Кэшированная пересборка

Запускайте из корня репозитория. Команды используют существующие `distillate/dat/*`
и не перекомпилируют геоданные. Для изменившихся правил полная публикация требует
пересборки `.dat` в release workflow.

```bash
python3 scripts/build_distillate.py --skip-compiled
python3 scripts/build_clash_config.py
python3 scripts/build_happ_routing.py
python3 scripts/build_incy_routing.py
python3 scripts/build_potato_link_worker.py
```

После пересборки выполните `python3 -m unittest discover -s tests -v` и
`python3 -m compileall -q scripts tests`, затем проверьте diff.
Генераторы HAPP/INCY должны остановиться при отсутствии обязательных текстовых входов;
не заменяйте отсутствующие файлы пустыми ради прохождения сборки.

### Обновление источников и полная сборка

Для явного обновления upstream сначала запустите `python3 scripts/sync_lists.py --no-pull`.
Затем выполните `python3 scripts/build_distillate.py` и остальные команды кэшированной
Go и сетевого доступа; новые зависимости проверяются по правилам проекта.
Обновление источников, сборка и публикация — отдельные операции.

### GitHub Actions

- `.github/workflows/sync-lists.yml` запускается по weekly cron или вручную через **Run workflow**. Read-only job получает плавающие публичные данные BM7/OISD/HaGeZi, собирает их закреплёнными версиями компиляторов, проверяет тесты и допустимый размер diff; отдельная write-job публикует только generated allowlist.
- Для проверенного резкого изменения количества правил ручной запуск поддерживает `allow_large_diff`; пустые обязательные категории, неверный формат и запрещённые пути этот флаг не разрешает.
- При ошибке или аномалии workflow создаёт GitHub issue со ссылкой на run, поэтому уведомление приходит через стандартные GitHub notifications/email.
- `.github/workflows/build-happ-routing.yml` — read-only проверка cached rebuild и тестов; она ничего не коммитит.
- HAPP и INCY-профили относятся к shared routing-артефактам; при изменении входов оба генератора и Worker-пакет пересобираются вместе.

Политика изменений:
- Изменение групп `MANUAL-PROXY`, `WL` и auto-фильтра — **shared**: синхронизировано в `shadowrocket.conf` и `shadowrocket_custom.conf`; custom-only поля `[General]` сохранены.
- `shadowrocket_custom.conf`, `shadowrocket_whitelist.conf` считаются `custom-only`.
- Если улучшение полезно всем, его нужно переносить и в основной конфиг, и в кастомные файлы.
- При изменении generated `rules/*.list` меняйте `distillate/manifest.json`, `distillate/overlays/*` или `distillate/filters/*`, а не итоговые generated-файлы.
- При изменении `shadowrocket.conf` пересобирайте `clash_config.yaml`, `HAPP/DEFAULT.*` и `INCY/*`.
- При изменении `distillate/manifest.json`, `distillate/overlays/*`, `distillate/filters/*` или vendored upstream пересобирайте `distillate/*`, generated `rules/*.list`, anti-ad module refs, `HAPP/*` и `INCY/*`.

## Неизвестное поведение Shadowrocket

Если непонятны параметры, порядок правил, DNS, модули или поддержка протокола,
сначала проверьте [репозиторий руководства LOWERTOP/Shadowrocket](https://github.com/LOWERTOP/Shadowrocket)
и [официальный новостной канал Shadowrocket News](https://t.me/ShadowrocketNews).
Руководство поддерживает сообщество; это не исходный код приложения.
Дополнительный источник — [Shadowrocket/manual](https://github.com/Shadowrocket/manual).

Сопоставьте описание с установленной версией и номером сборки: изменения TestFlight
не доказывают наличие функции в стабильном выпуске. Если источники не дают ответа,
зафиксируйте неопределённость и проверьте поведение на минимальном примере в приложении.
Не переносите семантику Clash, HAPP или INCY на Shadowrocket без проверки.


## Расширение правил

Если нужно добавить сервис, добавьте категорию в `distillate/manifest.json` и при необходимости вход в `distillate/overlays/*.list`. Подключите сгенерированный список в `[Rule]`, если маршрут требует отдельного правила.
