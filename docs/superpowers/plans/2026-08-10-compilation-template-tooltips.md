# Compilation Template Tooltip Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add concise hover explanations to the compilation-template wizard so users understand each field without changing template behavior.

**Architecture:** Reuse the existing `RAGFlowFormItem.tooltip` API and `FormLabel` tooltip rendering. Add localized copy in the English and Simplified Chinese locale trees. Keep descriptions contextual to the current wizard step; no API, schema, or persistence changes.

**Tech Stack:** React, TypeScript, react-i18next, existing RAGFlow form and tooltip components.

## Global Constraints

- Modify only the compilation-template wizard and its localized copy.
- Do not change compilation-template request payloads or backend behavior.
- Keep tooltip text short enough to read on hover and explain purpose, not implementation details.

---

### Task 1: Add localized tooltip copy

**Files:**
- Modify: `web/src/locales/en.ts`
- Modify: `web/src/locales/zh.ts`

- [ ] Add keys for group description, template description, extraction model, global rules, built-in template, schema sections, blueprint instruction, and page example.
- [ ] Keep the English and Simplified Chinese key sets identical.

### Task 2: Wire tooltips into the wizard

**Files:**
- Modify: `web/src/pages/user-setting/compilation-templates/create-next/components/basic-info-step.tsx`
- Modify: `web/src/pages/user-setting/compilation-templates/create-next/components/template-configuration.tsx`
- Modify: `web/src/pages/user-setting/compilation-templates/create-next/components/blueprints-step.tsx`

- [ ] Pass the matching localized tooltip to each `RAGFlowFormItem`.
- [ ] Use the existing `FormLabel` tooltip affordance; do not introduce a second tooltip implementation.
- [ ] Add the page-example explanation beside the existing Blueprint instruction field without changing editor behavior.

### Task 3: Verify the frontend change

**Files:**
- No new test file; this is presentational localized metadata using an existing tested form-label primitive.

- [ ] Run `npm run type-check` from `web`.
- [ ] Run `npm run lint` from `web`.
- [ ] Run `npm run format:check` from `web`.

