# DNS Override

Модуль задаёт два DNS: основной через параметр `DNS` и прямой через
`SmartDNS`. В `DNS` можно указать свой приватный DNS; по умолчанию — `9.9.9.9`.
В `SmartDNS` укажите Smart DNS перед включением. Адрес хранится в настройках модуля Shadowrocket,
а публичный файл содержит только шаблон.

Резервный `fallback-dns-server` остаётся из активного конфига. При его
использовании запросы могут уйти к резервному DNS, а не к приватному.
Smart DNS применяется ко всем запросам, попавшим под прямые доменные правила,
а не только к Gemini. Для Gemini используйте также модуль Google AI Smart DNS.

Установите DNS Override самым верхним в списке модулей.

Публичный файл:
https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/modules/dns_override.module
