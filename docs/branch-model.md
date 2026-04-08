# Branch Model

Этот репозиторий использует три роли веток:

- `main` — release/publish-ветка. Именно из нее раздаются публичные raw URL, включая `shadowrocket.conf`, `HAPP/DEFAULT.DEEPLINK`, `rules/*.list` и `XKeen/05_routing.json`.
- `source/main` — shared source-of-truth. Здесь живут manifest, overlays, filters, скрипты, документация и базовые конфиги.
- `custom/sergio` — personal source-ветка. Здесь живут GFN/NVIDIA и прочие single-user отклонения.

## Правила изменений

- Любая задача должна быть явно классифицирована как `shared`, `custom-only` или `promote-to-main`.
- `custom-only` по умолчанию относится к GFN/NVIDIA и single-user поведению.
- Если изменение оказалось полезным всем, его сначала переносят в `source/main`, затем подтягивают в `custom/sergio`.

## Generated artifacts

В source-ветках не коммитятся:

- `distillate/upstream/`
- `distillate/text/`
- `distillate/dat/`
- `distillate/summary.json`
- generated `rules/*.list`
- `HAPP/DEFAULT.*`
- `XKeen/05_routing.json`

Эти файлы собираются workflow `publish-release.yml` и публикуются в `main` только при содержательном diff.
