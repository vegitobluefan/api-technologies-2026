"""Устойчивость разбора ответов СПАРК: обёртки, посторонние списки, обязательные поля, связь с группой."""
import unittest
from datetime import date

from app import spark_parse as p
from app.spark_errors import MappingError

REPORT = {"Inn": "7700000001", "ShortName": "ООО А", "Status": "ACTIVE", "RegistrationDate": "2012-03-15"}


class HardeningTests(unittest.TestCase):
    def test_record_found_in_deep_wrapper(self):
        resp = {"ShortReport": {"Company": REPORT, "Meta": {"Source": "x"}}}
        row = p.to_company_row(resp, None)
        self.assertEqual((row["inn"], row["short_name"], row["status"]), ("7700000001", "ООО А", "ACTIVE"))

    def test_service_status_does_not_hide_company(self):
        resp = {"Status": "OK", "Company": REPORT}
        self.assertEqual(p.to_company_row(resp, None)["short_name"], "ООО А")

    def test_inn_from_request_when_missing_in_answer(self):
        rep = {"ShortName": "ООО Б", "Status": "ACTIVE", "RegistrationDate": "2020-01-01"}
        self.assertEqual(p.to_company_row(rep, None, inn="7700000009")["inn"], "7700000009")

    def test_check_row_rejects_empty_and_lists_keys(self):
        row = p.to_company_row({"Foo": "bar"}, None, inn="7700000001")
        with self.assertRaises(MappingError) as ctx:
            p.check_row(row, {"Foo": "bar"})
        text = str(ctx.exception)
        self.assertIn("short_name", text)
        self.assertIn("Foo", text)

    def test_check_row_passes_good_row(self):
        p.check_row(p.to_company_row(REPORT, None))

    def test_find_list_prefers_list_with_inns(self):
        resp = {"Warnings": [], "Tags": ["a", "b"], "Companies": {"Company": [{"Inn": "7700000001"}]}}
        self.assertEqual(p.find_list(resp), [{"Inn": "7700000001"}])

    def test_find_list_falls_back_to_first_list(self):
        self.assertEqual(p.find_list({"Items": [{"x": 1}]}), [{"x": 1}])
        self.assertEqual(p.find_list({"Warnings": []}), [])

    def test_inn_forms(self):
        self.assertEqual(p.inn_of(7700000001), "7700000001")
        self.assertEqual(p.inn_of({"Company": {"Inn": 7700000003}}), "7700000003")
        self.assertIsNone(p.inn_of({"Foo": 1}))
        self.assertIsNone(p.inn_of(None))

    def test_relation_from_members_list(self):
        group = {"Group": {"GroupId": "G1", "GroupName": "Группа", "Members": {"Member": [
            {"Inn": "7700000001", "Relation": "subsidiary"}, {"Inn": "7700000002", "Relation": "parent"}]}}}
        row = p.to_company_row(REPORT, group)
        self.assertEqual((row["group_id"], row["group_relation"]), ("G1", "SUBSIDIARY"))
        self.assertEqual(p.group_name_of(group), "Группа")

    def test_relation_on_group_level_wins(self):
        group = {"GroupId": "G1", "Relation": "affiliate", "Members": [{"Inn": "7700000001", "Relation": "parent"}]}
        self.assertEqual(p.to_company_row(REPORT, group)["group_relation"], "AFFILIATE")

    def test_no_group_variants(self):
        for group in (None, {}, {"Group": None}, {"GroupId": ""}):
            row = p.to_company_row(REPORT, group)
            self.assertIsNone(row["group_id"], group)
            self.assertIsNone(p.group_name_of(group))

    def test_dates_and_types(self):
        self.assertEqual(p.to_date("2012-03-15T00:00:00"), date(2012, 3, 15))
        self.assertIsNone(p.to_date(""))
        row = p.to_company_row({**REPORT, "Ogrn": 1027700000001, "Kpp": 770001001}, None)
        self.assertEqual((row["ogrn"], row["kpp"]), ("1027700000001", "770001001"))


REAL_REPORT = {
    "INN": "5030357423", "OGRN": "1985052376087", "KPP": "503001001", "ShortName": "ООО «Уральская Гавань»",
    "FullName": "Общество с ограниченной ответственностью «Уральская Гавань»", "Status": "ACTIVE",
    "RegistrationDate": "1998-08-03", "RegionCode": "50",
    "LegalAddress": "262387, Московская область, г. Подольск, ул. Гагарина, д. 18, оф. 159",
    "OKVED": {"Code": "49.41", "Name": "Деятельность автомобильного грузового транспорта"},
    "AuthorizedCapital": 68000, "EmployeeCount": 68,
    "Head": {"FullName": "Попов Дмитрий Иванович", "Position": "Директор"},
    "GroupId": "grp-000019", "Revision": 3, "ActualDate": "2026-10-30 20:53:39+00:00"}
REAL_GROUP = {"GroupId": "grp-000019", "GroupName": "Группа «Балтийская Звезда»", "Members": {"Member": [
    {"INN": "2515633287", "ShortName": "ООО «Балтийская Звезда»", "Role": "parent", "SharePercent": "100.0", "Status": "ACTIVE"},
    {"INN": "2579091449", "ShortName": "АО «Волжская Компания»", "Role": "affiliate", "SharePercent": "25.0", "Status": "ACTIVE"},
    {"INN": "5030357423", "ShortName": "ООО «Уральская Гавань»", "Role": "subsidiary", "SharePercent": "75.9", "Status": "ACTIVE"}]}}


class RealDataTests(unittest.TestCase):
    """Ответы, снятые с настоящего мока СПАРК (probe.txt). Если мок или наш разбор поменяются, это упадёт."""

    def test_report_and_group_to_row(self):
        row = p.to_company_row(REAL_REPORT, REAL_GROUP, "5030357423")
        self.assertEqual(row, {
            "inn": "5030357423", "ogrn": "1985052376087", "kpp": "503001001",
            "short_name": "ООО «Уральская Гавань»",
            "full_name": "Общество с ограниченной ответственностью «Уральская Гавань»",
            "status": "ACTIVE", "registration_date": date(1998, 8, 3),
            "legal_address": "262387, Московская область, г. Подольск, ул. Гагарина, д. 18, оф. 159",
            "director": "Попов Дмитрий Иванович", "okved_code": "49.41",
            "okved_name": "Деятельность автомобильного грузового транспорта",
            "group_id": "grp-000019", "group_relation": "SUBSIDIARY"})
        p.check_row(row, REAL_REPORT)
        self.assertEqual(p.group_name_of(REAL_GROUP), "Группа «Балтийская Звезда»")

    def test_actual_date_and_revision(self):
        from datetime import datetime, timezone
        expected = datetime(2026, 10, 30, 20, 53, 39, tzinfo=timezone.utc)
        self.assertEqual(p.actual_date_of(REAL_REPORT), expected)
        self.assertEqual(p.actual_date_of({**REAL_REPORT, "ActualDate": expected}), expected)
        self.assertEqual(p.actual_date_of({**REAL_REPORT, "ActualDate": "2026-10-30T20:53:39Z"}), expected)
        self.assertEqual(p.actual_date_of({**REAL_REPORT, "ActualDate": "2026-10-30 20:53:39"}), expected)   # без пояса = UTC
        self.assertIsNone(p.actual_date_of({**REAL_REPORT, "ActualDate": "не дата"}))
        self.assertEqual(p.revision_of(REAL_REPORT), 3)

    def test_has_group(self):
        self.assertTrue(p.has_group(REAL_REPORT))
        self.assertFalse(p.has_group({k: v for k, v in REAL_REPORT.items() if k != "GroupId"}))
        self.assertFalse(p.has_group({**REAL_REPORT, "GroupId": None}))

    def test_company_without_group_in_real_shape(self):
        rep = {k: v for k, v in REAL_REPORT.items() if k != "GroupId"}
        row = p.to_company_row(rep, None, "5030357423")
        self.assertIsNone(row["group_id"])
        p.check_row(row, rep)


class RealShapeTests(unittest.TestCase):
    """Формы ответов, снятые с настоящего мока (probe.txt)."""

    LIST = {"Total": 1000, "Page": 1, "Companies": {"Company": [
        {"INN": "5030357423", "ShortName": "ООО «Уральская Гавань»", "Status": "ACTIVE"},
        {"INN": "0537950913", "ShortName": "ООО «Медиа Палитра»", "Status": "LIQUIDATING"}]}}
    CHANGES = {"Total": 40, "Page": 1, "Changes": {"Change": [
        {"INN": "7755120778", "ChangedAt": "2026-11-10 10:09:45+00:00", "ChangeType": "head"},
        {"INN": "0260815076", "ChangedAt": "2026-11-10 14:53:01+00:00", "ChangeType": "group"}]}}

    def test_company_list(self):
        inns = [p.inn_of(i) for i in p.find_list(self.LIST)]
        self.assertEqual(inns, ["5030357423", "0537950913"])          # ведущий ноль не теряется
        self.assertEqual(p.pick(self.LIST, "Total"), 1000)

    def test_changes_list(self):
        items = p.find_list(self.CHANGES)
        self.assertEqual([p.inn_of(i) for i in items], ["7755120778", "0260815076"])
        self.assertEqual({i["ChangeType"] for i in items}, {"head", "group"})


if __name__ == "__main__":
    unittest.main()
