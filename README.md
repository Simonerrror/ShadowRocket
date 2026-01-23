# Shadowrocket конфиг — объяснение и настройка

Ниже описана логика правил в `shadowrocket.conf`, а также даны пошаговые инструкции по подключению.

## Как настроить

1. **Добавьте конфиг по ссылке** (вставьте в поле URL и сохраните):
   ```
   https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/shadowrocket.conf
   ```
2. **Добавьте свою подписку на сервера**: откройте список серверов/подписок в Shadowrocket и вставьте URL подписки от вашего провайдера.
3. **Создайте подгруппу `GOOGLE` и назначьте рабочий сервер**:
   * В разделе политик/групп добавьте группу с названием `GOOGLE`.
   * Выберите тип группы (например, `Select`) и укажите сервер, который стабильно работает с Google.
   * Важно: имя группы должно совпадать с `GOOGLE` в конфиге, иначе правила для Google-сервисов не будут применяться.

## Общая логика

* Секция `[General]` задаёт поведение движка (DNS, IPv6, bypass, hijack и т.д.).
* Секция `[Rule]` обрабатывается **сверху вниз**: первое совпадение останавливает дальнейшую проверку.
* Секция `[Host]` задаёт статические резолвы хостов.
* Секция `[URL Rewrite]` описывает правила редиректов на уровне URL.

## `shadowrocket.conf` построчно

### `[General]`
1. `[General]` — начало секции общих настроек приложения.
2. `bypass-system = true` — трафик, не подходящий под прокси-правила, не перехватывается системным прокси и идёт напрямую.
3. `skip-proxy = 127.0.0.1, 192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12, localhost, *.local, captive.apple.com, *.ru, *.su, *.рф` — домены и подсети, которые всегда идут мимо прокси (локальная сеть, loopback, локальные домены и зоны .ru/.su/.рф).
4. `bypass-tun = 10.0.0.0/8, 100.64.0.0/10, 127.0.0.0/8, 169.254.0.0/16, 172.16.0.0/12, 192.0.0.0/24, 192.0.2.0/24, 192.88.99.0/24, 192.168.0.0/16, 198.18.0.0/15, 198.51.100.0/24, 203.0.113.0/24, 224.0.0.0/4, 255.255.255.255/32` — список подсетей, которые не отправляются в TUN-движок (служебные сети, локальные, multicast и т.п.).
5. `dns-server = https://1.1.1.1/dns-query, https://8.8.8.8/dns-query` — основные DNS-over-HTTPS серверы.
6. `fallback-dns-server = tls://8.8.8.8, tls://1.1.1.1, https://94.140.14.14/dns-query, system` — резервные DNS-серверы (DoT/DoH и системный fallback).
7. `ipv6 = false` — отключает IPv6 в конфигурации.
8. `prefer-ipv6 = false` — запрещает приоритет IPv6 при выборе адреса.
9. `dns-direct-system = true` — при прямом подключении используется системный DNS.
10. `icmp-auto-reply = true` — автоответ на ICMP (для локальной диагностики/пинга).
11. `always-reject-url-rewrite = false` — не блокировать запросы только из-за URL Rewrite.
12. `private-ip-answer = true` — разрешить ответы DNS с приватными IP.
13. `dns-direct-fallback-proxy = false` — не проксировать DNS-fallback для прямого трафика.
14. `hijack-dns = 8.8.8.8:53, 8.8.4.4:53` — перехват DNS-запросов на указанные адреса, чтобы гарантировать обработку DNS политикой приложения.

### `[Rule]`
15. `[Rule]` — начало секции правил маршрутизации.
16. `RULE-SET,https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/whitelist_direct.list,DIRECT` — ручной whitelist для прямого доступа.
17. `RULE-SET,https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/greylist_proxy.list,PROXY,force-remote-dns` — ручной greylist, который уводится в `PROXY` с удалённым DNS.
18. `AND,((PROTOCOL,UDP),(DEST-PORT,443)),REJECT` — блокировка QUIC (UDP/443), чтобы не было обрывов в Chrome/мобайле.
19. `AND,((PROTOCOL,UDP),(DEST-PORT,853)),REJECT-NO-DROP` — блокировка DNS-over-TLS (UDP/853).
20. `RULE-SET,https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/google-gemini.list,GOOGLE,force-remote-dns` — домены Google/Gemini, трафик направляется в политику `GOOGLE`.
21. `RULE-SET,https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/google.list,GOOGLE,force-remote-dns` — расширенный список Google-доменов с удалённым DNS.
22. `RULE-SET,https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/gemini_ip.list,GOOGLE,no-resolve` — IP-диапазоны Gemini; `no-resolve` отключает доменный резолв.
23. `RULE-SET,https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/youtube.list,GOOGLE,force-remote-dns` — домены YouTube с удалённым DNS.
24. `RULE-SET,https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/youtubemusic.list,GOOGLE,force-remote-dns` — домены YouTube Music с удалённым DNS.
25. `RULE-SET,https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/microsoft.list,PROXY,force-remote-dns` — Microsoft/Office 365/Teams/OneDrive через `PROXY`.
26. `DOMAIN-SUFFIX,twitch.tv,DIRECT,pre-matching` — Twitch идёт напрямую и предварительно матчится.
27. `DOMAIN-SUFFIX,ttvnw.net,DIRECT,pre-matching` — CDN Twitch также направляется напрямую.
28. `RULE-SET,https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/domains_community.list,PROXY` — прочие доменные списки сообщества через `PROXY`.
29. `RULE-SET,https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/domain_ips.list,PROXY,no-resolve` — IP-списки через `PROXY` без DNS-резолва.
30. `RULE-SET,https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/voice_ports.list,PROXY` — списки голосовых сервисов/портов через `PROXY`.
31. `RULE-SET,https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/telegram.list,PROXY` — Telegram-домены через `PROXY`.
32. `DOMAIN-SUFFIX,ru,DIRECT` — домены зоны `.ru` идут напрямую.
33. `DOMAIN-SUFFIX,рф,DIRECT` — домены зоны `.рф` идут напрямую.
34. `DOMAIN-SUFFIX,su,DIRECT` — домены зоны `.su` идут напрямую.
35. `GEOIP,RU,DIRECT` — весь трафик по GeoIP для RU идёт напрямую.
36. `FINAL,PROXY,force-remote-dns` — финальное правило: всё, что не совпало выше, идёт в `PROXY` с принудительным удалённым DNS.

### `[Host]`
37. `[Host]` — начало секции статических хостов.
38. `localhost = 127.0.0.1` — фиксированный резолв `localhost` на loopback.

### `[URL Rewrite]`
39. `[URL Rewrite]` — начало секции URL-редиректов.
40. `^https?://(www.)?nnmclub.to https://nnmclub.to 302` — редирект `www`-версии nnmclub на канонический домен.
41. `^https?://(www.)?yandex.ru https://www.ya.ru 302` — редирект с yandex.ru на ya.ru.
