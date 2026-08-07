# TradePilot Accessibility Review

## Purpose

Use this skill for TradePilot AI tasks that review or improve accessibility across routes, forms, dialogs, navigation, analysis content, timelines, system states, and responsive layouts.

Use it together with:

- `tradepilot-source-lock`;
- `tradepilot-ui-ux-implementation`;
- `tradepilot-focused-testing`;
- `tradepilot-visual-verification` when browser inspection is required.

Its purpose is to make the approved workflow usable through keyboard, assistive technology, and non-visual cues without changing product behavior.

## Core Rule

Accessibility work may improve semantics, focus, labels, contrast, interaction clarity, and error communication.

It must not change:

- lifecycle;
- action eligibility;
- evidence requirements;
- field definitions;
- API contracts;
- analysis content;
- session ownership;
- Archive rules;
- decision meaning.

Return `BLOCKED` if an accessibility issue can only be solved through an unapproved product change.

## Semantic Structure

Every page must have:

- one clear page-level heading;
- logical heading order;
- meaningful landmarks where supported;
- descriptive page and section titles;
- semantic buttons for actions;
- semantic links for navigation;
- real form controls instead of clickable generic containers.

Do not use heading styles only for visual size.

Do not use a link for a mutation or a button for ordinary navigation unless repository conventions require an accessible equivalent.

## Keyboard Navigation

All primary workflows must be operable without a mouse.

Verify:

- logical tab order;
- no keyboard trap;
- visible focus indicator;
- Enter and Space behavior on controls;
- Escape behavior for dismissible dialogs where appropriate;
- focus does not jump unpredictably after state updates;
- hidden or disabled actions cannot receive focus;
- mobile and desktop navigation remain keyboard reachable.

Do not remove focus outlines unless replaced by an equally visible approved focus style.

## Focus Management

After route navigation, focus should move to a meaningful page location, typically the page heading or main content.

After opening a dialog:

- focus enters the dialog;
- focus remains within the dialog while open;
- closing returns focus to the triggering control where practical.

After form submission:

- success focus moves to the resulting status or next screen;
- validation failure focus moves to the error summary or first invalid field;
- server failure remains understandable without losing entered values.

Do not move focus on every polling refresh or minor background update.

## Forms

Every input must have:

- a persistent visible label;
- programmatic label association;
- correct required-state communication;
- clear instructions where needed;
- accessible error association;
- logical grouping for related controls.

Placeholder text must not replace a label.

Errors must:

- explain the problem;
- identify the affected field;
- not rely on color alone;
- remain visible until corrected or dismissed appropriately.

Use suitable input type, autocomplete, and input mode where they improve mobile and assistive use without changing canonical values.

## Buttons and Action Names

Interactive controls must have names that describe the outcome.

Good examples:

- Buat Sesi;
- Buka Sesi;
- Kirim Bukti Awal;
- Kirim WAIT Update;
- Update Posisi;
- Tutup Sesi;
- Arsipkan Sesi;
- Kembalikan ke Daftar.

Avoid ambiguous labels such as:

- OK;
- Submit;
- Click Here;
- Continue,

unless the surrounding accessible name makes the outcome explicit.

Icon-only controls require an accessible name and visible or discoverable purpose.

## Status and System Feedback

Loading, submitting, processing, success, failure, and retry states must be understandable without visual observation.

Where supported, use appropriate live-region behavior for important state changes.

Do not repeatedly announce polling progress or unchanged content.

Status must not rely only on:

- color;
- icon;
- position;
- animation.

Use concise text such as:

- Analisis sedang diproses;
- Bukti berhasil dikirim;
- Sesi berhasil diarsipkan;
- Terjadi kesalahan. Coba lagi.

Do not announce fabricated success before the backend confirms it.

## Color and Contrast

Text, controls, borders, focus indicators, status labels, and error states must have sufficient contrast for their purpose.

Do not communicate:

- lifecycle status;
- gain or loss;
- enabled state;
- error;
- selected tab,

through color alone.

Pair color with text, shape, icon, border, or state attribute.

Do not introduce hardcoded bullish, bearish, or PnL color semantics that are not product-approved.

## Dialogs and Confirmations

Archive, Restore, Close, and other approved confirmations must:

- have a descriptive title;
- explain the result of the action;
- expose clearly named confirm and cancel controls;
- receive initial focus safely;
- prevent interaction with background content where appropriate;
- return focus on close;
- remain usable at mobile widths and with the keyboard open.

Avoid confirmation copy that only says “Are you sure?”

## Navigation Accessibility

Global and in-session navigation must:

- expose the current route or selected section;
- use understandable labels;
- remain reachable at mobile and desktop widths;
- preserve logical reading order;
- not depend on hover;
- not hide essential destinations behind inaccessible controls.

Tabs or segmented controls must use repository-consistent accessible semantics.

Direct URL, refresh, not-found, and unauthorized states must still provide a meaningful page title and safe navigation path.

## Analysis Content

Analysis output must preserve semantic reading order.

Use:

- headings for major sections;
- lists for grouped findings;
- tables only for genuinely tabular information;
- clear labels for values;
- readable numeric formatting.

Do not build essential analysis structure from visually positioned generic containers.

Tables must:

- have meaningful headers;
- remain readable on mobile;
- avoid inaccessible horizontal clipping;
- provide an alternative stacked presentation where required.

Do not rewrite or simplify canonical analysis content solely for accessibility without product approval.

## Timeline

The session timeline must:

- follow chronological document order;
- use meaningful event headings or labels;
- not rely on the visual spine or marker alone;
- keep timestamps associated with the correct event;
- remain understandable when CSS is unavailable;
- avoid duplicate screen-reader content from decorative elements.

Archive metadata should remain separate from the trading timeline unless explicitly approved.

## Images and Evidence Inputs

Decorative images require empty alternative text where applicable.

Informational images require concise alternative text only when the image itself is intended for user interpretation.

Uploaded orderbook and chart evidence may not have meaningful automatic descriptions. Do not invent financial interpretation as alternative text.

File inputs must expose:

- accepted file expectations where approved;
- selected filename;
- validation error;
- upload state.

## Motion and Timing

Avoid unnecessary animation.

Respect reduced-motion preferences where supported.

Do not use auto-advancing content, flashing indicators, or time-limited interactions.

Polling updates must not repeatedly steal focus or reset scroll position.

## Responsive Accessibility

At mobile and zoomed layouts:

- controls must not overlap;
- content must reflow;
- horizontal scrolling must not be required for ordinary page use;
- text must remain readable;
- dialogs must fit the viewport;
- focus indicators must remain visible;
- sticky actions must not cover focused content.

Verify at high browser zoom where practical, especially for forms and navigation.

## Focused Verification

Minimum applicable checks:

- keyboard-only navigation;
- visible focus;
- heading order;
- label and input association;
- required and error communication;
- dialog focus entry and return;
- current navigation state;
- non-color status meaning;
- loading and success announcements where implemented;
- mobile reflow;
- zoomed layout;
- representative screen-reader semantics where tooling permits.

Automated accessibility tools may support review but cannot replace manual keyboard and semantic inspection.

## Defect Severity

### Blocking

The user cannot complete an approved workflow using keyboard or assistive technology.

### Major

Important information, action, error, or state is inaccessible or seriously ambiguous.

### Minor

A semantic or contrast issue that does not block the flow.

### Observation

A non-blocking improvement outside the current task.

Do not expand scope to fix unrelated observations.

## PASS Rules

Issue `PASS` only when:

- the affected flow is keyboard operable;
- labels and errors are associated correctly;
- focus behavior is safe;
- status does not rely on color alone;
- no blocking or major accessibility defect remains;
- fixes do not change business behavior.

Use `PASS WITH LIMITATIONS` only for documented, non-blocking limitations.

## BLOCKED Conditions

Return `BLOCKED` when:

- required semantics conflict with an authoritative interaction requirement;
- accessible action naming requires an unresolved product decision;
- repository components cannot be corrected without broad out-of-scope replacement;
- authentication or route behavior prevents meaningful keyboard access;
- analysis content structure is insufficient and changing the contract is required;
- testing requires unavailable infrastructure that cannot be added within scope.

## Required Result Report

Report:

- official task ID and title;
- routes and components reviewed;
- keyboard flow tested;
- semantic and heading findings;
- form-label and error behavior;
- dialog and focus behavior;
- status and contrast findings;
- mobile and zoom verification;
- automated tools used;
- defects fixed and remaining;
- confirmation that business behavior was unchanged;
- final status.