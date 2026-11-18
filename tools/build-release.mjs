// 설치 묶음 만들기(맥에서 실행). 맥·윈도우 묶음 폴더와 zip을 release/ 에 만든다.
// 사용: node tools/build-release.mjs [mac] [windows]
//   mac     : desktop/src-tauri/target/release/bundle/macos/AI 학교 허브.app 이 있어야 한다
//   windows : build/windows-app/ 에 setup.exe 가 있어야 한다(likim 빌드 또는 Actions 산출물)
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { REPO } from './lib.mjs';

// 태그로 만들 때는 태그와 VERSION 파일이 같아야 한다(다르면 업데이트 확인이 엉킨다)
const VERSION = fs.readFileSync(path.join(REPO, 'VERSION'), 'utf8').trim();
if (process.env.GITHUB_REF_NAME?.startsWith('v') && process.env.GITHUB_REF_NAME !== `v${VERSION}`) throw new Error(`태그 ${process.env.GITHUB_REF_NAME} 와 VERSION ${VERSION} 이 달라요`);
const want = process.argv.slice(2).length ? process.argv.slice(2) : ['mac', 'windows'];
const OUT = path.join(REPO, 'release');
const HUB_FILES = ['AGENTS.md', 'CLAUDE.md', 'README.md', 'app', 'skills', 'tools/lib.mjs', 'tools/setup.mjs', 'tools/skills-sync.mjs', 'tools/skill-register.mjs', 'tools/keys.mjs', 'tools/update.mjs', 'VERSION', 'docs/open-source.md'];
const skip = (s) => /[\\/](__pycache__|node_modules|\.git)([\\/]|$)|\.DS_Store$|\.bak/.test(s);

function stageHub(dst) {
  for (const f of HUB_FILES) {
    const s = path.join(REPO, f), d = path.join(dst, f);
    if (!fs.existsSync(s)) { console.log(`  주의: ${f} 없음(건너뜀)`); continue; }
    fs.mkdirSync(path.dirname(d), { recursive: true });
    fs.cpSync(s, d, { recursive: true, filter: (x) => !skip(x) });
  }
}
// 개인정보 검사기(build/scan_private.py)는 공개 저장소에 없다. 있을 때만 돌린다.
function scan(dir) {
  const sp = path.join(REPO, 'build', 'scan_private.py');
  if (!fs.existsSync(sp)) return { n: 0, out: '', skipped: true };
  const r = spawnSync('python3', [path.join(REPO, 'build', 'scan_private.py'), dir], { encoding: 'utf8' });
  const m = (r.stdout || '').match(/걸린 것: (\d+)건/);
  return { n: m ? Number(m[1]) : -1, out: (r.stdout || '') + (r.stderr || '') };
}
// 맥 묶음은 앱 권한을 지키려고 ditto, 윈도우 묶음은 __MACOSX 없는 일반 zip
function zip(srcDir, zipFile, os) {
  fs.rmSync(zipFile, { force: true });
  const r = os === 'mac'
    ? spawnSync('ditto', ['-c', '-k', '--norsrc', '--keepParent', srcDir, zipFile], { encoding: 'utf8' })
    // 윈도우: 한글 파일 이름을 NFC로 바꾸고 UTF-8 표시를 켠 zip(윈도우 압축 풀기가 읽을 수 있게)
    : spawnSync('python3', ['-c', `import os,sys,zipfile,unicodedata
src,out=sys.argv[1],sys.argv[2]
base=os.path.dirname(src)
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
    for root,ds,fs in os.walk(src):
        for f in fs:
            if f=='.DS_Store': continue
            full=os.path.join(root,f)
            z.write(full, unicodedata.normalize('NFC', os.path.relpath(full,base)))
`, srcDir, zipFile], { encoding: 'utf8' });
  if (r.status !== 0) throw new Error(r.stderr);
}

for (const os of want) {
  const root = path.join(OUT, os, 'AISchoolHub-install');
  fs.rmSync(path.join(OUT, os), { recursive: true, force: true });
  fs.mkdirSync(root, { recursive: true });
  stageHub(path.join(root, 'hub'));
  if (os === 'mac') {
    const app = path.join(REPO, 'desktop', 'src-tauri', 'target', 'release', 'bundle', 'macos', 'AI 학교 허브.app');
    if (!fs.existsSync(app)) throw new Error('맥 앱이 없어요. desktop/src-tauri 에서 tauri build --bundles app 먼저');
    spawnSync('ditto', [app, path.join(root, 'AI 학교 허브.app')]);
    fs.copyFileSync(path.join(REPO, 'install', 'mac', 'install-mac.command'), path.join(root, 'install-mac.command'));
    fs.chmodSync(path.join(root, 'install-mac.command'), 0o755);
  } else {
    const wa = path.join(OUT, '..', 'build', 'windows-app');
    const exe = fs.existsSync(wa) ? fs.readdirSync(wa).find((f) => /setup.*\.exe$/i.test(f)) : null;
    if (!exe) console.log('  주의: build/windows-app 에 setup.exe 가 없어 앱 없이 묶어요');
    else fs.copyFileSync(path.join(wa, exe), path.join(root, exe));
    for (const f of ['install-windows.ps1', 'install-windows.cmd']) {
      let t = fs.readFileSync(path.join(REPO, 'install', 'windows', f), 'utf8').replace(/^﻿/, '');
      t = t.replace(/\r?\n/g, '\r\n');
      // PowerShell 5는 BOM 없는 UTF-8 한글을 깨뜨리므로 .ps1 은 BOM을 붙인다
      fs.writeFileSync(path.join(root, f), (f.endsWith('.ps1') ? '﻿' : '') + t, 'utf8');
    }
  }
  const sc = scan(path.join(root, 'hub'));
  console.log(sc.skipped ? `[${os}] 개인정보 검사기 없음(건너뜀)` : `[${os}] 개인정보 검사 ${sc.n}건`);
  if (sc.n !== 0) { console.log(sc.out.split('\n').slice(-30).join('\n')); process.exitCode = 1; continue; }
  const z = path.join(OUT, `AISchoolHub-${os}.zip`);
  zip(root, z, os);
  console.log(`[${os}] ${z} · ${(fs.statSync(z).size / 1048576).toFixed(1)}MB`);
}
