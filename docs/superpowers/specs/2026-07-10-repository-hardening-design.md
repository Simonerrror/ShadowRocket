# ShadowRocket Repository Hardening Design

## Цель

Сохранить автоматическую еженедельную публикацию публичных routing-листов, но отделить получение и сборку недоверенных upstream-данных от job с правом записи. Одновременно убрать XKeen из публичного репозитория, сделать distillate-сборку атомарной, подключить тесты к CI, устранить дрейф HAPP и убрать персональный default-узел из whitelist-профиля.

## Границы работы

В scope входят:

- публичный репозиторий `ShadowRocket`;
- локальная приватная область `../ShadowRocket_private/XKeen`;
- weekly и manual GitHub Actions;
- `sync_lists.py`, `build_distillate.py`, `build_happ_routing.py`;
- тесты, README и агентские инструкции.

В scope не входят:

- новая схема VPN для роутера;
- домашний туннель;
- мониторинг приватной подписки;
- изменение текущей Shadowrocket routing-политики, кроме переносимого выбора узла в whitelist-профиле.

## Архивация XKeen

Публичный XKeen-контур удаляется полностью:

- `XKeen/`;
- `scripts/build_xkeen_local.py`;
- `tests/test_build_xkeen_local.py`;
- упоминания XKeen в публичной документации и инструкциях.

Перед удалением создаётся точный архив в:

`../ShadowRocket_private/XKeen/archive/legacy-generator-2026-07-10/`

Архив содержит:

- `scripts/build_xkeen_local.py`;
- `scripts/build_clash_config.py`, от которого зависит генератор;
- `tests/test_build_xkeen_local.py`;
- архивный README с явным статусом `deprecated / unsupported` и командой запуска тестов из каталога архива.

Существующие приватные подписки, `local/`, `singles/`, `diagnostics/` и `example/` не перезаписываются. Архив не подключается к публичному CI и не поддерживается до отдельного решения по роутерному VPN.

## Модель доверия weekly pipeline

Публичные данные BM7, OISD и HaGeZi остаются плавающими: их обновление является основной функцией репозитория. Исполняемый код фиксируется:

- GitHub Actions указываются по immutable commit SHA с комментарием о major release;
- `v2fly/domain-list-community` и `v2fly/geoip` checkout выполняется на явно заданных reviewed commit SHA;
- Go dependencies контролируются upstream `go.mod` и `go.sum` выбранного commit.

Pipeline разделяется на jobs:

1. `build` получает только `contents: read`, checkout выполняется с `persist-credentials: false`.
2. `build` загружает публичные листы, запускает validators, тесты и полную сборку в staging-каталоге.
3. Разрешённые outputs передаются через artifact с фиксированным списком путей.
4. `publish` получает `contents: write`, скачивает только этот artifact в чистый checkout, проверяет allowlist путей и коммитит изменения.
5. `notify` получает только `issues: write`, не делает checkout и при failure/anomaly создаёт GitHub issue со ссылкой на run. Уведомление приходит через стандартные GitHub notifications/email.

Ни недоверенные списки, ни сторонние Go-компиляторы не выполняются в job, где доступны push credentials.

Оба режима сохраняются:

- weekly cron автоматически собирает и публикует безопасные изменения;
- `workflow_dispatch` запускает немедленную пересборку.

Manual input `allow_large_diff` разрешает после человеческой проверки обойти только порог изменения количества правил. Он не отключает parser validation, тесты, path allowlist или запрет пустых обязательных категорий.

Для исключения гонок workflow использует один `concurrency` group без отмены уже начатой публикации.

## Валидация upstream-данных

Каждый download сначала попадает во временный файл. До замены cache проверяются:

- HTTPS URL;
- UTF-8;
- размер не более 64 MiB на источник;
- непустой payload;
- успешный разбор поддерживаемого формата;
- непустой результат для категории, которая была непустой в предыдущем `summary.json`.

После сборки новая статистика сравнивается с закоммиченным `distillate/summary.json`. Без `allow_large_diff` публикация блокируется, если количество доменов или CIDR в существующей непустой категории:

- уменьшилось более чем на 40%;
- выросло более чем на 100%.

Обычные изменения в пределах порогов публикуются автоматически. Блокировка не изменяет кэш или generated outputs рабочего дерева.

## Атомарная distillate-сборка

`build_distillate()` формирует все text, rules, modules, summary и `.dat` во временном staging root. Исходный репозиторий не очищается до успешного завершения parsing и обоих Go-компиляторов.

После полной валидации outputs заменяются по allowlist. При любой ошибке staging удаляется, а последняя рабочая версия остаётся неизменной. `--skip-compiled` использует тот же staging flow, но сохраняет существующие `.dat`.

## HAPP reproducibility

`build_happ_routing.py` меняет `LastUpdated` только при явно переданном `--build-stamp`. Если аргумент отсутствует и `HAPP/DEFAULT.JSON` уже существует, генератор сохраняет его текущий stamp. Поэтому повторная локальная сборка на bot-HEAD идемпотентна.

Weekly workflow передаёт один новый epoch stamp для JSON и deeplink в рамках конкретной публикации.

## Whitelist-профиль

Публичный `shadowrocket_whitelist.conf` больше не содержит имя конкретного VPN-узла. Группа `PROXY` использует общий `policy-regex-filter=WL`; пользователь выбирает доступный WL-узел в Shadowrocket. README явно описывает этот шаг и отсутствие стабильного переносимого default-узла.

## Тестирование

CI до публикации запускает:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q scripts tests
```

Новые тесты покрывают:

- отказ при пустом или слишком большом upstream payload;
- delta thresholds и ручной override;
- отсутствие изменения рабочего дерева при ошибке staged build;
- успешную атомарную публикацию outputs;
- сохранение существующего HAPP stamp без `--build-stamp`;
- обновление stamp при явном аргументе;
- отсутствие персонального node name в whitelist-профиле;
- структуру workflow: read-only build, отдельный write publish, concurrency, tests и manual dispatch.

Полная локальная проверка дополнительно сравнивает cached rebuild с tracked outputs и подтверждает чистый `git status`.

## Документация и эксплуатация

README и `AGENTS.md` обновляются так, чтобы:

- не ссылаться на удалённый XKeen;
- признавать существование автоматических тестов;
- описывать weekly auto-publish, manual rebuild и anomaly issue;
- различать плавающие публичные данные и закреплённый исполняемый код;
- перечислять реальные generated и manually maintained файлы;
- не содержать персональных абсолютных путей или имён VPN-узлов.

## Критерии готовности

Работа завершена, когда:

1. Публичный репозиторий не содержит XKeen-кода или приватных node names.
2. Приватный архив содержит самодостаточный legacy snapshot и проходит свои архивные тесты.
3. Weekly и manual rebuild сохранены.
4. Build job не имеет push credentials; publish job не исполняет сторонний код.
5. Аномальный upstream не меняет рабочие outputs и создаёт уведомление.
6. Повторная локальная сборка HAPP и cached artifacts не создаёт diff.
7. Все публичные тесты проходят, а рабочее дерево содержит только запланированные изменения.
