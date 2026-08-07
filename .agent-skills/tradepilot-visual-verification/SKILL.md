# TradePilot Visual and Responsive Verification

## Purpose

Use this skill to verify TradePilot AI screens in a real browser or production-like local environment.

Its purpose is to detect visual, responsive, navigation, and interaction defects without changing approved business behavior.

Use it together with:

- `tradepilot-source-lock`;
- `tradepilot-ui-ux-implementation`;
- `tradepilot-focused-testing`.

## Verification Principle

Visual verification must prove that the implemented screen is:

- understandable;
- mobile-friendly;
- responsive;
- consistent with the approved design direction;
- complete for the tested lifecycle state;
- free from obvious layout and interaction defects.

Visual inspection does not replace functional testing. Functional and visual evidence must support each other.

## Environment Rules

Use a safe local or production-like environment with:

- isolated test data;
- authenticated access where required;
- representative session fixtures;
- frontend and backend versions matching the inspected repository;
- no production database mutation;
- no production evidence files;
- no real Gemini request unless explicitly authorized.

Prefer existing session data, fixtures, mocks, or stored canonical analysis responses.

Record the exact environment, route, viewport, and session state used.

## Required Viewports

Verify applicable screens at:

### Mobile Narrow

Approximately 320–375 CSS pixels wide.

Use this to detect:

- horizontal overflow;
- clipped controls;
- narrow cards;
- broken tabs;
- long filename issues;
- unusable dialogs;
- crowded headers.

### Mobile Standard

Approximately 390–430 CSS pixels wide.

Use this as the primary mobile acceptance viewport.

### Tablet

Approximately 768–1024 CSS pixels wide where the task affects responsive layout.

### Desktop

At least one common desktop viewport, such as 1280×800 or wider.

Do not optimize only for one device width.

## Required Screen-State Matrix

Verify only states relevant to the official task, but include representative lifecycle coverage at phase gates.

Possible states include:

- login;
- empty Sessions list;
- Sessions list with multiple statuses;
- Create Session;
- NEW;
- analysis processing;
- INITIAL_ANALYZED;
- WAITING;
- OPEN_POSITION;
- CLOSED;
- CLOSED_SKIPPED;
- archived terminal session;
- Archived Sessions empty state;
- Archived Sessions populated state;
- validation error;
- server failure;
- unauthorized;
- not found.

Do not fabricate states through production-code changes. Use safe fixtures or test data.

## Layout Checks

For every inspected screen, check:

- no horizontal page scrolling;
- no clipped text or controls;
- no overlapping elements;
- no unintended fixed-width content;
- safe wrapping for ticker, company name, notes, analysis, and filenames;
- readable content width;
- consistent page gutters;
- correct spacing between related and unrelated elements;
- cards do not become excessively narrow;
- empty space does not hide the primary action;
- sticky elements do not cover content.

Long Indonesian copy and realistic company names must be included in representative checks.

## Mobile Interaction Checks

Verify:

- touch targets are large and separated;
- the primary action is easy to reach;
- no critical interaction depends on hover;
- tabs and navigation remain usable;
- browser back behavior is understandable;
- dialogs fit within the viewport;
- controls remain reachable when the mobile keyboard is open;
- numeric inputs use suitable keyboard hints where implemented;
- upload controls work with supported mobile file selection;
- validation messages remain visible and associated with fields;
- unsent values survive recoverable validation errors.

Do not claim mobile support from a resized desktop layout alone when actual browser interaction can be inspected.

## Navigation Checks

Verify:

- login lands on the approved route;
- global Sessions and Archive navigation works;
- direct session URLs load correctly;
- refresh preserves the correct session;
- in-session Ringkasan, Analisis, and Riwayat navigation preserves context;
- Back returns to the intended parent screen;
- archived detail remains readable;
- legacy redirects do not loop;
- unauthorized or missing sessions show controlled states.

Check that navigation does not briefly show data from a previously opened session.

## Action Visibility Checks

For each inspected lifecycle state, verify that only approved actions appear.

Examples:

- NEW: Initial Evidence;
- INITIAL_ANALYZED: BUY, WAIT, SKIP;
- WAITING: WAIT Update;
- OPEN_POSITION: Position Update and Close;
- CLOSED or CLOSED_SKIPPED: Archive;
- archived terminal: Return to List.

Report any invalid, missing, duplicated, disabled-without-reason, or misleading action.

Visual verification must not redefine backend eligibility.

## Form Checks

For every applicable form, verify:

- labels are visible;
- required fields are understandable;
- field order is logical;
- controls align consistently;
- selected filenames wrap safely;
- helper and error text do not shift the layout unpredictably;
- primary and secondary actions remain distinct;
- submitting state prevents repeated interaction;
- long forms remain manageable on mobile;
- confirmation copy clearly describes the outcome.

Archive and Close must not visually imply permanent deletion.

## Analysis and Timeline Checks

Analysis content must:

- remain readable at mobile and desktop widths;
- preserve heading hierarchy;
- avoid edge-to-edge desktop line lengths;
- wrap tables, numbers, and long text safely;
- distinguish the latest analysis from historical analyses;
- avoid invented visual meaning.

Timeline content must:

- preserve chronological order;
- remain readable as a vertical stream on mobile;
- avoid overlapping markers or lines;
- keep long event content within the viewport;
- remain separate from Archive metadata unless explicitly approved.

## Accessibility-Oriented Visual Checks

Inspect:

- visible keyboard focus;
- meaningful focus order;
- text contrast;
- status meaning beyond color;
- disabled-control clarity;
- dialog focus containment where testable;
- error visibility;
- heading order;
- accessible button wording.

A visual PASS must not be issued when primary controls are inaccessible by keyboard.

## Screenshot Evidence

Capture evidence only when it helps establish acceptance or document a defect.

Each screenshot record should identify:

- route;
- viewport;
- lifecycle state;
- relevant test data;
- expected behavior;
- observed result.

Do not rely on screenshots alone for behavior such as submission, polling, ownership, or persistence.

Avoid collecting redundant screenshots of unchanged states.

## Defect Classification

Classify findings as:

### Blocking

The user cannot complete the approved task, a business rule appears incorrect, data is hidden, or mobile interaction is unusable.

### Major

The flow remains possible but is confusing, misleading, substantially broken, or inaccessible.

### Minor

Cosmetic inconsistency that does not materially affect use.

### Observation

A non-blocking limitation or improvement outside the current task.

Do not fix an observation if doing so exceeds the official scope.

## Fix Rules

Visual fixes may adjust:

- layout;
- spacing;
- wrapping;
- typography hierarchy;
- responsive behavior;
- focus treatment;
- approved copy consistency;
- component composition.

Visual fixes must not change:

- lifecycle;
- eligibility;
- API payloads;
- evidence requirements;
- analysis contracts;
- status values;
- database behavior;
- polling semantics;
- decision meaning.

Return `BLOCKED` if a visual problem can only be solved through an unapproved product or business change.

## PASS Rules

Issue `PASS` only when:

- required viewports and states were inspected;
- no blocking or major defect remains;
- relevant actions are visible and usable;
- mobile layout has no horizontal overflow;
- navigation and refresh behave correctly;
- evidence is sufficient and reproducible.

Use `PASS WITH LIMITATIONS` when only documented non-blocking limitations remain.

## Required Result Report

Report:

- official task ID and title;
- repository revision and environment;
- routes and states inspected;
- viewport matrix;
- browser or device used;
- visual and interaction findings;
- screenshots or evidence references;
- accessibility observations;
- defects fixed;
- defects remaining;
- confirmation that business behavior was unchanged;
- final status.