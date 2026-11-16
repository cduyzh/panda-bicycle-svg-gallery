#!/bin/bash
set -e

echo "=> 1. 检查是否有待评分的新作品..."
if python3 scoring.py audit >/dev/null 2>&1; then
  echo "当前没有发现需要打分的新 SVG 文件。"
  exit 0
fi

WORK_DIR="work/auto-scoring-$(date +%s)"
echo "=> 2. 生成打分计划到 $WORK_DIR ..."
python3 scoring.py prepare --out "$WORK_DIR"

echo "=> 3. 抓取 SVG 各时间点画面..."
node /Users/hobby/.codex/tools/browser-qa/capture.mjs "$WORK_DIR/capture-plan.json"

echo "=> 4. 召唤大模型进行视觉评审与打分..."
# 使用 Antigravity CLI (agy) 让大模型作为阅卷人，补充完 review.json
agy --prompt "请读取 $WORK_DIR/review.json 和 $WORK_DIR/frames/ 下的截图以及对应 SVG 源码，严格依据 scoring.json (v1.2) 的 13 项量化锚点与 README 规范，直接在 $WORK_DIR/review.json 里补充所有 null 项。必须结合源码检查车轮/曲柄旋转方向（严禁仅凭离散帧辐条频闪误判倒转）、牙盘存在性、轮地速度比、use 复用数与 title/desc 完整性，填写 13 项评分、一句话点评 (comment)、四维实质性评分依据 (notes，每项不少于8字，严禁填入占位语)、评审人 (reviewer)。完成后覆写 $WORK_DIR/review.json 并退出。"

echo "=> 5. 应用分数并自校验..."
python3 scoring.py apply "$WORK_DIR/review.json"
python3 scoring.py audit
python3 -m unittest discover -s tests

echo "=> 6. 自动化流程已完成，新评分已生效到本地网页并同步远程。"
git add .
git commit -m "feat: Auto update svg scores"
git push
