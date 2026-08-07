# TradePilot Next.js Routing and State Recovery

## Purpose

Use this skill for TradePilot AI tasks involving Next.js routes, layouts, navigation, session-detail loading, direct URLs, refresh recovery, client state, polling ownership, and legacy-route cutover.

Use it together with:

- `tradepilot-source-lock`;
- `tradepilot-ui-ux-implementation`;
- `tradepilot-focused-testing`.

Its purpose is to make the guided multi-page flow reliable without changing backend business behavior.

## Core Rule

Route state must be recoverable from:

- the current URL;
- authenticated user context;
- authoritative backend data.

Do not require temporary browser state, a previously selected session, or navigation from a specific parent page to render a valid screen.

A direct URL and page refresh must recover the same session safely.

## Approved Route Responsibility

Each route must have one clear responsibility.

Typical approved structure:

- `/login` — authentication;
- `/sessions` — non-archived session list;
- `/sessions/new` — session creation;
- `/sessions/archived` — archived session list;
- `/sessions/[sessionId]` — session summary and current action;
- `/sessions/[sessionId]/analysis` — analysis reading;
- `/sessions/[sessionId]/history` — complete history.

Focused lifecycle forms may use nested routes, drawers, or route-controlled subviews when approved by the official task.

Do not add extra routes merely to mirror every component.

## Server and Client Boundary

Follow the repository’s established Next.js architecture.

Prefer server-side loading where it improves:

- authentication enforcement;
- direct URL reliability;
- initial session retrieval;
- not-found handling;
- reduced client loading complexity.

Use client components only where needed for:

- forms;
- polling;
- upload interaction;
- local validation;
- modal or drawer behavior;
- interactive navigation state.

Do not convert large route trees to client components without necessity.

## Route Parameter Validation

Treat `sessionId` as untrusted input.

The route must handle:

- missing identifier;
- malformed identifier;
- non-existent session;
- unauthorized session;
- archived session;
- valid owned session.

Do not leak whether another user’s session exists.

Use repository-standard not-found or access-denied behavior.

## Authentication and Authorization

Protected routes must require authenticated access.

The frontend may redirect unauthenticated users, but backend ownership checks remain mandatory.

Preserve safe intended-route behavior only if supported by the existing authentication design.

Avoid:

- redirect loops;
- exposing protected content before auth resolution;
- relying on hidden UI as authorization;
- storing sensitive session aggregates in globally persistent client state.

## Route-Based Data Loading

Every session route must load its session by `sessionId`.

Do not use only:

- `selectedSession`;
- prior list-page state;
- browser memory;
- stale cached aggregate from another session.

Loading must expose controlled states:

- loading;
- success;
- unauthorized;
- not found;
- recoverable failure.

When moving rapidly between sessions, stale responses must not overwrite the current route’s data.

Use aborting, request identity, framework cache controls, or repository-consistent safeguards.

## Cache and Freshness

Choose caching behavior according to data volatility.

Session lifecycle, request status, action availability, and archive state are dynamic and must not remain stale beyond acceptable workflow behavior.

Do not use static generation for user-specific session state.

After a successful mutation, use the repository’s approved mechanism to:

- revalidate;
- refetch;
- invalidate;
- update local state from the canonical response.

Do not manually fabricate the resulting lifecycle state.

## Navigation Rules

Use framework-native navigation.

After mutations:

- Create Session → new Session Detail;
- Initial Evidence or analysis submission → processing/current session context;
- decision → resulting session state;
- close → terminal Session Detail;
- archive → Archived Sessions or a clear archived state;
- restore → Completed section or terminal detail.

Back and Cancel must return to the intended parent without submitting or losing already persisted work.

Do not use full-page browser reloads unless technically required.

## Refresh Recovery

Refreshing during any supported state must not:

- create a duplicate session;
- upload evidence again;
- resubmit a decision;
- start another analysis request;
- lose the canonical session;
- redirect incorrectly to the workspace root.

The route must recover active request status from the backend.

Persisted backend state, not client optimism, determines the recovered view.

## Polling Ownership

Only one mounted owner may poll a specific active request.

The polling component must:

- know the canonical request identifier;
- stop unnecessary polling on unmount or route change;
- avoid overlapping intervals;
- avoid restarting submission;
- recover processing state after refresh;
- stop when terminal request status is reached;
- handle failure according to the approved retry contract.

The Sessions list must not continuously poll every session.

Do not run polling simultaneously in layout, summary, and analysis components for the same request.

## Mutation Safety

Every client mutation must:

- prevent duplicate submission;
- handle network uncertainty;
- preserve valid input after recoverable errors;
- use canonical backend responses;
- display submitting and failure states;
- avoid optimistic lifecycle transitions unless explicitly safe and approved.

When the response is uncertain, refetch authoritative state instead of assuming failure or success.

## Layout and Nested Route Rules

Shared layouts may provide:

- global navigation;
- session identity;
- approved in-session navigation;
- common loading boundaries.

They must not:

- fetch unrelated heavy data for every nested route;
- start polling globally;
- render all lifecycle actions;
- preserve stale session data across different `sessionId` values;
- hide route-specific errors.

Ensure component keys or boundaries update correctly when `sessionId` changes.

## Legacy Route Cutover

Do not redirect `/trade-workspace` until the official parity audit and phase gate pass.

Before cutover, verify:

- no approved workflow depends on the legacy page;
- internal links use the new routes;
- direct URLs work;
- tests no longer assume the old workspace;
- authentication redirect does not loop.

After cutover, preserve a safe redirect to `/sessions` unless an authoritative task requires removal.

Do not delete legacy components in the redirect task unless explicitly in scope.

## Error Boundaries

Use repository-consistent route-level handling for:

- loading;
- not found;
- unauthorized;
- server failure;
- unexpected rendering failure.

Errors must provide a safe path back to Sessions or retry when permitted.

Do not reveal raw stack traces, identifiers, or backend internals to the user.

## Focused Verification

Minimum applicable checks:

- successful login destination;
- direct session URL;
- refresh on each affected route;
- malformed, missing, unauthorized, and archived session;
- rapid navigation between sessions;
- create-to-detail navigation;
- mutation success and failure navigation;
- refresh during processing;
- one polling owner;
- browser back and Cancel;
- legacy redirect after approved cutover;
- mobile navigation overflow.

Use mocks, fixtures, or safe local data. No real Gemini request is required by default.

## BLOCKED Conditions

Return `BLOCKED` when:

- the repository is not using Next.js as assumed by the task;
- route requirements conflict with authoritative documents;
- authentication or ownership cannot be enforced safely;
- direct URL recovery requires a new backend contract outside scope;
- duplicate-request prevention cannot be established;
- polling ownership is ambiguous across existing components;
- legacy cutover parity has not passed;
- the task requires a broad routing architecture replacement not explicitly approved.

## Required Result Report

Report:

- official task ID and title;
- routes and layouts changed;
- server/client boundary decisions;
- data loading and cache behavior;
- authentication and ownership behavior;
- refresh and direct-URL verification;
- polling ownership;
- navigation after mutations;
- legacy-route impact;
- exact focused tests;
- limitations or deviations;
- confirmation that business contracts remain unchanged;
- final status.