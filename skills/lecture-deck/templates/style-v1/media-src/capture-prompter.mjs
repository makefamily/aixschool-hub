// ../script.html(프롬프터) 화면 상단 1600x1000 캡처 → media/prompter.png
import { createRequire } from 'module'; import path from 'path'; import { fileURLToPath } from 'url'; import fs from 'fs';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PW);
const HERE = path.dirname(fileURLToPath(import.meta.url));
const SRC = path.join(HERE, '..', '..', 'script.html');
if (!fs.existsSync(SRC)) { console.log('script.html 없음 — prompter 는 pending 유지'); process.exit(0); }
const b = await chromium.launch({ executablePath: process.env.CHROME, headless: true });
const p = await b.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 2 });
await p.goto('file://' + SRC); await p.waitForTimeout(1200);
// 상단 '강의 시작 전' 준비 메모(발표자 전용)는 화면에 담지 않는다 — 첫 부 제목부터
await p.evaluate(() => { document.documentElement.style.scrollBehavior = 'auto'; const h = document.querySelector('h2'); if (h) window.scrollTo(0, h.getBoundingClientRect().top + scrollY - 170); });
await p.waitForTimeout(400);
await p.screenshot({ path: path.join(HERE, '..', 'media', 'prompter.png') });
await b.close(); console.log('prompter.png ok');
