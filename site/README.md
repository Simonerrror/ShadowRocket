# Сайт ShadowRocket

[Открыть сайт](https://simonerrror.github.io/ShadowRocket/).

`site/index.html` — исходник страницы с кнопками основного конфига,
всех модулей и двух профилей INCY. Пояснения находятся в раскрывающихся блоках.
Номера и названия модулей совпадают с `#!name` и
[общей таблицей](../docs/shadowrocket-modules.md#порядок-модулей).
DNS Override Example открывает текст для локальной копии без URL обновления.

Кнопки Shadowrocket используют `shadowrocket://`, кнопки INCY — `incy://`.
Переадресация через внешний сервер не требуется. Если браузер мессенджера
не открывает приложение, откройте сайт в Safari.

После изменения страницы или профилей INCY выполните:

```sh
python3 scripts/build_site.py
python3 -m unittest discover -s tests
```

Сборка проверяет INCY deeplink и создаёт `docs/index.html`.
Не редактируйте generated-страницу вручную. Изображения и favicon находятся
в `docs/images/` и `docs/favicon.svg`; пути в HTML относительные.

В настройках Pages выберите `Deploy from a branch`, ветку `main`, каталог `/docs`.
GitHub публикует страницу штатным механизмом Pages. `deploy-pages.yml`
проверяет сборку перед запросом публикации; после успешного `Sync rule lists`
запрашивает пересборку отдельно. Node, npm и Cloudflare для сайта не используются.
