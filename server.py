"""Serve the SVG gallery and describe each original file without renaming it."""

import datetime
import http.server
import json
import re
import socketserver
import urllib.parse
from collections import defaultdict
from pathlib import Path
from scoring import load_data, score_for


PORT = 8000
DIRECTORY = Path(__file__).resolve().parent

# These are generation settings, not model names. Match a complete tail only;
# a new or unknown tail remains part of the model name to avoid false grouping.
SETTINGS = ("Ultra", "Extra", "High", "Max", "最大", "极高", "默认", "高")
SETTING_PATTERN = "|".join(re.escape(setting) for setting in SETTINGS)
RUN_PATTERN = re.compile(r"^(.*?)([\s_-]+)([1-9]\d*)$")
ATTACHED_RUN_PATTERN = re.compile(
    rf"^(.*?(?:{SETTING_PATTERN}|codex))([1-9]\d*)$", re.IGNORECASE
)


def split_run(stem, known_stems, numbered_sibling_bases=None):
    """Only interpret a final number as a run when the name makes that clear."""
    match = RUN_PATTERN.fullmatch(stem)
    if match and int(match.group(3)) >= 2:
        base = match.group(1).casefold()
        if base in known_stems or base in (numbered_sibling_bases or ()):
            return match.group(1), int(match.group(3))

    # "Max2" and "高3" have no separator, but their setting is unambiguous.
    match = ATTACHED_RUN_PATTERN.fullmatch(stem)
    if match and int(match.group(2)) >= 2:
        return match.group(1), int(match.group(2))

    return stem, None


def model_and_setting(family, model, tail):
    tail = tail.strip(" -_\t")
    if not tail:
        return family, model, ""

    match = re.fullmatch(
        rf"(.*?)(?:[\s_-]*)({SETTING_PATTERN})(?:[\s_-]+(codex))?", tail, re.IGNORECASE
    )
    if match:
        extra = match.group(1).strip(" -_\t")
        if extra:
            model += f" {extra}"
            
        setting = next(
            value for value in SETTINGS if value.casefold() == match.group(2).casefold()
        )
        if match.group(3):
            setting += " · Codex"
        return family, model, setting

    # Keeping an unfamiliar suffix in the model prevents accidental merges.
    return family, f"{model} {tail}", ""


def classify_stem(stem):
    """Return (family, precise model, setting) for the naming seen in this gallery."""
    patterns = (
        (
            "GPT",
            r"^(\d+(?:\.\d+)?)\s+(Sol|Luna|Astra)(.*)$",
            lambda m: f"{m[1]} {m[2].title()}",
        ),
        (
            "DeepSeek",
            r"^DeepSeek[\s-]+V(\d+(?:\.\d+)?)[\s-]+(Pro|Flash)(.*)$",
            lambda m: f"DeepSeek V{m[1]} {m[2].title()}",
        ),
        (
            "GLM",
            r"^GLM[\s-]+(\d+(?:\.\d+)?)(?:[\s-]+(FlashX|Flash))?(.*)$",
            lambda m: f"GLM-{m[1]}" + (f" {m[2]}" if m[2] else ""),
        ),
        (
            "Gemini",
            r"^Gemini\s+(\d+(?:\.\d+)?)\s+(Pro|Flash)(.*)$",
            lambda m: f"Gemini {m[1]} {m[2].title()}",
        ),
        (
            "Kimi",
            r"^Kimi[\s-]+k(\d+)(.*)$",
            lambda m: f"Kimi K{m[1]}",
        ),
        (
            "MiniMax",
            r"^(?:MiniMax[\s-]+)?M(\d+(?:\.\d+)?)(?:[\s-]+(Flash[\s-]+Preview))?(.*)$",
            lambda m: f"MiniMax M{m[1]}" + (" Flash Preview" if m[2] else ""),
        ),
        (
            "Qwen",
            r"^Qwen[\s-]+(\d+(?:\.\d+)?)(Flash|Max)(.*)$",
            lambda m: f"Qwen {m[1]} {m[2].title()}",
        ),
        (
            "Seed",
            r"^Seed[\s-]+(\d+(?:\.\d+)?)[\s-]+(Pro|Turbo)(.*)$",
            lambda m: f"Seed {m[1]} {m[2].title()}",
        ),
        (
            "Seed",
            r"^Seed[\s-]+Code(.*)$",
            lambda m: "Seed Code",
        ),
        (
            "Claude",
            r"^(Sonnet|Opus|Haiku)[\s-]*(\d+(?:[.,]\d+)?)(.*)$",
            lambda m: f"{m[1].title()} {m[2].replace(',', '.')}",
        ),
        (
            "Step",
            r"^Step[\s-]+(\d+)[\s-]+(Preview)(.*)$",
            lambda m: f"Step {m[1]} {m[2].title()}",
        ),
    )

    for family, pattern, make_model in patterns:
        match = re.fullmatch(pattern, stem, re.IGNORECASE)
        if match:
            return model_and_setting(family, make_model(match), match.group(match.lastindex))

    # A future model from a known maker still belongs under that maker. Its full
    # filename stem remains the model until its naming convention is understood.
    for family in ("DeepSeek", "GLM", "Gemini", "Kimi", "MiMo", "MiniMax", "Qwen", "Seed", "Step"):
        if re.match(rf"^{family}(?:[\s-]|$)", stem, re.IGNORECASE):
            return family, stem, ""

    # Unknown conventions get their own precise model, without guessing a family.
    return "其他", stem, ""


def list_svgs():
    scoring = load_data()
    files = [path for path in DIRECTORY.iterdir() if path.is_file() and path.suffix.lower() == ".svg"]
    known_stems = {path.stem.casefold() for path in files}
    numbered_siblings = defaultdict(set)
    for stem in known_stems:
        match = RUN_PATTERN.fullmatch(stem)
        if match and int(match.group(3)) >= 2:
            numbered_siblings[match.group(1).casefold()].add(int(match.group(3)))
    numbered_sibling_bases = {
        base for base, runs in numbered_siblings.items() if len(runs) >= 2
    }
    items = []

    for path in files:
        stem, explicit_run = split_run(path.stem, known_stems, numbered_sibling_bases)
        family, model, setting = classify_stem(stem)
        mtime = path.stat().st_mtime
        items.append(
            {
                "name": path.name,
                "date": datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d"),
                "family": family,
                "model": model,
                "setting": setting,
                "mtime": mtime,
                "score": score_for(path, scoring),
                "_explicit_run": explicit_run,
            }
        )

    groups = defaultdict(list)
    for item in items:
        groups[(item["family"], item["model"], item["setting"])].append(item)

    for group in groups.values():
        used = set()
        for item in sorted(group, key=lambda value: (value["mtime"], value["name"])):
            run = item["_explicit_run"]
            if run is not None and run not in used:
                item["run"] = run
                used.add(run)

        # Alias spellings such as M3 / MiniMax-M3 share one model and still need
        # distinct run labels. Assign only after reserving explicit suffixes.
        for item in sorted(group, key=lambda value: (value["mtime"], value["name"])):
            if "run" not in item:
                run = 1
                while run in used:
                    run += 1
                item["run"] = run
                used.add(run)

    for item in items:
        del item["_explicit_run"]

    return sorted(
        items,
        key=lambda item: (
            item["family"].casefold(),
            item["model"].casefold(),
            item["setting"].casefold(),
            item["run"],
            item["name"].casefold(),
        ),
    )


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        if parsed_path.path in ("/api/svgs", "/api/scoring"):
            try:
                data = list_svgs() if parsed_path.path == "/api/svgs" else {
                    key: value for key, value in load_data().items() if key != "reviews"
                }
            except (ValueError, KeyError, TypeError, OSError) as error:
                self.log_error("评分数据不可用：%s", error)
                self.send_error(503, "Scoring data is unavailable")
                return
            payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        else:
            super().do_GET()

    def end_headers(self):
        path = urllib.parse.urlparse(self.path).path
        if path.endswith(".svg") or path == "/" or path.endswith(".html"):
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()


socketserver.TCPServer.allow_reuse_address = True

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Server started at http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
