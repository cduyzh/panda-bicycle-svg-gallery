import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scoring
import server


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.data = scoring.load_data()
        self.name = next(iter(self.data["reviews"]))

    def test_all_current_works_and_original_control_scores(self):
        result = scoring.audit(self.data)
        self.assertEqual(len(result["scored"]), len(scoring.svg_files()))
        self.assertEqual(result["pending"] + result["stale"] + result["orphaned"], [])
        self.assertEqual(sum(review["source"] == "spreadsheet" for review in self.data["reviews"].values()), 15)
        self.assertEqual(scoring.score_for(scoring.ROOT / "Sonnet5,5 thinking Max.svg", self.data)["total"], 88)
        self.assertEqual(scoring.score_for(scoring.ROOT / "DeepSeek V4 Pro 极高.svg", self.data)["total"], 59)
        self.assertEqual(len(server.list_svgs()), len(scoring.svg_files()))

    def test_level_boundaries_and_real_zero(self):
        criteria = self.data["criteria"]
        for total, label in [(0, "有明显缺陷"), (59, "有明显缺陷"), (60, "及格"),
                             (69, "及格"), (70, "良好"), (79, "良好"), (80, "优秀"),
                             (89, "优秀"), (90, "惊艳"), (100, "惊艳")]:
            remaining = total
            review = self.data["reviews"][self.name]
            for item in criteria:
                review["scores"][item["code"]] = min(remaining, item["max"])
                remaining -= review["scores"][item["code"]]
            score = scoring.score_for(scoring.ROOT / self.name, scoring.validate(self.data))
            self.assertEqual(score["status"], "scored")
            self.assertEqual(score["level"], label)
            self.assertEqual(score["total"], total)

    def test_new_file_and_changed_content_do_not_inherit_scores(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / self.name
            file.write_text("<svg/>")
            score = scoring.score_for(file, self.data)
            self.assertEqual(score["status"], "stale")
            self.assertNotIn("total", score)
            new = Path(directory) / "新模型 默认.svg"
            new.write_text("<svg/>")
            self.assertEqual(scoring.score_for(new, self.data)["status"], "pending")
        self.data["rubricVersion"] = "2.0"
        self.assertEqual(scoring.score_for(scoring.ROOT / self.name, self.data)["status"], "stale")

    def test_invalid_inputs_are_rejected(self):
        for value in [None, -1, 13, True, float("nan"), "10"]:
            data = copy.deepcopy(self.data)
            data["reviews"][self.name]["scores"]["A1"] = value
            with self.assertRaises(ValueError):
                scoring.validate(data)
        data = copy.deepcopy(self.data)
        del data["reviews"][self.name]["scores"]["B4"]
        with self.assertRaises(ValueError):
            scoring.validate(data)
        data = copy.deepcopy(self.data)
        data["criteria"][0]["max"] = 13
        with self.assertRaises(ValueError):
            scoring.validate(data)

    def test_apply_requires_evidence_and_preserves_data_on_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            file = root / "新作品.svg"
            file.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 800"/>')
            source = root / "scoring.json"
            scoring.write_json(source, self.data)
            before = source.read_bytes()
            with patch.object(scoring, "ROOT", root), patch.object(scoring, "DATA_PATH", source):
                out = root / "work/review"
                scoring.prepare(self.data, out, [file.name])
                plan = json.loads((out / "capture-plan.json").read_text())
                self.assertEqual(plan["shots"][0]["viewport"], {"width": 1200, "height": 800})
                review_path = out / "review.json"
                review = json.loads(review_path.read_text())
                row = review["reviews"][file.name]
                row["scores"] = {key: 0 for key in row["scores"]}
                row["comment"] = "测试作品，核心内容缺失。"
                row["reviewer"] = "测试评审"
                row["notes"] = {code: "本测试仅检查更新合同。" for code in "ABCD"}
                scoring.write_json(review_path, review)
                with self.assertRaises(ValueError):
                    scoring.apply_reviews(self.data, review_path)
                self.assertEqual(source.read_bytes(), before)
                for shot in plan["shots"]:
                    shot_file = out / shot["output"]
                    shot_file.parent.mkdir(parents=True, exist_ok=True)
                    shot_file.write_bytes(b"test evidence")
                file.write_text("<svg/>")
                with self.assertRaises(ValueError):
                    scoring.apply_reviews(self.data, review_path)
                self.assertEqual(source.read_bytes(), before)
                file.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 800"/>')
                scoring.apply_reviews(self.data, review_path)
                updated = scoring.load_data()
                self.assertEqual(scoring.score_for(file, updated)["total"], 0)
                self.assertEqual(updated["reviews"][self.name], self.data["reviews"][self.name])


if __name__ == "__main__":
    unittest.main()
