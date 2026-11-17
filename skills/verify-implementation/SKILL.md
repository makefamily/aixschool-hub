---
name: verify-implementation
description: Consolidated implementation verification workflow. Use after code changes to run tests, targeted checks, and a concise verification report before final closeout.
---

# Verify Implementation

Use this skill after implementation or before a PR-sized closeout.

## Purpose
- run the most relevant available checks
- avoid fake confidence
- produce a compact verification summary

## Workflow
1. Detect available verification surfaces:
   - unit or integration tests
   - lint
   - typecheck
   - build
   - project-specific smoke checks
2. Run the smallest meaningful set that covers the changed area.
3. Record:
   - commands run
   - pass/fail result
   - blockers
4. If something could not be run, say so explicitly.

## Selection Rules
- Prefer targeted tests over full-suite runs when scope is narrow.
- Prefer full build or broader checks when routing, types, or infra changed.
- If the environment blocks a command, report that rather than pretending verification happened.

## Output Format
```markdown
## 구현 검증

- 실행: [command]
- 결과: [PASS / FAIL / NOT RUN]
- 메모: [짧은 설명]
```

## Guardrails
- Verification is evidence, not optimism.
- Keep the report concise and factual.
- Report in Korean.
