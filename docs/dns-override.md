# DNS Override

После импорта откройте Config → Modules → DNS Override и редактор текста модуля.
Впишите адреса после знака `=`:

- `dns-server` — основной DNS: можно указать свой приватный адрес вместо `9.9.9.9`.
- `direct-dns-server` — Smart DNS для прямых запросов. Заполните до включения модуля.

Аргументы не используются. Персональные адреса вписываются только в локальную
копию в Shadowrocket. При повторном импорте проверьте, сохранились ли они.
Резервный `fallback-dns-server` остаётся из активного конфига.
Smart DNS применяется ко всем прямым доменным правилам, а не только к Gemini.
Для Gemini используйте также модуль Google AI Smart DNS.

Модуль Google AI Smart DNS направляет `waa-pa.clients6.google.com`,
`geminiweb-pa.clients6.google.com` и `ogads-pa.clients6.google.com` через
`DIRECT` вместе с Gemini.
DNS для этих запросов задаёт `direct-dns-server`.
Расположите Google AI Smart DNS выше Anti-Advertising, чтобы исключения
применялись раньше блокирующих правил.

Добавьте Google AI Smart DNS по постоянной ссылке:

https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/modules/google_ai_smart_dns_mobile.module

Для уже добавленного модуля выполните обновление в Config → Modules.
Его заголовок `#!url` содержит ту же ссылку.

Установите DNS Override самым верхним в списке модулей.

https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/modules/dns_override.module
