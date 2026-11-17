// 미디어 조판 HTML → PNG. Node와 Playwright가 설치돼 있어야 한다. 없으면 사용자에게 설치가 필요하다고 알린다.
// node render.mjs [name ...]   (없으면 전부)
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PW || 'playwright');
import path from 'path'; import { fileURLToPath } from 'url';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, '..', 'media');
const CH = process.env.CHROME;
const names = process.argv.slice(2).length ? process.argv.slice(2)
  : ['q1-transcript', 'my-data-folder', 'brain-index', 'design-doc', 'transcript'];
const b = await chromium.launch({ executablePath: CH, headless: true });
const p = await b.newPage({ viewport: { width: 1700, height: 1000 }, deviceScaleFactor: 2 });
for (const n of names) {
  await p.goto('file://' + path.join(HERE, n + '.html'));
  await p.evaluate(() => document.fonts.ready);
  const el = await p.$('#page');
  await el.screenshot({ path: path.join(OUT, n + '.png'), omitBackground: true });
  const bb = await el.boundingBox();
  console.log(n, Math.round(bb.width) + 'x' + Math.round(bb.height));
}
await b.close();
