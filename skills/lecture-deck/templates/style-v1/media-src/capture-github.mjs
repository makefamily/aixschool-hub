// ReelForge 저장소 페이지 상단 1600x1000 캡처
import { createRequire } from 'module'; import path from 'path'; import { fileURLToPath } from 'url';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PW);
const OUT = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'media', 'reelforge-github.png');
const b = await chromium.launch({ executablePath: process.env.CHROME, headless: true });
const p = await b.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 2, colorScheme: 'light', locale: 'ko-KR' });
const r = await p.goto('https://github.com/gongnyang/reelforge', { waitUntil: 'networkidle', timeout: 45000 });
console.log('status', r.status(), await p.title());
await p.waitForTimeout(1500);
await p.screenshot({ path: OUT, clip: { x: 0, y: 0, width: 1600, height: 1000 } });
await b.close();
