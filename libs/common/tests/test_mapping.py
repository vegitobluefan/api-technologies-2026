import unittest
from datetime import date, datetime, timezone

from platform_common.mapping import iso_utc, to_company_group, to_company_info

ROW = {"inn": "7700000001", "ogrn": "1027700000001", "kpp": None, "short_name": "ООО «Ромашка»",
       "full_name": None, "status": "ACTIVE", "registration_date": date(2012, 3, 15),
       "legal_address": "г. Москва", "okved_code": "64.19", "okved_name": "Прочее",
       "group_id": "grp-1", "group_relation": "PARENT", "is_bank_client": True,
       "data_as_of": datetime(2026, 9, 23, 6, 15, tzinfo=timezone.utc)}


class MappingTests(unittest.TestCase):
    def test_iso_utc(self):
        self.assertEqual(iso_utc(datetime(2026, 9, 23, 6, 15)), "2026-09-23T06:15:00Z")

    def test_company_info(self):
        d = to_company_info(ROW)
        self.assertEqual(d["registrationDate"], "2012-03-15")
        self.assertEqual(d["mainActivity"], {"code": "64.19", "name": "Прочее"})
        self.assertIsNone(d["kpp"])
        self.assertNotIn("fullName", d)
        self.assertEqual(d["dataAsOf"], "2026-09-23T06:15:00Z")
        self.assertIs(d["isBankClient"], True)

    def test_group_filter(self):
        rows = [dict(ROW, inn="1"), dict(ROW, inn="2", is_bank_client=False, group_relation="SUBSIDIARY")]
        at = ROW["data_as_of"]
        allm = to_company_group("1", "grp-1", "Группа", rows, False, at)
        only = to_company_group("1", "grp-1", "Группа", rows, True, at)
        self.assertEqual(allm["totalMembers"], 2)
        self.assertEqual([m["inn"] for m in only["members"]], ["1"])
        self.assertEqual(only["totalMembers"], 1)

    def test_no_group(self):
        d = to_company_group("1", None, None, [], False, ROW["data_as_of"])
        self.assertEqual((d["groupId"], d["members"], d["totalMembers"]), (None, [], 0))


if __name__ == "__main__":
    unittest.main()
