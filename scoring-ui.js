/* 与画廊共用 state 与 DOM 工具；评分规则全部读取自 /api/scoring。 */
function renderScoreCoverage() {
  const scored = state.items.filter((item) => item.score?.status === "scored").length;
  const imported = state.items.filter((item) => item.score?.status === "scored" && item.score.source === "spreadsheet").length;
  const stale = state.items.filter((item) => item.score?.status === "stale").length;
  $("score-coverage").textContent = `${scored} / ${state.items.length} 份已评分 · 原表 ${imported} 份 · 补评 ${scored - imported} 份${state.items.length > scored ? ` · 待评分 ${state.items.length - scored - stale} 份 · 待复评 ${stale} 份` : ""}。卡片分数对应最新作品，详情可逐份查看。`;
}

function renderRubric() {
  const rubric = state.rubric;
  if (!rubric) return;
  $("weight-grid").replaceChildren(...rubric.dimensions.map((dimension) => {
    const box = node("div", "weight-item");
    box.append(node("span", "", `${dimension.code} · ${dimension.label}`), node("strong", "", `${dimension.max}%`));
    return box;
  }));
  const content = $("rubric-content");
  content.replaceChildren();
  content.appendChild(node("p", "scoring-note", `100 分制 · 规则 v${rubric.rubricVersion} · 数据更新 ${rubric.updatedAt}`));
  const wrap = node("div", "rubric-table-wrap");
  const table = node("table", "rubric-table");
  const head = node("thead"), row = node("tr");
  for (const label of ["评分小项", "满分", "评判标准"]) {
    const th = node("th", "", label); th.scope = "col"; row.appendChild(th);
  }
  head.appendChild(row); table.appendChild(head);
  const body = node("tbody");
  for (const item of rubric.criteria) {
    const tr = node("tr");
    tr.append(node("td", "", `${item.code} ${item.label}`), node("td", "", `${item.max} 分`), node("td", "", item.standard));
    body.appendChild(tr);
  }
  table.appendChild(body); wrap.appendChild(table); content.appendChild(wrap);
  const levels = node("div", "level-list");
  rubric.levels.forEach((level, index) => {
    const ceiling = index === 0 ? 100 : rubric.levels[index - 1].min;
    const range = index === 0 ? `${level.min}–${ceiling}` : `${level.min} 至不足 ${ceiling}`;
    const label = node("span", "", `${range} 分 · ${level.label}`);
    label.title = level.meaning; levels.appendChild(label);
  });
  content.appendChild(levels);
  for (const [title, lines] of [["计算与评审流程", rubric.methodology], ["评分范围与局限", rubric.limitations]]) {
    content.appendChild(node("h3", "", title));
    const list = node("ul", "rubric-list");
    lines.forEach((line) => list.appendChild(node("li", "", line)));
    content.appendChild(list);
  }
}

function scoreBlock(item, detailed = false) {
  const score = item.score;
  const block = node("div", `score-block${detailed ? " detail-score" : ""}`);
  const top = node("div", "score-top");
  top.appendChild(node("span", "score-label", detailed ? "本作品评分" : "最新作品评分"));
  if (score?.status !== "scored") {
    top.appendChild(node("span", "score-level score-pending", score?.status === "stale" ? "待复评" : "待评分"));
    block.append(top, node("p", "score-comment", score?.comment || "等待按公开标准评审。"));
    return block;
  }
  const number = node("span", "score-number", score.total);
  number.appendChild(node("small", "", " / 100"));
  top.append(number, node("span", "score-level", score.level));
  block.append(top, node("p", "score-comment", score.comment));
  if (detailed && state.rubric) {
    const dimensions = node("div", "score-dimensions");
    for (const dimension of state.rubric.dimensions) {
      const item = node("div", "score-dimension", dimension.label);
      const value = score.dimensions[dimension.code];
      item.appendChild(node("strong", "", `${value} / ${dimension.max}`));
      const track = node("div", "score-track"), fill = node("span", "score-fill");
      fill.style.width = `${value / dimension.max * 100}%`;
      track.appendChild(fill); item.appendChild(track); dimensions.appendChild(item);
    }
    block.appendChild(dimensions);
    const details = node("details", "score-details");
    details.appendChild(node("summary", "", "查看小项得分与评分依据"));
    for (const criterion of state.rubric.criteria) {
      const row = node("div", "score-item");
      row.append(node("span", "", `${criterion.code} ${criterion.label}`), node("strong", "", `${score.scores[criterion.code]} / ${criterion.max}`));
      details.appendChild(row);
    }
    const notes = node("div", "score-notes");
    for (const dimension of state.rubric.dimensions) {
      if (score.notes[dimension.code]) notes.appendChild(node("p", "", `${dimension.label}：${score.notes[dimension.code]}`));
    }
    if (score.evidence?.sampleTimesMs) notes.appendChild(node("p", "score-source", `动画取样：${score.evidence.sampleTimesMs.map((time) => `${time / 1000}s`).join("、")}。`));
    if (score.source === "spreadsheet") notes.appendChild(node("p", "score-source", "评分依据及点评沿用原评分表；原表检查了 0–2 秒的 12 帧。"));
    details.appendChild(notes); block.appendChild(details);
    const link = node("a", "score-source", "查看完整评分制度 ↗"); link.href = "#scoring-rules";
    link.addEventListener("click", closeDetail); block.appendChild(link);
  }
  block.appendChild(node("p", "score-source", score.source === "spreadsheet" ? `原表评分 · 导入 ${score.reviewedAt}` : `${score.reviewer} 补评 · ${score.reviewedAt}`));
  return block;
}
