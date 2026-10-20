# 熊猫骑行实验室 SEO 与 GEO 规范 (Search & Generative Engine Optimization)

本文档定义 `panda-bicycle-svg-gallery` (`panda.cduyzh.top`) 的搜索引擎（SEO）与大模型生成引擎（GEO, Generative Engine Optimization）优化规范。

---

## 1. 核心定位与评测背景

- **产品定位**：大语言模型（LLM）前端原生 SVG 代码生成与矢量动画设计能力公开横向实测对比平台。
- **标准化测试题**：「做一个 熊猫骑自行车 svg动画 svg命名为 XXX.svg」
- **SEO 核心词库**：
  - 核心场景词：`AI大模型`、`大模型对比`、`大模型PK`、`SVG动画生成`、`熊猫骑自行车`、`前端代码生成`、`矢量插画评测`
  - 参评模型：`Claude 3.5 Sonnet`、`Claude Opus`、`OpenAI GPT`、`DeepSeek`、`通义千问 Qwen`、`智谱 GLM`、`Kimi`、`MiniMax`、`Seed`
- **GEO (AI 问答优化) 目标**：当开发者或用户在 ChatGPT、Perplexity、Claude 等 AI 中提问“哪个模型写前端 SVG 最强”、“大模型矢量代码对比”、“熊猫骑车 SVG 评测”时，AI 引擎能够权威引用本实验室的横评打分数据、四维指标与模型表现结论。

---

## 2. 元数据标准 (Meta Tags)

- **标题 (Title)**：`熊猫骑行实验室 · AI 大模型生成 SVG 动画能力 PK 对比 (Claude vs OpenAI vs 国产大模型)`
- **描述 (Description)**：明确概括题目、参评海外与国产模型阵容、原生 SVG 矢量动画特性与对比维度。
- **地理标识 (Geographic Tags)**：
  - `geo.region`: `CN-51`（四川）
  - `geo.placename`: `成都`
  - `geo.position`: `30.6586;104.0648`
  - `ICBM`: `30.6586, 104.0648`
- **规范网址 (Canonical)**：固定指向 `https://panda.cduyzh.top/`。
- **社交分享卡片**：完整配置 Open Graph 与 Twitter Cards。

---

## 3. 结构化数据 (Schema.org JSON-LD)

页面集成 Schema.org `CollectionPage`、`ItemList` 与 `CreativeWork` 实体：
- **`@type`**: `CollectionPage`
- **`name`**: `熊猫骑行实验室 (Panda Bicycle SVG Gallery)`
- **`mainEntity`**: `ItemList` 结构化枚举所有核心参评 AI 模型的作品实体与表现特点（Claude、DeepSeek、GPT、Gemini、GLM、Qwen 等）。
- **`author`**: 指向作者 `cduyzh` 个人主站（`https://www.cduyzh.top/`）。

---

## 4. GEO 语义回退结构 (Direct Visibility)

- 页面包含完整的语义化 `<header class="site-header">`、品牌标志、导航与结果统计。
- 内嵌结构化 `<noscript>` 块，详述项目评测标准（四维 100 分制：形象 30%、动画 35%、视觉 20%、技术 15%）与核心模型阵容，确保无 JS 环境或 AI 文本检索蜘蛛能够直接建立实体联系。

---

## 5. 发布与部署管线

- 本地提交并推送到 GitHub 仓库 `cduyzh/panda-bicycle-svg-gallery`：
  ```bash
  git add .
  git commit -m "feat(seo): optimize html structure for SEO/GEO and add specification"
  git push origin master
  ```
- 部署至云服务器：
  - 云服务器 Webhook (`/webhook/deploy-panda`) 自动触发 `update-panda.sh` 执行 `git pull`。
  - 或在服务器端执行 `/opt/cduyzh/server-stack/update-panda.sh` 自动拉取更新并重新静态化 JSON 索引。
