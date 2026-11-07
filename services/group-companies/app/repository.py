"""Доступ к данным Group Companies (владелец: Павел)."""


def get_group(inn: str) -> dict | None:
    """Вернуть None, если компании с таким ИНН нет в company_snapshot (-> 404 COMPANY_NOT_FOUND).
    Иначе dict:
      {"group_id": str | None, "group_name": str | None,
       "rows": [строки company_snapshot всех компаний группы, включая запрошенную; [] если группы нет],
       "data_as_of": datetime}
    SQL: SELECT group_id, group_name, data_as_of FROM company_snapshot WHERE inn=%s;
         SELECT * FROM company_snapshot WHERE group_id=%s ORDER BY inn;"""
    raise NotImplementedError
