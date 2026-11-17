---
name: red-team
description: Adversarial review workflow for implementation outputs. Use after meaningful code changes to find bugs, regressions, blind spots, security issues, and operational risks before closeout.
---

# Red Team

Use this skill after non-trivial implementation, especially for L2 and L3 work.

## Review Lenses
- assumptions and hidden coupling
- missing requirements or incomplete flows
- failure modes and edge cases
- consistency with project rules and prior decisions
- code-level risk in concurrency, data integrity, auth, secrets, and error handling

## Severity
- `CRITICAL`: release-blocking, security-impacting, or data-loss risk
- `IMPORTANT`: likely defect, regression, or strong quality concern
- `MINOR`: useful improvement that is not blocking

## Workflow
1. Review the implementation artifact, changed files, and any verification output.
2. Produce findings first, ordered by severity.
3. For each finding, include the concrete fix direction.
4. If no findings exist, state that explicitly and mention residual risk or test gaps.

## Minimum Coverage
Check:
- unhappy paths
- input validation
- state consistency
- deployment/config assumptions
- test coverage gaps

## Output Format
```markdown
## Red Team Review

판정: [PASS / PASS WITH CONDITIONS / REVISE / BLOCK]

### Findings
1. [severity] [file or area] - [issue] - [fix direction]
```

## Guardrails
- Do not praise by default.
- Findings are the primary output.
- Report in Korean.
