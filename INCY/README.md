# INCY Routing

**Пользователям HAPP настоятельно рекомендуем перейти на INCY: поддержка HAPP завершена.**

Готовые routing-профили для INCY. Профили строятся из distillate-агрегатов по официальному INCY-контракту:
`useChunkFiles` — boolean `false`, без поля `UseChunkFiles`.

## Ссылки

- DEFAULT (`роут-MotivatoPotato`), deeplink:
  [DEFAULT.DEEPLINK](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/INCY/DEFAULT.DEEPLINK)
- DEFAULT, JSON:
  [DEFAULT.JSON](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/INCY/DEFAULT.JSON)
- RU-VPN, deeplink:
  [RU-VPN.DEEPLINK](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/INCY/RU-VPN.DEEPLINK)
- RU-VPN, JSON:
  [RU-VPN.JSON](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/INCY/RU-VPN.JSON)
- Кликабельный DEFAULT: [potato-link/incy](https://potato-link.motivato-potato.workers.dev/incy)
- Кликабельный RU-VPN: [potato-link/incy/ru](https://potato-link.motivato-potato.workers.dev/incy/ru)

Deeplink имеет вид `incy://routing/onadd/<standard-base64-compact-json>`.
Для одноразового добавления без активации генератор поддерживает режим `add`.

## Профили

`DEFAULT` направляет обычный трафик по `sr-direct`, `sr-proxy` и
`motivato-block`. `RU-VPN` направляет `geosite:category-ru` и `geoip:ru`
через выбранный proxy, а несовпавший трафик — напрямую. Перед активацией
выберите сервер с проверенным российским выходным IP.

Оба профиля используют `RouteOrder: block-proxy-direct`, геоданные из
[release incy-geodata](https://github.com/Simonerrror/ShadowRocket/releases/tag/incy-geodata)
(`geoip.dat` и `geosite.dat`), а также сохранённый
`LastUpdated`. При наличии `.sha256` рядом с geo-файлами INCY сможет
пропускать скачивание неизменившихся файлов.

## Сборка

```bash
python3 scripts/build_incy_routing.py
python3 scripts/build_potato_link_worker.py
```

Генератор самостоятельно строит профили из distillate. Worker предоставляет
страницу ссылок на `/`, импорт INCY на `/incy` и `/incy/ru`.
