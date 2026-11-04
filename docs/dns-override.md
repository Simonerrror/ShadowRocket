# DNS Override Example

Это пример для создания локального модуля с вашими адресами DNS. В примере нет
`#!url` и `update-url`: он не задаёт источник обновления поверх пользовательских значений.

## Создание локальной копии

1. Откройте [текст примера](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/modules/dns_override.module)
   и скопируйте его содержимое.
2. Откройте **Config → Modules → Новый модуль** и вставьте текст.
3. Впишите адреса после знака `=`:
   - `dns-server` — основной DNS; при необходимости замените `9.9.9.9` своим адресом.
   - `direct-dns-server` — ваш Smart DNS для прямых запросов; заполните перед включением.
4. Сохраните имя `01_01 · DNS Override Example` и поставьте модуль первым в списке.
5. Включите локальную копию.

Аргументы не используются. Персональные адреса остаются в локальном модуле.
Не импортируйте публичный пример повторно поверх заполненной копии.
Если в уже настроенном модуле осталась строка `#!url=...`, удалите только её,
сохранив свои адреса DNS.

Резервный `fallback-dns-server` остаётся из активного конфига.
Smart DNS применяется ко всем прямым доменным правилам, а не только к Gemini.
Для Gemini используйте также отдельный модуль Google AI Smart DNS.

Модуль Google AI Smart DNS направляет `waa-pa.clients6.google.com`,
`geminiweb-pa.clients6.google.com` и `ogads-pa.clients6.google.com` через
`DIRECT` вместе с Gemini.
DNS для этих запросов задаёт `direct-dns-server`.
Расположите Google AI Smart DNS (`20_03`) выше Anti-Advertising (`90_01`), чтобы исключения
применялись раньше блокирующих правил.

Добавьте Google AI Smart DNS по постоянной ссылке:

https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/modules/google_ai_smart_dns_mobile.module

Для уже добавленного Google AI Smart DNS выполните обновление в Config → Modules.
Его заголовок `#!url` содержит ту же ссылку; это отдельный обновляемый модуль.

Установите локальный DNS Override Example самым верхним в списке модулей.
