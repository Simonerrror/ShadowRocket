# ShadowRocket: актуальный конфиг и правила

Репозиторий содержит готовый конфиг `shadowrocket.conf` и набор списков правил в каталоге `rules/`.
Конфиг уже включает группы прокси, обновление по URL и разделённую маршрутизацию (Google/Gemini/YouTube,
Microsoft, Telegram, голосовые сервисы и т.д.).

## Быстрый старт

1. **Добавьте конфиг по ссылке** (Shadowrocket → Add Config/Добавить конфиг → URL):
   ```
   https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/shadowrocket.conf
   ```
   > В конфиге также указан `update-url`, поэтому он будет обновляться автоматически.
2. **Добавьте свою подписку** на сервера в Shadowrocket (URL от вашего провайдера).
3. **Проверьте группы прокси**:
   * `AUTO-MAIN` — автоматический выбор по URL-тесту (исключает RU/BY/UA, только VLESS).
   * `GOOGLE` — отдельный автоподбор для Google (только NL и UAE, только VLESS).
   * `PROXY` — главный переключатель (Select): `AUTO-MAIN`, `GOOGLE` или `DIRECT`.

## Что внутри `shadowrocket.conf`

### [General]
* Базовые сетевые настройки: DNS-over-HTTPS, IPv6 выключен, список исключений для локальных/служебных сетей.
* `update-url` указывает на конфиг в репозитории.

### [Proxy Group]
* **AUTO-MAIN** — URL-тест с фильтром по имени (исключаем Russia/Belarus/Ukraine, оставляем VLESS).
* **GOOGLE** — отдельный URL-тест для Google/Gemini/YouTube (NL/UAE + VLESS).
* **PROXY** — Select-группа для ручного выбора между AUTO-MAIN/GOOGLE/DIRECT.

### [Rule]
Порядок важен: правила обрабатываются сверху вниз.

1. **Блокировки протоколов**
   * QUIC (UDP/443) и DoT (UDP/853).
2. **Ручные списки**
   * `whitelist_direct.list` — принудительно DIRECT.
   * `greylist_proxy.list` — принудительно PROXY.
3. **Google/Gemini/YouTube**
   * Домены и IP направляются в группу `GOOGLE` с `force-remote-dns` для доменных списков.
4. **Microsoft/Office 365/Teams/OneDrive**
   * Уходят в `PROXY` с `force-remote-dns` для доменных списков.
5. **Остальные правила**
   * Комьюнити-списки доменов, IP-диапазоны, голосовые сервисы, Telegram → `PROXY`.
6. **Direct для РФ**
   * Домены `.ru/.рф/.su` и GEOIP RU идут напрямую.
7. **FINAL**
   * Всё остальное — в `PROXY`.

### [Host] / [URL Rewrite]
* Статический `localhost`.
* Редиректы для `nnmclub.to` и `yandex.ru`.

## Списки правил (rules/)

* `whitelist_direct.list` — ручной whitelist (DIRECT).
* `greylist_proxy.list` — ручной greylist (PROXY).
* `google.list`, `google-gemini.list`, `gemini_ip.list`, `youtube.list`, `youtubemusic.list` — Google/Gemini/YouTube.
* `microsoft.list` — Microsoft/Office/Teams/OneDrive.
* `telegram.list` — Telegram.
* `voice_ports.list` — голосовые сервисы и порты.
* `domains_community.list` / `domain_ips.list` — общие домены и IP-диапазоны.
* `russia_extended.list` — дополнительный список РФ (можно подключать вручную при необходимости).

## Как обновлять

* Конфиг обновляется автоматически через `update-url`.
* Списки правил обновляются при обновлении конфига или вручную через Shadowrocket.

---
Если нужно добавить сервис — достаточно создать новый список в `rules/` и подключить его в секции `[Rule]`.
