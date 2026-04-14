# Инструкции для агентов

## Область действия
Эти правила применяются ко всему репозиторию.

## Общие принципы
- Сохраняйте смысл и порядок правил маршрутизации: порядок строк важен в конфигурациях Shadowrocket/Clash.
- Не добавляйте новые правила без явного указания пользователя.
- Предпочитайте минимальные изменения: не переформатируйте файлы без необходимости.
- Любое изменение по умолчанию нужно явно классифицировать как `shared` или `custom-only`.
- Изменения для GFN/NVIDIA и одного пользователя по умолчанию считаются `custom-only`.
- Если улучшение полезно всем, его нужно раскатывать и в основной конфиг, и в кастомные файлы.

## Источники истины
- `shadowrocket.conf` — source of truth для порядка `[Rule]`, inline-правил, `[General]` и `[Proxy Group]` базового профиля.
- `distillate/manifest.json` — source of truth для состава категорий, bucket'ов, publish-политики и generation большинства `rules/*.list`.
- `distillate/overlays/*.list` и `distillate/filters/*.list` — ручные входы distillate-сборки; содержимое generated-файлов меняется через них, а не через прямое редактирование итоговых артефактов.
- `shadowrocket_custom.conf` не генерируется из `shadowrocket.conf`; это отдельный `custom-only` профиль, который поддерживается вручную.

## Форматирование и стиль
- Используйте LF и UTF-8.
- В конфигурациях (`shadowrocket.conf`, `shadowrocket_custom.conf`, `clash_config.yaml`) не меняйте секции местами и не переставляйте блоки.
- `clash_config.yaml` должен пересобираться из `shadowrocket.conf` через `scripts/build_clash_config.py`, а не поддерживаться вручную параллельно.
- В списках правил (`rules/*.list`) одна запись в строке, без лишних пробелов и комментариев, если не требуется.

## Структура репозитория
- `rules/`: часть списков поддерживается вручную, часть генерируется скриптами и коммитится в эту же ветку.
- `modules/`: модули Shadowrocket. Не ломайте совместимость с существующими конфигами.
- `scripts/`: вспомогательные утилиты; обновляйте README, если меняете публичный интерфейс скриптов.
- `distillate/upstream`, `distillate/text`, `distillate/dat`, `distillate/summary.json`, `HAPP/DEFAULT.*`: generated-артефакты; при изменении сборки обновляйте их вместе с кодом.
- `clash_config.yaml`: generated-артефакт от `shadowrocket.conf` и Clash/Mihomo template-настроек; при изменении логики сборки обновляйте его вместе с кодом.

## Ownership файлов
- Редактируются вручную: `shadowrocket.conf`, `shadowrocket_custom.conf`, `distillate/manifest.json`, `distillate/overlays/*`, `distillate/filters/*`, `rules/adobe_telemetry_custom.list`, `rules/russia_extended.list`, `rules/voice_ports.list`, `modules/GFN-AM.module`.
- Generated, не редактировать вручную: `clash_config.yaml`, `HAPP/DEFAULT.*`, `distillate/text/**`, `distillate/dat/**`, `distillate/summary.json`, `rules/google-all.list`, `rules/microsoft.list`, `rules/domains_community.list`, `rules/telegram.list`, `rules/whitelist_direct.list`, `rules/greylist_proxy.list`, `rules/anti_advertising*.list`.
- `XKeen/local/*`, `XKeen/singles/*`, `XKeen/diagnostics/*` и `XKeen/sub/*` — `custom-only`; это локальные файлы, не часть публичного release-контура.
- Semi-generated: `modules/anti_advertising.module` и `modules/anti_advertising_custom.module` хранят ручные заголовки и локальные исключения, но `RULE-SET` на anti-ad chunks переписываются сборкой.

## Документация
- При изменении поведения конфигов обновляйте README и указывайте, какие секции затронуты.

## Правила изменений
- Если нужно поменять содержимое generated `rules/*.list`, меняйте `distillate/manifest.json`, `distillate/overlays/*` или `distillate/filters/*`, а не итоговые списки.
- Если меняется routing-логика, полезная всем, синхронизируйте её в `shadowrocket.conf` и `shadowrocket_custom.conf`, но не перетирайте custom-only поля из `[General]` и custom `policy-select-name`.
- `shadowrocket_custom.conf`, `modules/anti_advertising_custom.module`, `rules/adobe_telemetry_custom.list` и GFN/NVIDIA-исключения по умолчанию считаются `custom-only`.
- Не запускайте `scripts/sync_lists.py` без явного запроса на refresh vendored upstream. Для локальной детерминированной пересборки используйте закешированные `distillate/upstream/*` и `python3 scripts/build_distillate.py`.
- Если всё же нужен локальный sync, используйте `python3 scripts/sync_lists.py --no-pull`, чтобы не делать `git pull --rebase` автоматически.

## Каскад пересборки
- Изменили `shadowrocket.conf`: пересоберите `clash_config.yaml` и `HAPP/DEFAULT.*`.
- Изменили `distillate/manifest.json`, `distillate/overlays/*`, `distillate/filters/*` или vendored upstream в `distillate/upstream/*`: пересоберите `distillate/text/*`, `distillate/dat/*`, `distillate/summary.json`, generated `rules/*.list`, anti-ad module refs и `HAPP/DEFAULT.*`.
- Изменили `scripts/build_distillate.py`: проверьте, не затрагивает ли это `rules/*.list`, anti-ad chunking и `modules/anti_advertising*.module`.
- Изменили набор generated outputs или build inputs: обновите `.github/workflows/*.yml` path-фильтры и списки `git add`.

## Тесты/проверки
- Автоматические тесты отсутствуют, но build-check обязателен после изменений в сборке или routing-логике.
- После изменения `shadowrocket.conf` запускайте:
  - `python3 scripts/build_clash_config.py`
  - `python3 scripts/build_happ_routing.py`
- После изменения `distillate/manifest.json`, `distillate/overlays/*`, `distillate/filters/*` или vendored upstream запускайте:
  - `python3 scripts/build_distillate.py`
  - `python3 scripts/build_happ_routing.py`
- Если менялся weekly sync flow, отдельно проверяйте `python3 scripts/sync_lists.py --no-pull`.
- При возможности указывайте ручные шаги проверки, например импорт конфига в Shadowrocket/Clash/XKeen или проверку обновлённых generated-артефактов.
