# ShadowRocket: карта работы

## Lessons

- When adding or renaming a module, apply the numbering contract in [Порядок модулей](docs/shadowrocket-modules.md#порядок-модулей) to its `#!name`, documentation and any site button. Verify all modules and displayed buttons with the existing numbering tests; do not introduce a separate sequence on the site.

## Область и границы

Этот файл регулирует публичный Git-репозиторий `ShadowRocket/`.
До изменений прочитайте соседний `AGENTS.local.md`, если он есть: там задана
локальная граница приватных данных. Родительский `../AGENTS.md` владеет картой
подписок и роутера; глобальные инструкции — полномочиями, зависимостями и навыками.
Не копируйте эти правила сюда и не расширяйте ими полномочия пользователя.

Публичные результаты проекта: конфиги Shadowrocket, модули, generated-конфиг
Mihomo, профили маршрутизации INCY и сайт ссылок на GitHub Pages.
Поддержка HAPP и аварийного whitelist-профиля прекращена. Старые updater и
allowlist Gemini, списки russia_extended/voice_ports и модуль Twitch Direct удалены.
Не возвращайте их как запасные пути. `whitelist_direct` остаётся действующим
списком исключений основного конфига.

## Владельцы файлов

| Компонент | Источник истины и назначение |
| --- | --- |
| `shadowrocket.conf` | Основной профиль: General, группы и порядок Rule |
| `shadowrocket_custom.conf` | Отдельный ручной профиль; общие изменения синхронизируются с основным, персональные отличия сохраняются |
| `distillate/manifest.json` | Состав категорий, источников, агрегатов и generated-списков |
| `distillate/overlays/`, `distillate/filters/` | Ручные изменения состава правил |
| `distillate/upstream/` | Кэш публичных источников для воспроизводимой пересборки |
| `modules/` | Самостоятельные дополнения Shadowrocket; изменения сервисного модуля принадлежат ему |
| `scripts/build_clash_config.py` | Генерирует `clash_config.yaml` из основного профиля |
| `scripts/build_distillate.py` | Генерирует списки, агрегаты, summary и compiled-геоданные |
| `scripts/build_incy_routing.py` | Генерирует оба профиля INCY и SHA-256 sidecar геоданных |
| `scripts/build_site.py` | Встраивает проверенные INCY deeplink в `docs/index.html` |
| `site/index.html` | Исходник страницы с прямыми ссылками импорта |
| `docs/index.html`, `docs/images/`, `docs/favicon.svg` | Публикуемая страница GitHub Pages и её ресурсы |

Generated-файлы не правьте вручную: `docs/index.html`, `clash_config.yaml`, `INCY/*.JSON`,
`INCY/*.DEEPLINK`, `distillate/text/**`, `distillate/dat/**`, summary и списки
с заголовком `Generated from distillate/manifest.json`.
В `anti_advertising.module` сохраняйте ручной заголовок; ссылки на чанки
переписывает генератор. Число anti-ad чанков не фиксировано.

## Маршрутизация и DNS

- В основном профиле три группы: MANUAL-PROXY, AUTO-SPEED, WL. Селектор PROXY
  по умолчанию использует AUTO-SPEED. Не путайте выбор маршрута с успешным
  соединением, скоростью передачи или устойчивостью воспроизведения.
- Для ошибки GEOIP добавляйте домен в `distillate/overlays/greylist_proxy.add.list`.
  Не создавайте параллельное inline-правило: список уже подключён до GEOIP RU.
  Для принудительного DIRECT используйте владельца `whitelist_direct`.
- Общие правки маршрутизации переносите в основной и custom-профиль.
  Модули имеют собственный приоритет над правилами профиля; порядок модулей
  также влияет на результат. Проверяйте пересечения DIRECT/PROXY/REJECT.
- DNS Override Example — шаблон для локальной копии с ручными адресами DNS.
  Не добавляйте ему `#!url` или `update-url`: обновление не должно затирать
  пользовательские значения. Кнопка открывает текст примера для создания локального
  модуля. Пользователь вписывает основной DNS и Smart DNS после `=`.
  Не добавляйте персональные адреса в модуль, сайт, тесты или generated-файлы.
- Google AI Smart DNS — самостоятельный модуль. Состав общего Google-списка
  принадлежит `rules/google-all.list` и distillate; не собирайте его дубль.
- OpenAI USA использует url-test и фильтр USA по именам узлов всех подписок.
  URL проверки не доказывает доступность каждого сервиса OpenAI.
- При неизвестной семантике сначала проверьте [LOWERTOP/Shadowrocket](https://github.com/LOWERTOP/Shadowrocket)
  и [Shadowrocket News](https://t.me/ShadowrocketNews); дополнительный источник —
  [Shadowrocket/manual](https://github.com/Shadowrocket/manual). Сверяйте описание
  с версией и сборкой клиента. Не переносите семантику другого VPN-клиента по аналогии.

## Пересборка

Сначала определите изменённого владельца, затем обновляйте его выходы:

- Основной профиль → Clash YAML и INCY → страница GitHub Pages.
- Manifest, overlay, filter или upstream → distillate, generated rule lists,
  anti-ad ссылки и геоданные → INCY → страница GitHub Pages.
- Модуль или текст сайта → затронутые модульные проверки и тесты сайта; весь каскад
  не запускается без изменения его входов.

Кэшированная локальная сборка, без обновления upstream и загрузки компиляторов:

```sh
python3 scripts/build_distillate.py --skip-compiled
python3 scripts/build_clash_config.py
python3 scripts/build_incy_routing.py
python3 scripts/build_site.py
```

`--skip-compiled` не обновляет бинарные геоданные. Если изменился их состав,
полная публикация требует compiled-сборки. Она загружает закреплённые Go-исходники
и зависимости: соблюдайте глобальную dependency-safety policy.
Не запускайте `sync_lists.py` для обычной пересборки. Refresh публичных источников
выполняется только по запросу пользователя или действующему заданию weekly workflow.

## Проверки и доказательства

Для затронутых Python-компонентов запускайте их tracked-тесты. При изменении
общего генератора, выходов или CI выполните весь набор:

```sh
python3 -m unittest discover -s tests
python3 -m compileall -q scripts tests
```

Проверяйте воспроизводимость пересборки и `git diff --check`.
Тесты генератора доказывают его контракт, а не работу VPN-клиента. Для заявления
о рабочем импорте, TUN, DNS или воспроизведении нужен соответствующий runtime-тест.

## Версии и публикация

Поведение General, Rule или групп любого поддерживаемого `shadowrocket*.conf`
меняет общую `Config-Version` основного и custom-профиля. Формат `YYYY.MM.DD.N`;
ревизия должна быть выше опубликованной. Обновите ожидаемую метку в тесте профилей.
Удаление отдельного профиля или изменение сайта не требует менять маршруты
оставшихся конфигов ради новой метки.

Перед разрешённым push выполните fetch, проверьте staged diff, публикуемые refs
и generated-файлы на приватные данные. Значения находок в вывод не помещайте.
Сохраняйте независимые локальные изменения. История Git не переписывается
ради обычной очистки текущего дерева.

Сайт публикуется штатным GitHub Pages из `main/docs` по адресу
`https://simonerrror.github.io/ShadowRocket/`. `deploy-pages.yml` проверяет сборку
и запрашивает публикацию текущей проверенной ревизии `main`. После успешного
`Sync rule lists` он запускается отдельно через `workflow_run`.
Страница содержит прямые `shadowrocket://` и `incy://` ссылки; DNS Example
открывает публичный текст для локальной копии. Приватные подписки сюда не подключайте.
Подробности сборки принадлежат [site/README.md](site/README.md).

После публикации проверьте CI, публичную страницу, относительные пути к ресурсам
под `/ShadowRocket/` и соответствие ссылок актуальным конфигам и INCY deeplink.
Успешная публикация не доказывает импорт или работу VPN-клиента.

## Связанные инструкции

- [Сопровождение](docs/maintenance.md): источники, compiled-сборка и weekly release.
- [Модули](docs/shadowrocket-modules.md): пользовательский импорт и порядок.
- [DNS Override](docs/dns-override.md): ручное заполнение адресов.
- [INCY](INCY/README.md): назначение двух routing-профилей.
- [Clash Verge Rev](docs/clash-verge-rev.md): текущая инструкция для Windows.
  Наличие generated YAML не означает проверенную поддержку Android.
