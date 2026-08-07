# TradePilot UI/UX Implementation

## Purpose

Use this skill for TradePilot AI frontend, layout, navigation, form, component, responsive, and interaction tasks.

The goal is to implement a guided, mobile-first experience while preserving the authoritative product lifecycle and backend behavior.

This skill must always be used together with `tradepilot-source-lock`.

## Core Principles

### One Screen, One Purpose

Each screen must have one clear user goal and one dominant primary action.

Do not display all of the following together by default:

* session list;
* create-session form;
* all lifecycle forms;
* complete analysis history;
* full timeline;
* terminal actions.

Use progressive disclosure. Show only information and actions relevant to the current session state.

### Backend-Authoritative Workflow

The backend remains the source of truth for:

* session status;
* action availability;
* ownership;
* evidence eligibility;
* decision eligibility;
* request state;
* archive eligibility.

Frontend code may present or group canonical state but must not invent or override business eligibility.

Never create a frontend-only lifecycle rule that conflicts with the API.

### Mobile First

Design and verify narrow mobile layouts before desktop enhancement.

Required behavior:

* single-column layout on mobile;
* no horizontal scrolling;
* touch-safe controls;
* readable spacing;
* labels above inputs;
* long content wraps safely;
* primary actions remain easy to find;
* no critical interaction depends on hover;
* dialogs and forms remain usable with the mobile keyboard open.

Desktop may add columns or contextual side panels, but must not change workflow order or expose unrelated actions.

## Navigation Rules

Approved primary areas must remain simple and task-oriented.

Typical structure:

* Sessions;
* New Session;
* Session Detail;
* Analysis;
* History;
* Archived Sessions.

Route-based pages must recover state from the backend and route identifier.

Do not depend exclusively on temporary selected-session state.

Direct URL access and refresh must:

* load the correct session;
* preserve ownership checks;
* show controlled loading, unauthorized, not-found, and failure states;
* avoid duplicate submissions.

## Session Detail Rules

Session Detail must clearly show:

* ticker;
* company name;
* canonical status using approved user-facing wording;
* relevant timestamps;
* current step;
* latest relevant result;
* approved next action.

Only render actions valid for the current backend state.

Examples:

* NEW: Initial Evidence action;
* INITIAL_ANALYZED: BUY, WAIT, and SKIP;
* WAITING: WAIT Update;
* OPEN_POSITION: Position Update and Close;
* CLOSED or CLOSED_SKIPPED: read-only and Archive when non-archived;
* archived terminal session: read-only and Restore.

Do not render inactive lifecycle forms merely because their components exist.

## Form Requirements

Every form must:

* contain only approved fields;
* preserve canonical validation;
* show visible labels;
* preserve valid input after recoverable errors;
* prevent duplicate submission;
* expose clear submitting, success, and failure states;
* use suitable input types for mobile;
* maintain safe filename and error-message wrapping.

Do not add convenience fields, automatic calculations, defaults, or transformations unless explicitly approved.

Submission success must return the user to the correct session context.

## Analysis Presentation

Analysis must remain faithful to the canonical API response.

Do not:

* generate new conclusions in the frontend;
* reinterpret missing values;
* create unsupported scores;
* invent bullish, bearish, risk, or PnL color meaning;
* alter the approved analysis contract.

Display the latest analysis clearly and allow previous approved analysis types to be accessed chronologically.

Separate analysis reading from unrelated forms.

## Visual Hierarchy

Use the approved TradePilot design direction and existing design tokens.

The interface should feel:

* calm;
* analytical;
* trustworthy;
* structured;
* readable.

Use visual emphasis to clarify hierarchy, not to change business meaning.

Status must not rely on color alone.

Primary, secondary, neutral, and terminal actions must remain distinguishable.

Close and Archive are not Delete actions and must not use misleading destructive language or treatment.

## Content Rules

User-facing interface copy must be in Indonesian unless an authoritative document requires otherwise.

Technical identifiers, API values, schemas, and implementation documentation remain in English.

Do not introduce:

* new lifecycle terminology;
* unapproved numbering;
* speculative explanatory copy;
* marketing language;
* new product concepts.

Use concise, factual, action-oriented wording.

## Required System States

Implement relevant states for every screen:

* loading;
* empty;
* submitting;
* processing;
* success;
* validation error;
* server failure;
* unauthorized;
* not found;
* retry where permitted.

Do not display a blank screen, stale data, fabricated success, or an unrelated form while state is unresolved.

## Reuse and Refactoring

Prefer reusing existing components when they directly support the approved requirement.

Refactor only when necessary to:

* move a component into the new screen architecture;
* isolate state ownership;
* eliminate unsafe coupling;
* support responsive behavior;
* satisfy the official task.

Do not perform unrelated cleanup, component-system redesign, or abstraction work.

## Verification

For each task, verify only the affected states and viewports unless a phase gate requires broader coverage.

Minimum applicable checks:

* canonical status fixtures;
* mobile narrow;
* mobile standard;
* desktop;
* long company names;
* long filenames;
* optional or missing data;
* validation and server error;
* direct URL and refresh;
* duplicate-submit prevention;
* action visibility.

Do not make a real Gemini request for visual or component verification unless explicitly required.

## BLOCKED Conditions

Return `BLOCKED` when:

* the required UI needs a new business rule;
* action availability cannot be derived from authoritative backend state;
* approved copy or field definitions are unclear and materially affect behavior;
* the repository requires changing lifecycle, evidence, analysis, or API contracts;
* the task would require unrelated architecture replacement;
* the authoritative task conflicts with the current UI/UX PRD.

## Required Result Report

Report:

* official task ID and title;
* screens and components changed;
* route or state ownership changes;
* responsive states verified;
* tests executed;
* acceptance criteria results;
* business behavior confirmed unchanged;
* limitations or deviations;
* final status.
