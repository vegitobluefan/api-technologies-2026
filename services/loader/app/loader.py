"""Первичная загрузка 1000 компаний и групп (владелец: Данияр).
Продолжается после падения (прогресс в load_state), идемпотентна (запись только через scd2.upsert_company).
В конце ОБЯЗАТЕЛЬНО: set_state('initial_loaded_at', <время начала>), set_state('last_sync_at', <то же>),
set_state('initial_done', 'true') — по этому флагу ждут Enrichment и demo.sh."""


def initial_load(client): ...
