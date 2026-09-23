# ShadowRocket

Основной конфиг Shadowrocket: [shadowrocket.conf](shadowrocket.conf). Он задаёт маршрутизацию и обновляется по URL. Серверы добавляются в Shadowrocket отдельно — через подписку или вручную.

## Подключение

1. Откройте в Shadowrocket **Config → Add Config → URL** и добавьте:

   ```text
   https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/shadowrocket.conf
   ```

2. Добавьте свою подписку на серверы или локальные серверы. Для ссылки на подписку используйте шаблон `shadowrocket://add/SUBSCRIPTION_URL`: замените `SUBSCRIPTION_URL` полным HTTPS-адресом своей подписки.
3. Включите конфиг и выберите группу `PROXY`. По умолчанию она использует `AUTO-STABILITY`.

[Ссылка для импорта конфига](https://potato-link.motivato-potato.workers.dev/sr/config). Если встроенный браузер мессенджера не открывает Shadowrocket, откройте её в Safari.

## Выбор сервера

- `MANUAL-PROXY` — ручной выбор серверов без отдельных меток `WL` и `SS` в имени.
- `AUTO-SPEED` — выбирает самый быстрый доступный сервер.
- `AUTO-STABILITY` — выбирает первый доступный сервер в порядке списка.
- `WL` — отдельная группа для серверов с самостоятельной меткой `WL` в имени.

Автоматические группы отбирают имена с отдельными метками `VLESS`, `TT`, `Naive`, `NV`, `MR`, `AWG`, `AWG2` или `AWG3.1`. Имена с `Russia`, `Belarus`, `Ukraine` или самостоятельной меткой `WL` исключаются. Если добавляете сервер вручную, укажите в его имени отдельную метку: `TT` для TrustTunnel, `NV` для Naive, `MR` для Mieru, `AWG` для AmneziaWG. Например: `TT Мой сервер`. Затем проверьте в Shadowrocket, появился ли локальный сервер в нужной группе.

## Дополнения

- [Модули Shadowrocket](docs/shadowrocket-modules.md) — Apple, GFN, Tailscale, WeChat, Twitch и блокировка рекламы; там же порядок включения.
- [Аварийный whitelist-профиль](shadowrocket_whitelist.conf) — отдельный конфиг с маршрутизацией через один выбранный `PROXY`.
- [Clash Verge Rev](docs/clash-verge-rev.md) — настройка Windows-клиента.
- [INCY](INCY/README.md) — профили и ссылки для импорта; пользователям HAPP рекомендуется перейти на INCY.
- [HAPP](HAPP/README.md) — сохранённые профили на время перехода.
- [Сборка и сопровождение](docs/maintenance.md) — структура проекта, обновление списков и порядок пересборки.

## Как работает конфиг

### [General]
- Базовые сетевые настройки: DNS — `9.9.9.9`, `149.112.112.112`, `77.88.8.8`; fallback использует тот же набор, IPv6 выключен.
- Для доменов, совпавших с доменными правилами `DIRECT`, во всех трёх профилях задан `direct-dns-server = 77.88.8.8, 77.88.8.1` (Яндекс DNS).
- Основной и custom-профиль используют общий DNS/skip/bypass каркас.
- GFN/NVIDIA `always-real-ip` остаётся custom-only и не переносится в основной профиль.
- `update-url` указывает на конфиг в репозитории.
- Каждый публикуемый Shadowrocket-профиль содержит `Config-Version` сразу после `[General]`. Формат версии: `YYYY.MM.DD.N`, где `N` — номер ревизии за день.

### [Proxy Group]
- **MANUAL-PROXY** — ручной выбор поддерживаемых узлов подписки без standalone `WL`.
- **AUTO-SPEED** — `url-test`-группа для выбора самого быстрого живого узла из подписки:
  фильтр принимает standalone `VLESS`, `TT`, `Naive`, `NV`, `MR`, `AWG`, `AWG2` и `AWG3.1` и исключает `Russia`, `Belarus`, `Ukraine` и standalone `WL`; `url=https://www.youtube.com/favicon.ico`, `interval=180`, `tolerance=100`, `timeout=7`.
- **AUTO-STABILITY** — `fallback`-группа для выбора первого живого узла в порядке подписки:
  фильтр принимает standalone `VLESS`, `TT`, `Naive`, `NV`, `MR`, `AWG`, `AWG2` и `AWG3.1` и исключает `Russia`, `Belarus`, `Ukraine` и standalone `WL`; `url=https://www.youtube.com/favicon.ico`, `interval=780`, `timeout=7`.
- **WL** — отдельная `select`-группа для узлов любого протокола со standalone `WL` (включая `WL-lte`), фильтр `(?i)\bWL\b`.
- **PROXY** — Select-группа; по умолчанию выбран `AUTO-STABILITY`, доступны `MANUAL-PROXY`/`AUTO-SPEED`/`AUTO-STABILITY`/`WL`.
  В `AUTO-STABILITY` первичным считается первый живой узел в порядке уже фильтрованной подписки.

Тест загружает иконку с www.youtube.com; он проверяет доступность этого адреса, но не воспроизведение видео с googlevideo.com.

### [Rule]
Порядок важен: правила обрабатываются сверху вниз.

1. **Ручные overlays**
   - `distillate/overlays/whitelist_direct.add.list` — принудительно DIRECT.
   - Точечное DIRECT-исключение для Path of Exile (`DOMAIN-SUFFIX,pathofexile.com`, `DOMAIN-SUFFIX,poecdn.com`, плюс `DOMAIN-KEYWORD,pathofexile` и `DOMAIN-KEYWORD,pasthofexile`) также ведётся через `whitelist_direct`.
   - `distillate/overlays/greylist_proxy.add.list` — принудительно PROXY.
   - X/Twitter redirect и статика (`t.co`, `x.com`, `twitter.com`, `twimg.com`) закрепляются через `greylist_proxy`, чтобы короткие ссылки и связанные ресурсы не выпадали из принудительного PROXY-маршрута.
2. **Microsoft/Office 365/Teams/OneDrive**
   - Категория `microsoft` собирается из BM7 `Microsoft` и уходит в `PROXY`.
3. **Community bundle**
   - Категория `domains_community` собирается из BM7 `Telegram`/`GitHub`/`Steam`/`Riot`/`Origin`/`EA`/`Epic`/`Twitch`/`Pinterest` и уходит в `PROXY`.
4. **Direct для РФ**
   - Домены `.ru/.рф/.su` и GEOIP RU идут напрямую.
5. **FINAL**
   - Всё остальное — в `PROXY`.

## Импорт модулей

Инструкция и ссылки для импорта: [модули Shadowrocket](docs/shadowrocket-modules.md).
