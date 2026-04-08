# XKeen

`05_routing.json` в этой директории повторяет текущую логику маршрутизации
из базового `shadowrocket.conf` и собирается по порядку строк из `[Rule]`.

- `RULE-SET ... DIRECT` уходит в `direct`;
- `RULE-SET ... PROXY` и `RULE-SET ... GOOGLE` уходит в прокси;
- inline `DOMAIN*`/`IP-CIDR*`/`GEOIP` повторяются в том же порядке;
- `FINAL` превращается в финальное проксирующее правило.

Файл рассчитан на типовой `04_outbounds.json` из XKeen, где прокси-outbound имеет
тег `vless-reality`. Если у вас другой тег, пересоберите файл:

```bash
python3 scripts/build_xkeen_routing.py --conf shadowrocket.conf --proxy-tag my-proxy-tag
```

Установка:

1. Скопируйте `XKeen/05_routing.json` в `/opt/etc/xray/configs/05_routing.json`.
2. Убедитесь, что в `04_outbounds.json` есть outbound с тегом `vless-reality` или вашим кастомным тегом.
3. Перезапустите XKeen: `xkeen -restart`.

Ограничение: Xray field-rules не поддерживают `IP-ASN`, поэтому ASN-записи из
`domains_community.list` в этот JSON не попадают.
