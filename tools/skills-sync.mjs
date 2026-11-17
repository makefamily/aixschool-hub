// 허브 스킬·규칙을 이 PC의 허브 전용 폴더에 깐다. 사용자 개인 스킬 폴더는 건드리지 않는다.
// 사용: node tools/skills-sync.mjs [--dry]
import fs from 'node:fs';
import path from 'node:path';
import { REPO, PLATFORM, hubHome, codexHome, workRoot, has, copyDir, args, myRulesFile, ensureMy, myDir } from './lib.mjs';

const a = args();
const manifest = JSON.parse(fs.readFileSync(path.join(REPO, 'skills', 'manifest.json'), 'utf8'));
const haveOrca = has('orca');
const targets = [path.join(codexHome(), 'skills'), path.join(workRoot(), '.claude', 'skills')];

const installed = [], skipped = [];
for (const s of manifest.skills) {
  if (!s.os.includes(PLATFORM)) { skipped.push(`${s.name}(${PLATFORM} 아님)`); continue; }
  if (s.requires.includes('orca') && !haveOrca) { skipped.push(`${s.name}(Orca 없음)`); continue; }
  const src = path.join(REPO, 'skills', s.name);
  if (!fs.existsSync(path.join(src, 'SKILL.md'))) { skipped.push(`${s.name}(SKILL.md 없음)`); continue; }
  if (!a.dry) for (const t of targets) { fs.rmSync(path.join(t, s.name), { recursive: true, force: true }); copyDir(src, path.join(t, s.name)); }
  installed.push(s.name);
}

// 팀 규칙: Codex 허브 폴더의 AGENTS.md, Claude 작업 폴더의 CLAUDE.md
if (!a.dry) {
  fs.mkdirSync(codexHome(), { recursive: true });
  fs.mkdirSync(workRoot(), { recursive: true });
  const rules = fs.readFileSync(path.join(REPO, 'AGENTS.md'), 'utf8');
  const note = `\n\n<!-- AI 학교 허브(${REPO})에서 자동 복사. 여기서 고치지 말 것. -->\n`;
  // 이 PC 사람 전용 규칙(자동 점검에서 '내 전용'으로 고른 것)은 이 PC에만 붙인다.
  const pf = myRulesFile(); ensureMy(); const md = myDir();
  const personal = `\n\n## 내 규칙 파일\n\n이 사람의 규칙은 \`${pf}\`에 있다. 일을 시작할 때 이 파일을 먼저 읽고 따른다.\n사용자가 "앞으로 ~해 줘", "이거 규칙으로 넣어 줘"처럼 계속 지킬 것을 말하면, 그 뜻을 한 줄로 정리해 이 파일의 '## 내 규칙' 아래에 \`- \` 줄로 보태고 무엇을 넣었는지 한 줄로 알린다. 한 번만 필요한 지시는 넣지 않는다.\n\n## 내 자료\n\n이 사람의 자료는 \`${md}\` 폴더에 있다: about.md(나와 내 일), thinking.md(내 생각·원칙), writing/(내가 쓴 글), refs/(닮고 싶은 레퍼런스).\n글·기획·디자인·카드뉴스·영상 대본처럼 이 사람다운 결과가 필요한 일은 시작 전에 이 자료를 먼저 읽고 말투·대상·관점을 맞춘다.\n자료가 비어 있으면 일은 끝까지 하되, 끝에 한 줄로만 알린다(작업마다 한 번): 어떤 자료를 채우면 결과가 더 원하는 대로 나오는지.\n사용자가 \"내 자료 같이 채우자\"라고 하면 질문을 하나씩 던져 답을 about.md·thinking.md 의 빈칸에 적어 준다(사용자 말 그대로, 지어내지 않는다).\n\n## 연결(키)\n\n바깥 서비스에 올리거나 보내는 흐름(스레드 게시, 유튜브 업로드, 노션 등)은 키가 필요하다. 키는 대화·파일에 쓰지 않고 허브 설정 › 연결 화면의 칸에 사용자가 직접 넣는다(각자 PC 금고). 키가 없으면 그 연결 카드의 순서대로 하나씩 안내하고, 공식 문서로 지금 화면을 확인해 함께 따라간다. 스크립트는 \`${path.join(hubHome(), 'hub', 'tools', 'keys.mjs')}\`의 getKey로 키를 꺼내 쓰고 값은 절대 출력하지 않는다.\n\n## 쓸 수 있는 오픈소스\n\n대표가 실제로 써 온 오픈소스 목록이 \`${path.join(hubHome(), 'hub', 'docs', 'open-source.md')}\`에 있다. 일에 맞는 게 있으면 제안하고, 설치는 사용자 확인 후에 한다.\n`;
  // AI 직원표: "블로그 마케터에게 맡겨" 같은 말을 어떤 스킬로 할지 AI가 알게
  let staff = '';
  try {
    const st = JSON.parse(fs.readFileSync(path.join(REPO, 'skills', 'staff.json'), 'utf8')).staff || [];
    staff = `\n\n## AI 직원표\n\n사용자가 직원 이름을 말하거나 그 직원의 일을 맡기면 짝 스킬을 불러 그 절차대로 한다.\n\n| 직원 | 하는 일 | 스킬 | 함께 쓰는 스킬 |\n|---|---|---|---|\n${st.map((x) => `| ${x.name} | ${x.role} | ${x.skill} | ${(x.with || []).join(', ')} |`).join('\n')}\n`;
  } catch {}
  fs.writeFileSync(path.join(codexHome(), 'AGENTS.md'), rules + staff + personal + note);
  fs.writeFileSync(path.join(workRoot(), 'CLAUDE.md'), rules + staff + personal + note);
  // 이 PC 사람 전용 스킬
  const ps = path.join(hubHome(), 'personal-skills');
  if (fs.existsSync(ps)) for (const n of fs.readdirSync(ps)) for (const t of targets) { fs.rmSync(path.join(t, n), { recursive: true, force: true }); copyDir(path.join(ps, n), path.join(t, n)); installed.push(n + '(전용)'); }
}

console.log(`[AI 학교 허브] ${PLATFORM} · 설치 ${installed.length}개 · 건너뜀 ${skipped.length}개`);
if (skipped.length) console.log('  건너뜀: ' + skipped.join(', '));
console.log('  위치: ' + targets.join(' , '));
