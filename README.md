# ShadowRocket: конфиг и правила маршрутизации

Готовые конфиги для Shadowrocket и Clash Verge Rev (Mihomo), построенные на общем наборе правил в `rules/`.
Проект поддерживает автообновление по URL и разделённую маршрутизацию (Google/Gemini/YouTube,
Microsoft, Telegram, голосовые сервисы и т.д.).

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
- `rules/` — общий набор списков доменов и IP для маршрутизации.

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
| `rules/` | Списки доменов/IP для маршрутизации |
| `modules/` | Готовые модули для Shadowrocket |
| `scripts/` | Вспомогательные скрипты |

## Логика `shadowrocket.conf`

### [General]
- Базовые сетевые настройки: DNS — NextDNS (DoH), fallback — NextDNS IP → 1.1.1.1/8.8.8.8, IPv6 выключен.
- `update-url` указывает на конфиг в репозитории.

### [Proxy Group]
- **AUTO-MAIN** — URL-тест с фильтром по имени (только VLESS, исключаем RU/BY/UA):
  `url=https://abs.twimg.com/favicon.ico`, `interval=780`, `tolerance=200`, `timeout=7`.
- **MANUAL-PROXY** — ручной выбор из тех же серверов, что и AUTO-MAIN.
- **GOOGLE** — ручной выбор из отфильтрованного списка для Google/Gemini/YouTube (NL VLESS + UAE VLESS).
- **PROXY** — Select-группа для ручного выбора между AUTO-MAIN/MANUAL-PROXY/DIRECT.

### [Rule]
Порядок важен: правила обрабатываются сверху вниз.

1. **Ручные списки**
   - `whitelist_direct.list` — принудительно DIRECT.
   - `greylist_proxy.list` — принудительно PROXY.
2. **Google/Gemini/YouTube**
   - Домены и IP направляются в группу `GOOGLE` с `force-remote-dns` для доменных списков.
3. **Microsoft/Office 365/Teams/OneDrive**
   - Уходят в `PROXY` с `force-remote-dns` для доменных списков.
4. **Остальные правила**
   - Комьюнити-списки доменов, IP-диапазоны, голосовые сервисы, Telegram → `PROXY`.
5. **Direct для РФ**
   - Домены `.ru/.рф/.su` и GEOIP RU идут напрямую.
6. **FINAL**
   - Всё остальное — в `PROXY`.

### [Host] / [URL Rewrite]
- Статический `localhost`.
- Редиректы для `nnmclub.to` и `yandex.ru`.

## Обновление

- Конфиг обновляется автоматически через `update-url`.
- Списки правил обновляются при обновлении конфига или вручную через Shadowrocket.
- Списки `rules/*.list` синхронизируются в GitHub Actions (`.github/workflows/build-happ-routing.yml`) через `scripts/sync_lists.py`, после чего в той же джобе пересобираются HAPP-артефакты.
- Антирекламный список `rules/anti_advertising.list` собирается с дедупликацией источников OISD + HaGeZi.

## Расширение правил

Если нужно добавить сервис — создайте новый список в `rules/` и подключите его в секции `[Rule]`.
Для анти-рекламы можно использовать модуль `modules/anti_advertising.module` по ссылке:
```
https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/modules/anti_advertising.module
```
Или кастомный модуль с локальными исключениями для GFN/NVIDIA:
```
https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/modules/anti_advertising_custom.module
```
Модуль подключает единый список репозитория:
```
https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/anti_advertising.list
```
Как добавить модуль в Shadowrocket:
1. Откройте **Config → Modules**.
2. В правом верхнем углу нажмите **Add/Добавить**.
3. Вставьте ссылку на модуль и подтвердите загрузку.
4. Нажмите на загруженный модуль, чтобы активировать его.

Модуль работает в дополнение к любому активному конфигу и не заменяет его.
