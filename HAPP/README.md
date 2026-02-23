# HAPP Routing: установка и ссылки

## Быстрые ссылки

- Deeplink (текстовый файл для копирования):  
  [DEFAULT.DEEPLINK](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/HAPP/DEFAULT.DEEPLINK)
- JSON профиль:  
  [DEFAULT.JSON](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/HAPP/DEFAULT.JSON)
- Geo-файлы профиля:  
  [geoip.dat](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/HAPP/geoip.dat)  
  [geosite.dat](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/HAPP/geosite.dat)
- Отчет сборки:  
  [REPORT.md](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/HAPP/REPORT.md)

## Логика HAPP

- Основная схема: `RU -> DIRECT`, остальное `-> PROXY`.
- В HAPP-сборке используются списки `whitelist_direct.list`, `greylist_proxy.list`, `domains_community.list`, `telegram.list`.
- Списки `google-all.list`, `microsoft.list`, `voice_ports.list` в HAPP не участвуют.
- `geoip.dat` собирается как IPv4-only.
- DNS для HAPP берется из `shadowrocket.conf`:
  - `dns-server` -> `RemoteDNS`
  - `fallback-dns-server` -> `DomesticDNS`

## Как добавить в Happ

1. Открой на устройстве с Happ ссылку `DEFAULT.DEEPLINK` (выше).
2. Скопируй строку `happ://routing/onadd/...` целиком.
3. Вставь ее в адресную строку Safari и открой.
4. Подтверди открытие в Happ и добавление маршрутизации.

## Если deeplink не открылся

1. Убедись, что Happ установлен и обновлен.
2. Попробуй открыть deeplink еще раз через Safari (не через встроенный вебвью).
3. Используй JSON-вариант `DEFAULT.JSON` для ручного импорта в Happ.

## Локальная пересборка

```bash
python scripts/build_happ_routing.py
```
