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

Установите DNS Override самым верхним в списке модулей.

https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/modules/dns_override.module
