# Инструкции для агентов

## Область действия
Эти правила применяются ко всему репозиторию.

## Общие принципы
- Сохраняйте смысл и порядок правил маршрутизации: порядок строк важен в конфигурациях Shadowrocket/Clash.
- Не добавляйте новые правила без явного указания пользователя.
- Предпочитайте минимальные изменения: не переформатируйте файлы без необходимости.
- Любое изменение по умолчанию нужно явно классифицировать как `shared` или `custom-only`.
- AmneziaVPN IPv4-профиль и его summary относятся к `shared` routing-артефактам.
- Изменения для GFN/NVIDIA и одного пользователя по умолчанию считаются `custom-only`.
- Если улучшение полезно всем, его нужно раскатывать и в основной конфиг, и в кастомные файлы.

## Git preflight и синхронизация между Mac

Перед любым изменением:

1. Выполните `git fetch --prune origin`.
2. Выполните `git status --short --branch` и `git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}'`.
3. Если рабочее дерево не чистое или upstream не настроен, остановитесь и покажите состояние. Не применяйте stash, reset или rebase автоматически.
4. Выполните `git rev-list --left-right --count HEAD...'@{upstream}'`.
5. Если локальная ветка содержит свои коммиты или история разошлась, остановитесь. Не используйте force-push.
6. Если локальная ветка только отстаёт, выполните `git pull --ff-only`.
7. Повторно проверьте, что текущая ветка соответствует задаче и имеет `0 ahead / 0 behind` относительно upstream.

Перед переходом на другой Mac завершите проверку, закоммитьте согласованные изменения и отправьте их в upstream. Не публикуйте private subscription, токены, ключи, Tailnet/SSH-параметры и machine-specific конфигурацию. Перед push проверьте `git diff --cached`.

## Падения CI

- Если job этого репозитория падает, агент должен сразу найти и исправить причину без дополнительного подтверждения пользователя.
- Агент должен обновить необходимые исходники, generated-артефакты, тесты и workflow, затем сделать commit/push и дождаться результата нового CI-запуска.
- Агент не должен обходить проверки, ослаблять security controls, использовать force-push, раскрывать секреты или выполнять destructive-действия. Если исправление требует таких действий либо новых внешних прав, агент должен остановиться и запросить разрешение.

## Источники истины
- `shadowrocket.conf` — source of truth для порядка `[Rule]`, inline-правил, `[General]` и `[Proxy Group]` базового профиля.
- `distillate/manifest.json` — source of truth для состава категорий, bucket'ов, publish-политики и generation большинства `rules/*.list`.
- `distillate/overlays/*.list` и `distillate/filters/*.list` — ручные входы distillate-сборки; содержимое generated-файлов меняется через них, а не через прямое редактирование итоговых артефактов.
- `shadowrocket_custom.conf` и `shadowrocket_custom_private_dns.conf` не генерируются из `shadowrocket.conf`; это отдельные `custom-only` профили, которые поддерживаются вручную.
- `shadowrocket_whitelist.conf` — отдельный `custom-only` whitelist-профиль: direct allowlist/RU идут напрямую, весь остальной трафик идёт через один выбранный `PROXY`.

## Форматирование и стиль
- Используйте LF и UTF-8.
- В конфигурациях (`shadowrocket.conf`, `shadowrocket_custom.conf`, `shadowrocket_custom_private_dns.conf`, `clash_config.yaml`) не меняйте секции местами и не переставляйте блоки.
- `clash_config.yaml` должен пересобираться из `shadowrocket.conf` через `scripts/build_clash_config.py`, а не поддерживаться вручную параллельно.
- В списках правил (`rules/*.list`) одна запись в строке, без лишних пробелов и комментариев, если не требуется.

## Структура репозитория
- `rules/`: часть списков поддерживается вручную, часть генерируется скриптами и коммитится в эту же ветку.
- `modules/`: модули Shadowrocket. Не ломайте совместимость с существующими конфигами.
- `scripts/`: вспомогательные утилиты; обновляйте README, если меняете публичный интерфейс скриптов.
- `distillate/upstream`, `distillate/text`, `distillate/dat`, `distillate/summary.json`, `distillate/upstream/v2fly/ru_ipv4.txt`, `Amnezia/SR-DEFAULT-EXCLUDE.json`, `Amnezia/SR-DEFAULT-EXCLUDE.summary.json`, `HAPP/DEFAULT.*`, `INCY/DEFAULT.*`, `INCY/RU-VPN.*`, `cloudflare/potato-link/dist/destinations.js`: generated-артефакты; при изменении сборки обновляйте их вместе с кодом.
- `clash_config.yaml`: generated-артефакт от `shadowrocket.conf` и Clash/Mihomo template-настроек; при изменении логики сборки обновляйте его вместе с кодом.

## Ownership файлов
- Редактируются вручную: `shadowrocket.conf`, `shadowrocket_custom.conf`, `shadowrocket_custom_private_dns.conf`, `shadowrocket_whitelist.conf`, `distillate/manifest.json`, `distillate/overlays/*`, `distillate/filters/*`, `rules/adobe_telemetry_custom.list`, `rules/russia_extended.list`, `rules/voice_ports.list`, `modules/GFN-AM.module`, `modules/tailscale_direct.module`, `modules/wechat_direct.module`.
- Generated, не редактировать вручную: `clash_config.yaml`, `HAPP/DEFAULT.*`, `INCY/DEFAULT.*`, `INCY/RU-VPN.*`, `distillate/text/**`, `distillate/dat/**`, `distillate/summary.json`, `distillate/upstream/v2fly/ru_ipv4.txt`, `Amnezia/SR-DEFAULT-EXCLUDE.json`, `Amnezia/SR-DEFAULT-EXCLUDE.summary.json`, `rules/google-all.list`, `rules/microsoft.list`, `rules/domains_community.list`, `rules/openai.list`, `rules/telegram.list`, `rules/whitelist_direct.list`, `rules/greylist_proxy.list`, `rules/anti_advertising*.list`.
- Semi-generated: `modules/anti_advertising.module` и `modules/anti_advertising_custom.module` хранят ручные заголовки и локальные исключения, но `RULE-SET` на anti-ad chunks переписываются сборкой.

## Документация
- При изменении поведения конфигов обновляйте README и указывайте, какие секции затронуты.

## Правила изменений
- Если нужно поменять содержимое generated `rules/*.list`, меняйте `distillate/manifest.json`, `distillate/overlays/*` или `distillate/filters/*`, а не итоговые списки.
- Если меняется routing-логика, полезная всем, синхронизируйте её в `shadowrocket.conf` и `shadowrocket_custom.conf`, но не перетирайте custom-only поля из `[General]` и custom `policy-select-name`.
- `shadowrocket_custom.conf`, `shadowrocket_custom_private_dns.conf`, `shadowrocket_whitelist.conf`, `modules/anti_advertising_custom.module`, `modules/wechat_direct.module`, `rules/adobe_telemetry_custom.list` и GFN/NVIDIA-исключения по умолчанию считаются `custom-only`.
- Не запускайте `scripts/sync_lists.py` без явного запроса на refresh vendored upstream. Для локальной детерминированной пересборки используйте закешированные `distillate/upstream/*` и `python3 scripts/build_distillate.py`.
- Если всё же нужен локальный sync, используйте `python3 scripts/sync_lists.py --no-pull`, чтобы не делать `git pull --rebase` автоматически.

## Каскад пересборки
- Изменили `shadowrocket.conf`: пересоберите `clash_config.yaml`, `HAPP/DEFAULT.*` и `INCY/*`.
- Пересобрали `HAPP/*.DEEPLINK` или `INCY/*.DEEPLINK`: запустите `python3 scripts/build_potato_link_worker.py` и закоммитьте `cloudflare/potato-link/dist/destinations.js`.
- Изменили `distillate/manifest.json`, `distillate/overlays/*`, `distillate/filters/*` или vendored upstream в `distillate/upstream/*`: пересоберите `distillate/text/*`, `distillate/dat/*`, `distillate/summary.json`, generated `rules/*.list`, anti-ad module refs, `HAPP/*` и `INCY/*`.
- Изменили `scripts/build_distillate.py`: проверьте, не затрагивает ли это `rules/*.list`, anti-ad chunking и `modules/anti_advertising*.module`.
- Изменили `scripts/build_distillate.py` или `scripts/build_amnezia_routing.py`: пересоберите cached RU IPv4 и `Amnezia/SR-DEFAULT-EXCLUDE*.json`; summary должен явно показывать domain DIRECT правила, которые не представлены в IPv4.
- Изменили набор generated outputs или build inputs: обновите `.github/workflows/*.yml` path-фильтры и списки `git add`.

## Тесты/проверки
- Автоматические тесты обязательны: `python3 -m unittest discover -s tests -v` и `python3 -m compileall -q scripts tests`.
- Считайте только tracked-тесты (`git ls-files 'tests/test_*.py'`); локальные ignored-проверки не включайте в отчёт CI.
- Каждый тест должен владеть отдельным пользовательским контрактом, security/data-loss риском, fail-closed границей или межартефактной инвариантой.
- Объединяйте табличные варианты одного поведения. Не дублируйте инварианту на нескольких уровнях без отдельного риска каждого уровня.
- Не тестируйте константу ради константы, форматирование/документацию без исполняемого контракта, стандартную библиотеку или модель внешней программы, написанную внутри самого теста.
- После изменения `shadowrocket.conf` запускайте:
  - `python3 scripts/build_clash_config.py`
  - `python3 scripts/build_happ_routing.py`
  - `python3 scripts/build_incy_routing.py`
- После изменения `distillate/manifest.json`, `distillate/overlays/*`, `distillate/filters/*` или vendored upstream запускайте:
  - `python3 scripts/build_distillate.py`
  - `python3 scripts/build_amnezia_routing.py`
  - `python3 scripts/build_happ_routing.py`
  - `python3 scripts/build_incy_routing.py`
- Для отдельной проверки Amnezia: `python3 scripts/build_amnezia_routing.py`, затем проверьте JSON-массив `{ "hostname": "cidr-...invalid", "ip": "CIDR" }`, IPv4-only canonical CIDR и summary.
- Если менялся weekly sync flow, отдельно проверяйте `python3 scripts/sync_lists.py --no-pull`.
- При возможности указывайте ручные шаги проверки, например импорт конфига в Shadowrocket/Clash или проверку обновлённых generated-артефактов.
