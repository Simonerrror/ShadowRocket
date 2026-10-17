# Модули Shadowrocket

### Private DNS Override

Модуль `modules/private_dns_override.module` подставляет аргумент `DNS` в
`dns-server`, `fallback-dns-server` и `direct-dns-server`. Перед включением
задайте адрес DNS в параметрах модуля. `dns-direct-system` установлен в `false`.

### OpenAI через США

Модуль `modules/openai_usa.module` направляет существующий список
`rules/openai.list` в группу `OpenAI USA`. Группа собирает узлы с `USA`
в названии без учёта регистра из всех добавленных подписок. Выбор узла автоматический (url-test, каждые 180 секунд).

Импортируйте локальный файл в **Config → Modules**, включите модуль и
используйте группу **OpenAI USA** с автоматическим выбором узла. Используйте маршрутизацию
**Config / Конфигурация**. Расположите модуль выше GFN Direct и
Anti-Advertising, чтобы пересекающиеся правила OpenAI применялись первыми.

### Twitch через Польшу и Сербию

Модуль `modules/twitch_poland.module` направляет Twitch, чат и видеопотоки
из списка `rules/twitch.list` через группу `Twitch PL-RS`.
Группа автоматически выбирает узел из всех подписок по названиям `Poland`,
`Польша`, `Serbia`, `Сербия`, отдельным кодам `PL`/`RS` или флагам 🇵🇱/🇷🇸. Проверка — каждые 180 секунд.
Добавьте польские или сербские узлы в Shadowrocket перед включением модуля.

Сербия добавлена как дополнительный регион для проверки рекламы и доступности.
Отсутствие рекламы зависит от рекламных кампаний Twitch и не гарантируется.
URL-тест обращается к `https://www.twitch.tv/favicon.ico` через проверяемый узел.
Он проверяет доступность Twitch и время отклика, а не скорость видеопотока.

Добавьте модуль в **Config → Modules** по ссылке:

```text
https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/modules/twitch_poland.module
```

Включите маршрутизацию **Config / Конфигурация**. Расположите модуль после
OpenAI USA и выше Anti-Advertising. URL в заголовке модуля служит для обновления.

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
| 15_02 · OpenAI USA | `modules/openai_usa.module` | OpenAI через автоматический выбор среди узлов USA из всех подписок |
| 15_03 · Twitch PL-RS | `modules/twitch_poland.module` | Twitch через автоматический выбор польских и сербских узлов из всех подписок |
| 20_01 · GFN Direct | `modules/GFN-AM.module` | NVIDIA/GFN и связанные исключения DIRECT |
| 20_02 · WeChat Direct | `modules/wechat_direct.module` | WeChat и его CDN через DIRECT |
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
| 90 | Anti-Advertising | [Добавить](https://potato-link.motivato-potato.workers.dev/sr/modules/anti-advertising) |
