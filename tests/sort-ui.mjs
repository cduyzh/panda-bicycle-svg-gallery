import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { fileURLToPath } from 'node:url';
import { withManagedBrowser } from '/Users/hobby/.codex/tools/browser-qa/runtime.mjs';

const root = fileURLToPath(new URL('../', import.meta.url));
const output = new URL('../work/sort-ui/', import.meta.url);
await mkdir(output, { recursive: true });
const child = spawn('python3', ['-u', '-c',
  'import server,socketserver; s=socketserver.TCPServer(("127.0.0.1",0),server.Handler); print(s.server_address[1],flush=True); s.serve_forever()'],
  { cwd: root, stdio: ['ignore', 'pipe', 'ignore'] });
let stopping = false;
async function stop() {
  if (stopping) return;
  stopping = true;
  if (child.exitCode === null && child.signalCode === null) {
    child.kill('SIGTERM');
    await Promise.race([once(child, 'exit'), new Promise(resolve => setTimeout(resolve, 3000))]);
    if (child.exitCode === null && child.signalCode === null) child.kill('SIGKILL');
  }
}
for (const signal of ['SIGINT', 'SIGTERM', 'SIGHUP']) process.once(signal, () => { void stop(); });

try {
  const port = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('测试服务启动超时')), 10000);
    child.stdout.once('data', chunk => { clearTimeout(timer); resolve(Number(chunk.toString().trim())); });
    child.once('error', error => { clearTimeout(timer); reject(error); });
    child.once('exit', code => { clearTimeout(timer); reject(new Error(`服务提前退出 ${code}`)); });
  });
  await withManagedBrowser(async ({ context }) => {
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto(`http://127.0.0.1:${port}`, { waitUntil: 'load' });
    await page.waitForFunction(() => document.querySelectorAll('.model-card').length > 0);
    assert.equal(await page.locator('select').count(), 0, '排序不得使用原生 select');
    assert.equal(await page.locator('.control-row > :first-child').getAttribute('id'), 'sort-wrap');
    const position = async () => {
      const sort = await page.locator('#sort').boundingBox(), search = await page.locator('.search-field').boundingBox();
      assert.ok(sort.x + sort.width <= search.x, '排序必须位于搜索栏左侧');
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    };
    await position();
    const response = await page.request.get(`http://127.0.0.1:${port}/api/svgs`);
    const items = await response.json();
    const map = new Map();
    for (const item of items) {
      const key = `${item.family}|${item.model}`;
      if (!map.has(key)) map.set(key, { model: item.model, items: [] });
      map.get(key).items.push(item);
    }
    const individualCards = await page.locator('.model-card').count() === items.length;
    const groups = individualCards
      ? items.map(item => ({ model: item.name.replace(/\.svg$/i, ''), items: [item], latest: item }))
      : [...map.values()].map(group => ({ ...group,
        latest: [...group.items].sort((a, b) => b.mtime - a.mtime || b.run - a.run || a.name.localeCompare(b.name, 'zh-CN'))[0] }));
    const comparators = {
      recent: (a, b) => b.latest.mtime - a.latest.mtime || a.model.localeCompare(b.model, 'zh-CN'),
      name: (a, b) => a.model.localeCompare(b.model, 'zh-CN'),
      works: (a, b) => b.items.length - a.items.length || b.latest.mtime - a.latest.mtime,
      score: (a, b) => (b.latest.score.total ?? -1) - (a.latest.score.total ?? -1) || a.model.localeCompare(b.model, 'zh-CN'),
    };
    const labels = { recent: '最近更新', name: '模型名称', works: '作品数量', score: '最新作品评分' };
    async function verifyOrder(value) {
      assert.equal(await page.locator('#sort-label').textContent(), labels[value]);
      assert.deepEqual(await page.locator('.model-card .card-name').allTextContents(), [...groups].sort(comparators[value]).map(group => group.model));
      assert.equal(await page.locator('#sort').getAttribute('aria-expanded'), 'false');
      assert.equal(await page.evaluate(() => document.activeElement?.id), 'sort');
    }
    await page.locator('#sort').click();
    assert.equal(await page.getByRole('option').count(), 4);
    assert.equal(await page.getByRole('option', { selected: true }).getAttribute('aria-label'), '最近更新');
    assert.equal(await page.locator('#sort-options').evaluate(menu => getComputedStyle(menu).backgroundColor), 'rgb(255, 255, 255)');
    await page.locator('.browser-controls').screenshot({ path: fileURLToPath(new URL('desktop.png', output)), animations: 'disabled' });
    await page.screenshot({ path: fileURLToPath(new URL('desktop-menu.png', output)), animations: 'disabled' });
    for (const [value, label] of Object.entries(labels)) {
      if (await page.locator('#sort-options').isHidden()) await page.locator('#sort').click();
      await page.getByRole('option', { name: label, exact: true }).click();
      await verifyOrder(value);
    }
    await page.locator('#sort').focus();
    await page.keyboard.press('ArrowDown');
    assert.equal(await page.evaluate(() => document.activeElement?.id), 'sort-options');
    await page.keyboard.press('Home');
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('Enter');
    await verifyOrder('name');
    await page.keyboard.press('Space');
    await page.keyboard.press('End');
    await page.keyboard.press('Space');
    await verifyOrder('score');
    await page.keyboard.press('Enter');
    await page.keyboard.press('Home');
    await page.keyboard.press('Escape');
    await verifyOrder('score');
    await page.keyboard.press('ArrowUp');
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement?.id), 'search');
    assert.equal(await page.locator('#sort-options').isHidden(), true);
    await page.locator('#sort').click();
    await page.locator('#search').click();
    assert.equal(await page.locator('#sort-options').isHidden(), true);

    for (const width of [390, 320]) {
      await page.setViewportSize({ width, height: 844 });
      await page.locator('#sort').scrollIntoViewIfNeeded();
      await position();
      await page.locator('#sort').click();
      const menu = await page.locator('#sort-options').boundingBox();
      assert.ok(menu.x >= 0 && menu.x + menu.width <= width && menu.y >= 0 && menu.y + menu.height <= 844, '窄屏菜单必须完整落在屏幕内');
      await page.screenshot({ path: fileURLToPath(new URL(`mobile-${width}.png`, output)), animations: 'disabled' });
      assert.equal(await page.locator('#sort-options').evaluate(menu => {
        const box = menu.getBoundingClientRect();
        return menu.contains(document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2));
      }), true, '菜单不得被作品卡片遮挡');
      await page.getByRole('option', { name: '最近更新', exact: true }).click();
      await verifyOrder('recent');
    }
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.locator('#sort').click();
    assert.equal(await page.locator('#sort-options').evaluate(menu => getComputedStyle(menu).animationName), 'none');
    await page.keyboard.press('Escape');
    assert.deepEqual(errors, []);
    console.log('PASS: 最左侧、自定义选项面板、四种实际排序、选中态、方向键/Home/End/Enter/Space/Escape/Tab、外部点击、390/320 窄屏与 reduced-motion；同一浏览器完成');
  }, { timeoutMs: 90000 });
} finally {
  await stop();
}
