import threading
import time
import unittest
from datetime import date

from app import spark_parse as p
from app.rate_limiter import RateLimiter


class SparkParseTests(unittest.TestCase):
    def test_pick_ignores_case(self):
        self.assertEqual(p.pick({"INN": "1"}, "Inn"), "1")
        self.assertIsNone(p.pick({"Inn": ""}, "Inn"))

    def test_find_list_nested(self):
        resp = {"Page": 1, "Companies": {"Company": [{"Inn": "7700000001"}, {"Inn": "7700000002"}]}}
        self.assertEqual([p.inn_of(i) for i in p.find_list(resp)], ["7700000001", "7700000002"])
        self.assertEqual(p.find_list(["1", "2"]), ["1", "2"])
        self.assertEqual(p.find_list(None), [])

    def test_company_row(self):
        report = {"Company": {"Inn": "7700000001", "Ogrn": "1027700000001", "ShortName": "ООО «А»",
                              "Status": {"Code": "active"}, "RegistrationDate": "2012-03-15T00:00:00",
                              "MainActivity": {"Code": "62.01", "Name": "Разработка ПО"}}}
        group = {"Group": {"GroupId": "G1", "GroupName": "Группа А", "Relation": "PARENT"}}
        row = p.to_company_row(report, group)
        self.assertEqual(row["inn"], "7700000001")
        self.assertEqual(row["status"], "ACTIVE")
        self.assertEqual(row["registration_date"], date(2012, 3, 15))
        self.assertEqual((row["okved_code"], row["okved_name"]), ("62.01", "Разработка ПО"))
        self.assertEqual((row["group_id"], row["group_relation"]), ("G1", "PARENT"))
        self.assertEqual(p.group_name_of(group), "Группа А")

    def test_company_without_group(self):
        row = p.to_company_row({"Inn": "7700000003", "OkvedCode": "41.20"}, None)
        self.assertIsNone(row["group_id"])
        self.assertEqual(row["okved_code"], "41.20")


class RateLimiterTests(unittest.TestCase):
    def test_limit_shared_by_threads(self):
        limiter = RateLimiter(20)
        t0 = time.monotonic()
        threads = [threading.Thread(target=limiter.wait) for _ in range(11)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertGreaterEqual(time.monotonic() - t0, 0.45)   # 11 вызовов при 20/с >= 0.5 с


if __name__ == "__main__":
    unittest.main()
