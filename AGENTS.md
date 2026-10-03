# SVG 画廊校验

- 保留用户指定的 SVG 文件名和已有作品。XML/静态截图通过不能写成动画或真实交互验收通过。
- 需要批量检查 SVG 动画时，通过 `node /Users/hobby/.codex/tools/browser-qa/capture.mjs <plan.json>` 统一截图；计划与临时图片放在 `work/`。相同 SVG 的多个 `timeMs` 必须在同一个浏览器、页面内完成。
- 禁止用 shell/Python 循环为每个时间点启动 `/Applications/Google Chrome.app`。主任务和子 agent 共享同一轮截图结果，避免重复渲染。
- 页面交互测试可在项目自己的脚本中使用 `/Users/hobby/.codex/tools/browser-qa/runtime.mjs` 的 `withManagedBrowser()`；操作已打开的用户浏览器仍使用当前环境规定的工具。
