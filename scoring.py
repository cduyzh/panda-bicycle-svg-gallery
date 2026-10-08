"""画廊评分数据、校验及新增作品的评审入口（仅使用 Python 标准库）。"""

import argparse
import datetime
import hashlib
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "scoring.json"
SAMPLE_TIMES = [0, 120, 360, 600, 1000, 1500, 2000, 6000, 12000, 30000, 30120]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def validate(data):
    if data.get("schemaVersion") != 1 or not data.get("rubricVersion"):
        raise ValueError("评分数据版本缺失或不支持")
    criteria = data["criteria"]
    codes = [item["code"] for item in criteria]
    if len(codes) != len(set(codes)) or not codes:
        raise ValueError("评分小项代号必须唯一且非空")
    dimensions = {item["code"]: item for item in data["dimensions"]}
    if len(dimensions) != len(data["dimensions"]):
        raise ValueError("维度代号重复")
    for item in criteria:
        if item["dimension"] not in dimensions or type(item["max"]) is not int or item["max"] <= 0:
            raise ValueError("小项的维度或满分无效")
    if sum(item["max"] for item in criteria) != 100:
        raise ValueError("评分满分合计必须为 100")
    for code, dimension in dimensions.items():
        if dimension["max"] != sum(item["max"] for item in criteria if item["dimension"] == code):
            raise ValueError(f"维度 {code} 的分值不等于小项合计")
    levels = data["levels"]
    floors = [level["min"] for level in levels]
    if floors != sorted(set(floors), reverse=True) or floors[-1] != 0 or any(type(n) is not int or not 0 <= n <= 100 for n in floors):
        raise ValueError("档位下限必须由高到低、唯一，并覆盖 0 分")
    for filename, review in data["reviews"].items():
        if Path(filename).name != filename or Path(filename).suffix.lower() != ".svg":
            raise ValueError(f"评分键必须是原始 SVG 文件名：{filename}")
        if set(review["scores"]) != set(codes):
            raise ValueError(f"{filename}：13 个小项必须完整且无额外项")
        for item in criteria:
            score = review["scores"][item["code"]]
            if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= item["max"]:
                raise ValueError(f"{filename}：{item['code']} 分数缺失或越界")
        for key in ("comment", "reviewer", "reviewedAt", "rubricVersion", "source"):
            if not isinstance(review.get(key), str) or not review[key].strip():
                raise ValueError(f"{filename}：缺少 {key}")
        if review["source"] not in ("spreadsheet", "supplemental") or not re.fullmatch(r"[0-9a-f]{64}", review.get("sha256", "")):
            raise ValueError(f"{filename}：来源或 SHA-256 无效")
        if review["source"] == "supplemental":
            if set(review.get("notes", {})) != set(dimensions) or any(not str(value).strip() for value in review["notes"].values()):
                raise ValueError(f"{filename}：需填写四个维度的评分依据")
            evidence = review.get("evidence", {})
            if not evidence.get("capturePlan") or len(evidence.get("sampleTimesMs", [])) < 3:
                raise ValueError(f"{filename}：缺少动画时间点证据")
    return data


def load_data():
    return validate(json.loads(DATA_PATH.read_text(encoding="utf-8")))


def score_for(path, data):
    review = data["reviews"].get(path.name)
    if not review:
        return {"status": "pending", "comment": "新作品已收录，等待按公开标准评审。"}
    if review["sha256"] != digest(path) or review["rubricVersion"] != data["rubricVersion"]:
        return {"status": "stale", "comment": "作品或评分规则已更新，等待重新评审。"}
    scores = review["scores"]
    total = sum(scores.values())
    dimensions = {
        dimension["code"]: sum(scores[item["code"]] for item in data["criteria"] if item["dimension"] == dimension["code"])
        for dimension in data["dimensions"]
    }
    return {
        "status": "scored", "total": total,
        "level": next(level["label"] for level in data["levels"] if total >= level["min"]),
        "dimensions": dimensions, "scores": scores,
        "comment": review["comment"], "source": review["source"],
        "reviewedAt": review["reviewedAt"], "reviewer": review["reviewer"],
        "notes": review.get("notes", {}), "evidence": review.get("evidence", {}),
    }


def svg_files():
    return sorted((path for path in ROOT.iterdir() if path.is_file() and path.suffix.lower() == ".svg"), key=lambda path: path.name)


def technical_facts(path):
    facts = {"bytes": path.stat().st_size, "sha256": digest(path)}
    try:
        root = ET.parse(path).getroot()
        nodes = list(root.iter())
        tag = lambda node: node.tag.rsplit("}", 1)[-1]
        ids = [node.get("id") for node in nodes if node.get("id")]
        text = path.read_text(encoding="utf-8")
        external = [value for node in nodes for key, value in node.attrib.items() if key.rsplit("}", 1)[-1] == "href" and not value.startswith("#")]
        external += re.findall(r"(?:url\(\s*['\"]?(?!#)(?:https?:|//|data:)[^)]+|@import\s+[^;]+)", text)
        facts.update({"xmlValid": True, "svgRoot": tag(root) == "svg", "elements": len(nodes),
                      "duplicateIds": sorted({value for value in ids if ids.count(value) > 1}),
                      "externalReferences": external, "scripts": sum(tag(node) == "script" for node in nodes),
                      "eventHandlers": [key for node in nodes for key in node.attrib if key.lower().startswith("on")],
                      "hasTitle": any(tag(node) == "title" for node in nodes), "hasDesc": any(tag(node) == "desc" for node in nodes),
                      "smilCount": sum(tag(node) in ("animate", "animateTransform", "animateMotion", "set") for node in nodes),
                      "durations": sorted({node.get("dur") for node in nodes if node.get("dur")}),
                      "cssKeyframes": len(re.findall(r"@keyframes\b", text)), "useCount": sum(tag(node) == "use" for node in nodes)})
    except (ET.ParseError, UnicodeError) as error:
        facts.update({"xmlValid": False, "error": str(error)})
    return facts


def svg_viewport(path):
    """按原 SVG 画布截图，避免固定窗口裁掉大尺寸作品。"""
    try:
        attrs = ET.parse(path).getroot().attrib
        box = [float(value) for value in attrs.get("viewBox", "0 0 900 600").replace(",", " ").split()]
        size = []
        for name, fallback in zip(("width", "height"), box[2:]):
            value = attrs.get(name, "")
            size.append(float(value.removesuffix("px")) if re.fullmatch(r"[\d.]+(?:px)?", value) else fallback)
        return {"width": max(1, min(1920, round(size[0]))), "height": max(1, min(1920, round(size[1])))}
    except (ET.ParseError, ValueError, IndexError):
        return {"width": 900, "height": 600}


def audit(data):
    result = {"scored": [], "pending": [], "stale": [], "orphaned": []}
    files = svg_files()
    for path in files:
        result[score_for(path, data)["status"]].append(path.name)
    result["orphaned"] = sorted(set(data["reviews"]) - {path.name for path in files})
    return result


def prepare(data, output, filenames):
    files = svg_files()
    if filenames:
        unknown = set(filenames) - {path.name for path in files}
        if unknown:
            raise ValueError(f"未找到文件：{sorted(unknown)}")
        files = [path for path in files if path.name in filenames]
    else:
        files = [path for path in files if score_for(path, data)["status"] != "scored"]
    if not files:
        print("没有待评分或待复评的作品。")
        return
    if (output / "review.json").exists():
        raise ValueError("review.json 已存在；请使用新的 --out 目录，以保留已有评审")
    records, shots = {}, []
    for index, path in enumerate(files, 1):
        key = f"{index:02d}"
        records[path.name] = {"sha256": digest(path), "rubricVersion": data["rubricVersion"], "source": "supplemental",
                              "reviewedAt": datetime.date.today().isoformat(), "reviewer": "", "comment": "",
                              "scores": {item["code"]: None for item in data["criteria"]},
                              "notes": {item["code"]: "" for item in data["dimensions"]},
                              "evidence": {"capturePlan": str((output / "capture-plan.json").relative_to(ROOT)),
                                           "sampleTimesMs": SAMPLE_TIMES}, "technical": technical_facts(path)}
        shots.extend({"url": str(path), "timeMs": time, "output": f"frames/{key}-{time:05d}.png", "viewport": svg_viewport(path)} for time in SAMPLE_TIMES)
    write_json(output / "capture-plan.json", {"viewport": {"width": 900, "height": 600}, "timeoutMs": 180000, "shots": shots})
    write_json(output / "review.json", {"rubricVersion": data["rubricVersion"], "reviews": records})
    print(f"已准备 {len(files)} 份作品：{output.relative_to(ROOT)}/review.json")


def apply_reviews(data, path):
    patch = json.loads(path.read_text(encoding="utf-8"))
    if patch.get("rubricVersion") != data["rubricVersion"] or not patch.get("reviews"):
        raise ValueError("评审版本不一致或评审为空")
    candidate = {**data, "reviews": {**data["reviews"], **patch["reviews"]}}
    validate(candidate)
    for filename, review in patch["reviews"].items():
        file = ROOT / filename
        if not file.is_file() or review["sha256"] != digest(file):
            raise ValueError(f"{filename}：评审后作品已变动，必须重新检查")
        if review["source"] != "supplemental" or review["rubricVersion"] != data["rubricVersion"]:
            raise ValueError("新增评审必须标记 supplemental 并使用当前规则版本")
        plan_path = (ROOT / review["evidence"]["capturePlan"]).resolve()
        if not plan_path.is_relative_to((ROOT / "work").resolve()):
            raise ValueError("截图计划必须位于本项目 work 目录")
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        shots = [shot for shot in plan["shots"] if Path(shot["url"]).resolve() == file.resolve()]
        if {shot["timeMs"] for shot in shots} != set(review["evidence"]["sampleTimesMs"]):
            raise ValueError(f"{filename}：评审时间点与截图计划不一致")
        if any(not (plan_path.parent / shot["output"]).is_file() for shot in shots):
            raise ValueError(f"{filename}：请先完成截图和视觉评审")
    candidate["updatedAt"] = datetime.date.today().isoformat()
    write_json(DATA_PATH, candidate)
    print(f"已更新 {len(patch['reviews'])} 份评分；总分、档位和维度分由小项实时计算。")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("audit", help="检查缺评、作品改动和无对应 SVG 的旧记录")
    command = sub.add_parser("prepare", help="生成截图计划、技术检查与待填写评审")
    command.add_argument("--out", default="work/scoring-review")
    command.add_argument("--files", nargs="+")
    command = sub.add_parser("apply", help="校验已完成的评审并原子更新评分数据")
    command.add_argument("review")
    args = parser.parse_args()
    data = load_data()
    if args.command == "audit":
        result = audit(data)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return int(any(result[key] for key in ("pending", "stale", "orphaned")))
    if args.command == "prepare":
        output = (ROOT / args.out).resolve()
        if not output.is_relative_to((ROOT / "work").resolve()):
            raise ValueError("评审临时文件必须放在 work/ 内")
        prepare(data, output, args.files)
    else:
        apply_reviews(data, (ROOT / args.review).resolve())
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError, TypeError, OSError, StopIteration) as error:
        print(f"评分更新失败：{error}", file=sys.stderr)
        sys.exit(2)
