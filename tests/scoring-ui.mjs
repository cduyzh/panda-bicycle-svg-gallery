import assert from 'node:assert/strict';
import { readFile, mkdir } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { fileURLToPath } from 'node:url';
import { withManagedBrowser } from '/Users/hobby/.codex/tools/browser-qa/runtime.mjs';

const root = fileURLToPath(new URL('../', import.meta.url));
const data = JSON.parse(await readFile(new URL('../scoring.json', import.meta.url), 'utf8'));
const expectedCount = Object.keys(data.reviews).length;
const importedCount = Object.values(data.reviews).filter(review => review.source === 'spreadsheet').length;
const output = new URL('../work/scoring-ui/', import.meta.url);
await mkdir(output, { recursive: true });
// 测试服务占用系统分配的临时端口，不影响用户正在运行的 8000 服务。
const child = spawn('python3', ['-u', '-c',
  'import server,socketserver; s=socketserver.TCPServer(("127.0.0.1",0),server.Handler); print(s.server_address[1],flush=True); s.serve_forever()'],
  { cwd: root, stdio: ['ignore', 'pipe', 'ignore'] });
let stopping = false;
async function stop() {
  if (stopping) return;
  stopping = true;
  if (child.exitCode === null && child.signalCode === null) {
    child.kill('SIGTERM');
    await Promise.race([once(child, 'exit'), new Promise((resolve) => setTimeout(resolve, 3000))]);
    if (child.exitCode === null && child.signalCode === null) child.kill('SIGKILL');
  }
}
for (const signal of ['SIGINT', 'SIGTERM', 'SIGHUP']) process.once(signal, () => { void stop(); });

try {
  const port = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('测试服务启动超时')), 10000);
    child.stdout.once('data', (chunk) => { clearTimeout(timer); resolve(Number(chunk.toString().trim())); });
    child.once('error', (error) => { clearTimeout(timer); reject(error); });
    child.once('exit', (code) => { clearTimeout(timer); reject(new Error(`服务提前退出 ${code}`)); });
  });
  await withManagedBrowser(async ({ context, signal }) => {
    const page = await context.newPage();
    page.setDefaultTimeout(10000);
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await context.route('https://umami.cduyzh.top/**', (route) => route.abort());
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto(`http://127.0.0.1:${port}`, { waitUntil: 'load' });
    await page.waitForFunction(count => document.querySelector('#stat-works')?.textContent === String(count), expectedCount);
    const response = await page.request.get(`http://127.0.0.1:${port}/api/svgs`);
    const items = await response.json();
    assert.equal(items.length, expectedCount);
    assert.equal(await page.locator('.model-card .score-number').count(), await page.locator('.model-card').count());
    const coverage = await page.locator('#score-coverage').textContent();
    assert.ok(coverage.includes(`${expectedCount} / ${expectedCount}`));
    assert.ok(coverage.includes(`原表 ${importedCount} 份`));
    assert.ok(coverage.includes(`补评 ${expectedCount - importedCount} 份`));
    assert.deepEqual(await page.locator('.weight-item strong').allTextContents(), ['30%', '35%', '20%', '15%']);
    await page.locator('.rubric-details summary').click();
    assert.equal(await page.locator('.rubric-table tbody tr').count(), 13);
    assert.match(await page.locator('#rubric-content').textContent(), /不再重复乘权重/);
    await page.locator('#scoring-rules').screenshot({ path: fileURLToPath(new URL('rules.png', output)) });
    await page.locator('.rubric-details summary').click();
    await page.locator('#sort').click();
    await page.getByRole('option', { name: '最新作品评分', exact: true }).click();
    const scores = await page.locator('.model-card .score-number').allTextContents();
    const numbers = scores.map((value) => Number(value.split('/')[0]));
    assert.deepEqual(numbers, [...numbers].sort((a, b) => b - a));
    await page.locator('#works').screenshot({ path: fileURLToPath(new URL('gallery.png', output)) });

    const groups = new Map();
    for (const item of items) {
      const key = `${item.family}|${item.model}`;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(item);
    }
    for (const entries of groups.values()) {
      signal.throwIfAborted();
      await page.getByRole('button', { name: `查看 ${entries[0].model} 的 ${entries.length} 份作品`, exact: true }).click();
      for (const entry of entries) {
        await page.getByRole('button', { name: `预览 ${entry.name}`, exact: true }).click();
        const review = data.reviews[entry.name];
        const expected = Object.values(review.scores).reduce((sum, score) => sum + score, 0);
        assert.equal(await page.locator('#preview-filename').textContent(), entry.name);
        assert.equal((await page.locator('#detail-score .score-number').textContent()).trim(), `${expected} / 100`);
        assert.equal(await page.locator('#detail-score .score-comment').textContent(), review.comment);
        await page.locator('#detail-score summary').click();
        assert.equal(await page.locator('#detail-score .score-item').count(), 13);
        const dimensionValues = await page.locator('#detail-score .score-dimension strong').allTextContents();
        assert.equal(dimensionValues.reduce((sum, value) => sum + Number(value.split('/')[0]), 0), expected);
      }
      await page.keyboard.press('Escape');
    }
    await page.locator('#search').fill('Max2');
    assert.equal(await page.locator('.model-card').count(), 1);
    await page.locator('#search-clear').click();
    await page.getByRole('button', { name: /^DeepSeek/ }).first().click();
    assert.equal(await page.locator('.model-card').count(), 4);
    await page.getByRole('button', { name: /^全部模型/ }).click();

    await page.setViewportSize({ width: 390, height: 844 });
    await page.locator('#scoring-rules').screenshot({ path: fileURLToPath(new URL('mobile.png', output)) });
    await page.locator('.rubric-details summary').click();
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    await page.locator('.rubric-details summary').click();
    await page.getByRole('button', { name: '查看 DeepSeek V4 Pro 的 4 份作品', exact: true }).click();
    await page.getByRole('button', { name: '预览 DeepSeek V4 Pro Ultra 2.svg', exact: true }).click();
    await page.locator('#detail-score').scrollIntoViewIfNeeded();
    await page.screenshot({ path: fileURLToPath(new URL('mobile-detail.png', output)) });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    await page.locator('#detail-score summary').click();
    await page.getByRole('link', { name: '查看完整评分制度 ↗' }).click();
    assert.equal(await page.locator('#detail').isVisible(), false);
    assert.deepEqual(errors, []);

    // 只模拟接口状态，不创建或改写真实作品。在同一浏览器中验证后续收录流程。
    let fixture = { ...items[0], name: '本轮新增评分测试.svg', model: '本轮新增评分测试', family: '其他',
      mtime: Date.now() / 1000, score: { status: 'pending', comment: '等待按公开标准评审。' } };
    await page.route('**/api/svgs', route => route.fulfill({ contentType: 'application/json', body: JSON.stringify([...items, fixture]) }));
    await page.evaluate(() => fetchSvgs());
    const pendingCard = page.locator('.model-card').filter({ hasText: fixture.model });
    assert.match(await pendingCard.textContent(), /待评分/);
    assert.equal(await pendingCard.locator('.score-number').count(), 0);
    await pendingCard.locator('button').click();
    assert.match(await page.locator('#detail-score').textContent(), /待评分/);
    assert.equal(await page.locator('#detail-score .score-dimensions').count(), 0);
    await page.keyboard.press('Escape');
    fixture.score = { status: 'stale', comment: '作品已更新，等待重新评审。' };
    await page.waitForFunction(() => [...document.querySelectorAll('.model-card')].some(card =>
      card.textContent.includes('本轮新增评分测试') && card.textContent.includes('待复评')), {}, { timeout: 20000 });
    assert.equal(await pendingCard.locator('.score-number').count(), 0);
    fixture.score = { ...items[0].score, total: 0, level: '有明显缺陷', comment: '真实的零分作品。',
      scores: Object.fromEntries(Object.keys(items[0].score.scores).map(code => [code, 0])), dimensions: { A: 0, B: 0, C: 0, D: 0 } };
    await page.evaluate(() => fetchSvgs());
    assert.equal((await pendingCard.locator('.score-number').textContent()).trim(), '0 / 100');
    await pendingCard.locator('button').click();
    assert.equal((await page.locator('#detail-score .score-number').textContent()).trim(), '0 / 100');
    assert.equal(await page.locator('#detail-score .score-dimension').count(), 4);
    assert.deepEqual(errors, []);
    console.log(`PASS: ${items.length} 份作品逐一核对分数和点评，四维合计、13 小项、来源、排序、搜索、筛选及窄屏评分交互`);
    console.log('PASS: 待评分、待复评、真实 15 秒自动刷新及零分区分');
  }, { timeoutMs: 180000 });
} finally {
  await stop();
}
