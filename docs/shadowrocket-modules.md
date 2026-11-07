# Модули Shadowrocket

### DNS Override Example

`modules/dns_override.module` — пример для локального заполнения DNS и Smart DNS.
В нём нет URL обновления. Создайте локальную копию и впишите свои адреса по
[инструкции DNS](dns-override.md); повторно импортировать образец поверх неё не нужно.

### Google AI через Smart DNS

Для Gemini используйте `modules/google_ai_smart_dns_mobile.module` вместе с
DNS Override Example. Адрес Smart DNS задайте в локальной копии.
Установка и порядок этих модулей описаны в [инструкции DNS](dns-override.md).
Расположите DNS Override Example первым, а Google AI Smart DNS — выше Anti-Advertising.

### OpenAI через США

Модуль `modules/openai_usa.module` направляет существующий список
`rules/openai.list` в группу `OpenAI USA`. Группа собирает узлы с `USA`
в названии без учёта регистра из всех добавленных подписок. Выбор узла автоматический (url-test, каждые 180 секунд).

Импортируйте локальный файл в **Config → Modules**, включите модуль и
используйте группу **OpenAI USA** с автоматическим выбором узла. Используйте маршрутизацию
**Config / Конфигурация**. Расположите модуль выше GFN Direct и
Anti-Advertising, чтобы пересекающиеся правила OpenAI применялись первыми.

### Twitch No Advertise

Модуль `Twitch No Advertise` (`modules/twitch_poland.module`) направляет Twitch, чат и видеопотоки
из списка `rules/twitch.list` через группу `Twitch PL-RS`.
Группа автоматически выбирает узел из всех подписок по названиям `Poland`,
`Польша`, `Serbia`, `Сербия`, отдельным кодам `PL`/`RS` или флагам 🇵🇱/🇷🇸. Проверка — каждые 180 секунд.
Добавьте польские или сербские узлы в Shadowrocket перед включением модуля.

Польша и Сербия выбраны как регионы для просмотра без рекламы; её показ может измениться.
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

Состав правил Apple хранится в отдельном [списке `rules/apple.list`](../rules/apple.list):
домены, IPv4- и IPv6-диапазоны Apple Music и Store, iCloud, Push и обновлений.
Модуль `Apple Proxy` подключает весь список одной строкой `RULE-SET` с политикой
`PROXY`. Узел выбирается существующей группой `PROXY`; отдельного пула Apple нет.
В самом списке политика не задаётся. Для изменения состава редактируйте список,
а для изменения маршрута — модуль.

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

### Каталог GFN через прокси, запуск и игровой поток напрямую

Модуль `modules/GFN-AM.module` направляет только каталог приложения
`apps.gxn.nvidia.com` через существующую группу `PROXY` основного профиля.
Отдельной группы стран и проверки `favicon.ico` нет. Модуль не требует узлов
Казахстана, Украины или Армении. Видимость отдельных игр зависит от региона
выхода выбранного прокси; доступность одной игры не гарантирует доступность другой.

Авторизация `oauth.gfn.am`, служебные API NVIDIA, HTTPS API создания сессии
и игровой поток используют `DIRECT`. Точное правило каталога применяется раньше
общих правил NVIDIA/GFN. Реальные DNS-ответы для NVIDIA/GFN и прямое правило
подсети игровых серверов `37.186.111.0/24` сохраняются. Посторонних исключений
для Apple, Google и телеметрии в этом модуле нет.

Включите модуль и маршрутизацию **Config / Конфигурация**.
Используйте действующий узел в группе `PROXY` основного профиля.

Постоянный адрес обновления модуля:

```text
https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/modules/GFN-AM.module
```

Добавляйте модуль по этому URL или через ссылку импорта ниже. Заголовок `#!url`
содержит тот же адрес. После публикации новой версии выполните обновление модуля
в **Config → Modules**. Автоматическое обновление модулей включается отдельно
в настройках Shadowrocket; наличие `#!url` само по себе его не включает.
Версия отображается в описании модуля: `2026.11.08.1`.

Проверьте два результата в приложении GeForce NOW:

1. Найдите World of Warcraft в каталоге и откройте карточку. Сохранённая
   карточка библиотеки сама по себе не подтверждает доступность игры в каталоге.
2. Запустите игру и дождитесь начала трансляции. Открытие карточки или ответ
   `serverInfo` не подтверждает запуск.

В журнале Shadowrocket каталог должен использовать `PROXY`, а авторизация,
API сессии и игровой сервер — `DIRECT`. Если проверка не проходит, изменяйте
маршрут только того запроса, на котором подтверждён сбой, затем повторите обе проверки.

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

Все модули используют имя вида `NN_MM · Название`: `NN` — уровень,
`MM` — порядок внутри уровня. Уровни: `01` — ручной DNS, `10` — Tailscale,
`15` — сервисные прокси, `20` — сервисные исключения, `90` — блокировка рекламы.
Номер закреплён за модулем и одинаков в `#!name`, таблицах и кнопках сайта.
Номера не зависят от набора включённых модулей; пропуски допустимы.
При переименовании сохраняйте номер, при добавлении используйте свободный номер
подходящего уровня и обновляйте таблицы и кнопку, если она есть на сайте.

Выставьте модули в Config → Modules по возрастанию номера сверху вниз.
Само имя не переставляет модули в приложении. Проверьте итоговые правила после компиляции.

| Имя | Файл | Назначение |
|---|---|---|
| 01_01 · DNS Override Example | `modules/dns_override.module` | Локальная копия с ручными DNS; без URL обновления |
| 10_01 · Tailscale Direct | `modules/tailscale_direct.module` | Официальный клиент Tailscale |
| 10_02 · Tailscale Tailnet | `modules/tailscale_tailnet.module` | Встроенный Tailscale Shadowrocket |
| 15_01 · Apple Proxy | `modules/apple_proxy.module` | Сервисы Apple через выбранную политику PROXY |
| 15_02 · OpenAI USA | `modules/openai_usa.module` | OpenAI через автоматический выбор среди узлов USA из всех подписок |
| 15_03 · Twitch No Advertise | `modules/twitch_poland.module` | Просмотр Twitch без рекламы через автоматический выбор польских и сербских узлов из всех подписок |
| 20_01 · GFN Direct | `modules/GFN-AM.module` | Каталог через PROXY без фильтра стран; авторизация, запуск и поток DIRECT |
| 20_02 · WeChat Direct | `modules/wechat_direct.module` | WeChat и его CDN через DIRECT |
| 20_03 · Google AI Smart DNS | `modules/google_ai_smart_dns_mobile.module` | Google AI через DIRECT со Smart DNS из локальной копии DNS Override Example |
| 90_01 · Anti-Advertising | `modules/anti_advertising.module` | Общая блокировка после сервисных исключений |

Включайте только один модуль уровня 10. Сервисные исключения уровня 20 имеют
приоритет перед анти-рекламой, включая разрешённую ими телеметрию.
Google AI Smart DNS (`20_03`) расположен после GFN Direct (`20_01`) и WeChat Direct (`20_02`),
но выше Anti-Advertising (`90_01`). Настройка DNS описана в [инструкции DNS](dns-override.md).

При переходе удалите ранее установленные Anti-Advertising Custom,
Gemini Personal Outbound и Gemini Smart DNS Proxy из приложения. Действующий
Google AI Smart DNS сохраните. Удаление файлов из репозитория не удаляет загруженные копии.
Обновите оставшиеся модули и добавьте Tailscale Direct, если используете официальный клиент.
GFN уже покрывает NVIDIA/GFN-исключения удалённого Custom через существующие
DOMAIN-KEYWORD, DOMAIN-SUFFIX и IP-CIDR правила. Остальные правила Custom
не включены в новый набор.

Изменение набора и нумерации модулей — shared; персональные исключения остаются custom-only.

## Ссылки для импорта

Откройте ссылку на устройстве с установленным Shadowrocket. Если встроенный браузер мессенджера не открывает приложение, используйте Safari. После импорта выставьте порядок по номерам.
Кнопки «Добавить» находятся на сайте GitHub Pages. DNS Override Example
открывает текст для локальной копии и не выполняет удалённый импорт.

| Порядок | Модуль | Импорт |
|---|---|---|
| 01_01 | DNS Override Example | [Текст примера для локальной копии](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/modules/dns_override.module) |
| 15_01 | Apple Proxy | [Добавить](https://simonerrror.github.io/ShadowRocket/#module-apple) |
| 15_02 | OpenAI USA | [Добавить](https://simonerrror.github.io/ShadowRocket/#module-openai) |
| 15_03 | Twitch No Advertise | [Добавить](https://simonerrror.github.io/ShadowRocket/#module-twitch) |
| 20_01 | GFN Direct | [Добавить](https://simonerrror.github.io/ShadowRocket/#module-gfn) |
| 20_02 | WeChat Direct | [Добавить](https://simonerrror.github.io/ShadowRocket/#module-wechat) |
| 20_03 | Google AI Smart DNS | [Добавить](https://simonerrror.github.io/ShadowRocket/#module-google-ai) |
| 90_01 | Anti-Advertising | [Добавить](https://simonerrror.github.io/ShadowRocket/#module-anti-advertising) |
