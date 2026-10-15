# DNS Override

Модуль меняет только `direct-dns-server`: укажите Smart DNS в параметре
`SmartDNS` перед включением. Адрес хранится в настройках модуля Shadowrocket,
а публичный файл содержит только шаблон.

Основной `dns-server` и резервный `fallback-dns-server` остаются из активного
конфига. Добавлять публичные DNS в модуль для запаса не требуется.
Smart DNS применяется ко всем запросам, попавшим под прямые доменные правила,
а не только к Gemini. Для Gemini используйте также модуль Google AI Smart DNS.

Установите DNS Override самым верхним в списке модулей.

Публичный файл:
https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/modules/dns_override.module
