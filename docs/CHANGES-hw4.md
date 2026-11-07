# Изменения архитектуры и контрактов в ДЗ 4

| Что | Было (ДЗ 1–2) | Стало (ДЗ 4) | Почему |
|---|---|---|---|
| Scoring → ML Model | REST (`contracts/ml-model/openapi.yaml`, `POST /v1/predictions`) | gRPC (`proto/scoring.proto`) | требование задания; REST-контракт ML Model заменён `.proto` |
| Enrichment → АБС | не было связи на диаграмме | REST `/abs/v1/legal-clients:lookup` пачками до 500 ИНН | источник `isBankClient` |
| Аналитический контур | в архитектуре | не реализуется в ДЗ 4 | явно исключён заданием |
| Признак `groupBankClientsCount` | «компаний группы — клиенты банка» | число **других** компаний группы, клиентов банка (без самой компании) | так определено в `meta["feature_doc"]` модели |
| Версия модели в примерах | `lead-scoring-2026.09.1` | `company-scoring`, `1.0.0` | реальная модель из задания |

Остальное (Gateway, Client Info, Group Companies, Scoring, Redis, Postgres) соответствует `architecture/container.mmd`.
Диаграмму `container.png` перерисовать из обновлённого `container.mmd` (файл в LFS).
