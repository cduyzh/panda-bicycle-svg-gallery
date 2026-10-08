# SVG 画廊校验

- 保留用户指定的 SVG 文件名和已有作品。XML/静态截图通过不能写成动画或真实交互验收通过。
- 需要批量检查 SVG 动画时，通过 `node /Users/hobby/.codex/tools/browser-qa/capture.mjs <plan.json>` 统一截图；计划与临时图片放在 `work/`。相同 SVG 的多个 `timeMs` 必须在同一个浏览器、页面内完成。
- 禁止用 shell/Python 循环为每个时间点启动 `/Applications/Google Chrome.app`。主任务和子 agent 共享同一轮截图结果，避免重复渲染。
- 页面交互测试可在项目自己的脚本中使用 `/Users/hobby/.codex/tools/browser-qa/runtime.mjs` 的 `withManagedBrowser()`；操作已打开的用户浏览器仍使用当前环境规定的工具。

# SVG 评分与持续更新

- 新增、替换或修改 SVG 时，同一任务中必须完成评分更新。保留原始文件名与作品；不沿用其他文件或模型的分数。
- 先运行 `python3 scoring.py audit`，确认待评分与待复评清单。评分规则、档位与四维权重统一读取 `scoring.json`，不要在页面或脚本另写一套。
- 按 README 的「新增或修改 SVG 的评分流程」准备评审、批量截图、查看动作时间点并复核源码，再填完整 13 小项、四维依据和一句话点评，通过 `scoring.py apply` 更新数据。
- 新评分标记 `supplemental` 与实际评审人。原表评分标记 `spreadsheet`，保留 `sourceRef`、原小项及原点评；不要未经复评改动原表分数。
- 总分和档位由小项计算。满分 100，四维为形象 30 / 动画 35 / 视觉 20 / 技术 15；不得再乘一次权重。
- 不按文件体积、模型名、动画元素数或帧间像素差自动给审美分。静态截图及离散取样不等于连续播放、循环全覆盖、跨浏览器或真机性能验收。
- 文件 SHA-256 或规则版本不匹配时显示待复评；评分未完成时显示待评分，不伪造 0 分或继承旧分。调整正式规则时升级 `rubricVersion` 并复评受影响作品。
- 评分更新后运行 `python3 scoring.py audit` 与 `python3 -m unittest discover -s tests`。页面评分交互验收复用本轮受管浏览器，并按实际新增或变动范围检查。
