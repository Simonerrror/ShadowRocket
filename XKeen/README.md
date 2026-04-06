# XKeen

`05_routing.json` в этой директории повторяет текущую логику маршрутизации из
`shadowrocket.conf`:

- `whitelist_direct` уходит в `direct`;
- `google-all`, `microsoft` и `domains_community` уходит в прокси;
- `.ru`, `.su`, `.рф` и `geoip:ru` уходит в `direct`;
- всё остальное уходит в прокси.

Файл рассчитан на типовой `04_outbounds.json` из XKeen, где прокси-outbound имеет
тег `vless-reality`. Если у вас другой тег, пересоберите файл:

```bash
python3 scripts/build_xkeen_routing.py --proxy-tag my-proxy-tag
```

Установка:

1. Скопируйте [05_routing.json](/Users/sergio/Documents/30_HOBBY_AI/shadorock/ShadowRocket/XKeen/05_routing.json) в `/opt/etc/xray/configs/05_routing.json`.
2. Убедитесь, что в `04_outbounds.json` есть outbound с тегом `vless-reality` или вашим кастомным тегом.
3. Перезапустите XKeen: `xkeen -restart`.

Ограничение: Xray field-rules не поддерживают `IP-ASN`, поэтому ASN-записи из
`domains_community.list` в этот JSON не попадают.
