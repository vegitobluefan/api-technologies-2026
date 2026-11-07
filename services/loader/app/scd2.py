"""SCD2-запись истории (владелец: Артём).

upsert_company(conn, company, now) в ОДНОЙ транзакции:
  1) прочитать текущую версию (is_current) по inn;
  2) посчитать attrs_hash по бизнес-атрибутам (см. колонки company_versions без id/valid_*/is_current);
  3) хэш совпал -> ничего не делать (повторная загрузка не плодит версий);
     иначе закрыть текущую (valid_to=now, is_current=false) и вставить новую (valid_from=now, is_current=true).
company — dict с ключами = колонкам company_versions.
Группы: upsert_group(conn, group_id, group_name) -> таблица company_groups.
"""


def upsert_company(conn, company: dict, now) -> bool:
    """Возвращает True, если создана новая версия."""
    raise NotImplementedError


def upsert_group(conn, group_id: str, group_name: str) -> None:
    raise NotImplementedError
