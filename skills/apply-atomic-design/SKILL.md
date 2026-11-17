---
name: apply-atomic-design
description: Apply Brad Frost's Atomic Design principles as a practical, non-linear UI/UX system workflow for product screens, flows, component libraries, UI reviews, redesigns, and frontend implementation. Use whenever designing, critiquing, refactoring, or implementing product UI—including landing pages, onboarding, paywalls, pricing, checkout, dashboards, settings, responsive states, design systems, and reusable components—and when deciding whether a UI change belongs at the element, component, section, template, or page/scenario level.
---

# Apply Atomic Design

Treat every product interface as both a user-facing whole and a reusable system of parts. Apply the method proportionally: keep a tiny change lightweight, but never let a screen-level shortcut silently damage the system.

## Load the guidance

- Read [references/application-checklist.md](references/application-checklist.md) for every triggered task. Use only the sections relevant to the task size.
- Also read [references/atomic-design-source-notes.md](references/atomic-design-source-notes.md) before a new product, redesign, design-system or governance decision, or whenever the rationale behind a rule matters.
- Read [references/ui-reference-playbook.md](references/ui-reference-playbook.md) for customer-facing landing pages, product demos, new visual directions, or explicit reference-driven redesigns. Skip it for mechanical UI fixes unless choosing a reference is part of the task.
- When current tools, browser behavior, accessibility standards, or platform conventions matter, verify them from current primary sources. The book's named tools are examples from 2016, not mandatory technology choices.

## Execute the system workflow

1. **Set the UI scope.** Identify the user task, business goal, platforms, target environments, content types, constraints, and success criteria. Scope effort by behaviors, components, content structures, and variants—not by page count alone.
2. **Collect evidence and inspect the existing system.** Follow any applicable evidence-first UI research rule, including Lazyweb when available or required. Inspect current screens, components, tokens, code, and documentation before proposing new patterns. For an existing product, perform a proportional interface inventory; for greenfield work, inventory the core flows and expected recurring patterns. If brand or system evidence is unavailable, state the gap and label any neutral foundations as provisional rather than inventing final visual decisions.
3. **Model parts and whole concurrently.** Map the interface into foundations/properties, atoms, molecules, organisms, templates, and pages/scenarios. Use the team's native taxonomy if it communicates better. Do not execute these levels as a linear assembly line; move in both directions as the page context exposes component needs.
4. **Design structure with content.** Separate reusable structure from data while designing them together. Use representative content and include meaningful extremes: long and short copy, missing media, empty, loading, error, success, permission, role, localization, density, and large-list cases as applicable.
5. **Establish direction before polish.** Resolve content hierarchy and broad visual direction with low-cost artifacts before investing in full-fidelity screens. Get the design into its real interactive environment early enough to test behavior, responsiveness, accessibility, performance, and content variability.
6. **Reuse, document, and trace.** Reuse an existing pattern when it satisfies the need. When adding or changing a pattern, specify purpose, anatomy, variants, states, content constraints, accessibility behavior, responsive behavior, dependencies, and where it is used. Keep component examples and implementation as close to one source of truth as the project's architecture reasonably permits.
7. **Verify at two zoom levels.** Test the isolated part and every representative whole that consumes it. Check the complete state/variant matrix, the resolution spectrum, keyboard and assistive-technology behavior, input types, performance, and real content. Revisit lower-level patterns when page scenarios fail.
8. **Govern material changes.** For reusable additions or breaking changes, identify owner, approval path, rollout, documentation, migration/deprecation, release communication, and affected consumers. Treat the design system as an evolving product, not a one-time deliverable.

## Scale the ceremony

### Small UI change

- Find the current component and its consumers.
- Prefer an existing variant or token before creating a new pattern.
- Check the changed state plus the nearest contrasting state and representative screen.
- Record a system change only when shared behavior or API changed.

### New screen or feature

- Define the template/content structure and representative page scenarios.
- Reuse existing components first; justify each new component by a recurring responsibility.
- Cover responsive, content, role, loading, empty, error, and success behavior as relevant.
- Validate the feature flow as well as isolated components.

### New product, redesign, or design-system work

- Run an interface inventory or greenfield pattern inventory.
- Establish shared vocabulary, hierarchy, ownership, documentation, and governance.
- Start with a useful pilot, demonstrate value, then formalize the system.
- Plan how design assets, component code, documentation, and production stay synchronized.

### UI review

- Lead with findings ordered by severity.
- Distinguish user-task failures, system-level inconsistencies, component defects, and one-off polish.
- Name the affected pattern and consumers, not just the visible screen.
- Recommend the smallest system-level correction and the scenarios that must be rechecked.

## Enforce these rules

- Do not treat Atomic Design as five sequential production steps.
- Do not force the chemistry labels on a team whose own taxonomy is clearer.
- Do not approve placeholder-only or best-case-only screens; representative content and failure states are required.
- Do not create a page-specific component when a structure-based reusable pattern fits.
- Do not create a generic component so broad that it loses a single understandable responsibility.
- Do not let a component demo stand in for contextual page/flow verification.
- Do not let a polished static comp become an unquestionable specification; confirm interactive decisions in the real medium.
- Do not prescribe Pattern Lab, Mustache, or another named tool merely because the source used it.
- Do not present arbitrary spacing, color, typography, radius, motion, or breakpoint values as final when brand/system evidence is missing; use explicit provisional tokens or leave the value open.
- Do not use the book's “ask forgiveness” advice to bypass user authorization, organizational policy, security review, or high-impact change approval.
- Do not publish internal design-system material without explicit authorization.
- Keep the taxonomy mostly internal in routine handoffs; expose it only when it improves a decision, review, or implementation.

## Hand off the result

For material UI work, include a compact system note:

```text
User task and outcome:
Existing patterns reused:
Patterns added or changed:
Template/page scenarios verified:
Content and state extremes checked:
Responsive/accessibility/performance checks:
System impact, documentation, and follow-up:
```

Omit empty fields for a small task. Never substitute the note for the actual implementation or user-flow verification.
