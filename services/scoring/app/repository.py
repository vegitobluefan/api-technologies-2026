"""Данные для скоринга (владелец: Фёдор)."""


def load_company_for_scoring(inn: str) -> dict | None:
    """None, если компании нет в company_snapshot (-> 404 COMPANY_NOT_FOUND). Иначе:
      {"company": {"inn", "reg_date": date, "okved": str, "status": str},
       "members": [{"inn", "is_bank_client": bool}, ...]   # вся группа, включая саму компанию; [] если группы нет
       "data_as_of": datetime}
    SQL: строка из company_snapshot по inn; если group_id не NULL — все строки с этим group_id."""
    raise NotImplementedError
