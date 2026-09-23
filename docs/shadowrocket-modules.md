# Модули Shadowrocket

### Сервисы Apple через прокси

Модуль `Apple Proxy` направляет через `PROXY` домены и IP-диапазоны сервисов Apple,
включая Apple Music и Store, iCloud, Push и обновления. Доступность зависит от
выбранного прокси-узла: модуль не исправляет узел, который сам не подключается.

Добавьте в **Config → Modules → Add** ссылку:

```text
https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/modules/apple_proxy.module
```

Включите модуль и установите глобальную маршрутизацию **Config / Конфигурация**.
Поставьте `Apple Proxy` выше GFN Direct и других модулей с пересекающимися DIRECT-правилами,
а также выше блокирующих модулей. Это
позволяет правилу Apple `17.0.0.0/8` примениться раньше GFN DIRECT-исключения
`17.253.150.10/32`, а правилам сервисов — раньше anti-advertising.

Список доменов и диапазонов основан на [требованиях Apple для корпоративных сетей](https://support.apple.com/en-us/101555).

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

## Блокировка рекламы

Для анти-рекламы можно использовать модуль `modules/anti_advertising.module` по ссылке:
```
https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/modules/anti_advertising.module
```
Модуль подключает все собранные anti-ad чанки; ссылки `RULE-SET` обновляет генератор.
Подключайте модуль целиком: число чанков меняется при обновлении источников. Примеры имён:
```text
https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/anti_advertising.01.list
https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/anti_advertising.02.list
```
Как добавить модуль в Shadowrocket:
1. Откройте **Config → Modules**.
2. В правом верхнем углу нажмите **Add/Добавить**.
3. Вставьте ссылку на модуль и подтвердите загрузку.
4. Нажмите на загруженный модуль, чтобы активировать его.

Модуль работает в дополнение к любому активному конфигу и не заменяет его.
## Порядок модулей

Префиксы в `#!name` обозначают уровень и порядок внутри уровня. Выставьте этот
порядок в Config → Modules; проверьте итоговые правила после компиляции.

| Имя | Файл | Назначение |
|---|---|---|
| 10_01 · Tailscale Direct | `modules/tailscale_direct.module` | Официальный клиент Tailscale |
| 10_02 · Tailscale Tailnet | `modules/tailscale_tailnet.module` | Встроенный Tailscale Shadowrocket |
| 15_01 · Apple Proxy | `modules/apple_proxy.module` | Сервисы Apple через выбранную политику PROXY |
| 20_01 · GFN Direct | `modules/GFN-AM.module` | NVIDIA/GFN и связанные исключения DIRECT |
| 20_02 · WeChat Direct | `modules/wechat_direct.module` | WeChat и его CDN через DIRECT |
| 20_04 · Twitch Video Direct | `modules/twitch_video_direct.module` | Видеосерверы Twitch через DIRECT; сайт и API по основному конфигу |
| 90 · Anti-Advertising | `modules/anti_advertising.module` | Общая блокировка после сервисных исключений |

Включайте только один модуль уровня 10. Сервисные исключения уровня 20 имеют
приоритет перед анти-рекламой, включая разрешённую ими телеметрию.
Префикс 20_03 зарезервирован для будущего решения Google/Gemini.

При переходе удалите ранее установленные Anti-Advertising Custom и оба модуля
Gemini из приложения: удаление файлов из репозитория не удаляет загруженные копии.
Обновите оставшиеся модули и добавьте Tailscale Direct, если используете официальный клиент.
GFN уже покрывает NVIDIA/GFN-исключения удалённого Custom через существующие
DOMAIN-KEYWORD, DOMAIN-SUFFIX и IP-CIDR правила. Остальные правила Custom
не включены в новый набор.

Изменение набора и нумерации модулей — shared; персональные исключения остаются custom-only.

## Ссылки для импорта

Откройте ссылку на устройстве с установленным Shadowrocket. Если встроенный браузер мессенджера не открывает приложение, используйте Safari. После импорта выставьте порядок по номерам.
Для Apple Proxy добавьте прямую ссылку на файл через **Config → Modules → Add**.

| Порядок | Модуль | Импорт |
|---|---|---|
| 10_01 | Tailscale Direct | [Добавить](https://potato-link.motivato-potato.workers.dev/sr/modules/tailscale-direct) |
| 10_02 | Tailscale Tailnet | [Добавить](https://potato-link.motivato-potato.workers.dev/sr/modules/tailscale-tailnet) |
| 15_01 | Apple Proxy | [Файл модуля](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/modules/apple_proxy.module) |
| 20_01 | GFN Direct | [Добавить](https://potato-link.motivato-potato.workers.dev/sr/modules/gfn) |
| 20_02 | WeChat Direct | [Добавить](https://potato-link.motivato-potato.workers.dev/sr/modules/wechat) |
| 20_04 | Twitch Video Direct | [Добавить](https://potato-link.motivato-potato.workers.dev/sr/modules/twitch) |
| 90 | Anti-Advertising | [Добавить](https://potato-link.motivato-potato.workers.dev/sr/modules/anti-advertising) |
