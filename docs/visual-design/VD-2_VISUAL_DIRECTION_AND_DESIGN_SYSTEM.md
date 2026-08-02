# VD-2 — Visual Direction and Design System

## 1. Design-System Metadata

| Field | Value |
| --- | --- |
| Task | VD-2 — Visual Direction and Design System |
| Date | 2026-08-02 |
| Branch | `main` |
| Baseline commit | `00c11b2828a1c40b9571d48c1e468365deeb4be9` |
| VD-1 commit verification | VERIFIED: `00c11b2828a1c40b9571d48c1e468365deeb4be9` is `HEAD` and contains the accepted VD-1 document. |
| Source documents | PRD, Detailed Task Plan, Authoritative Task Ledger, and VD-1 audit listed below. |
| Frontend framework | Next.js 16.2.10 / React 19.2.4, App Router. |
| Styling approach | Tailwind CSS v4 with a global stylesheet at `frontend/src/app/globals.css`. |
| Implementation scope | Semantic global CSS custom properties only; no optional primitives and no screen migration. |

Authoritative sources read directly:

- `docs/TradePilot AI PRD v2 — Authoritative Rebuild.md`
- `docs/TradePilot AI Rebuild — Detailed Task Plan.md`
- `docs/rebuild/AUTHORITATIVE_TASK_LEDGER.md`
- `docs/visual-design/VD-1_CURRENT_UI_VISUAL_AUDIT.md`

Pre-existing working-tree changes were present at baseline and were not modified, staged, or cleaned.

## 2. Visual Direction

**Direction name:** `Calm Analytical Workspace`

The interface should feel calm, focused, trustworthy, modern, analytical, structured, professional, and readable during repeated daily use. It should support financial decision support without resembling an automated brokerage terminal.

The desired user perception is: “I can understand the current trade story, separate confirmed facts from Gemini’s advice, and see the next explicit action without pressure.” Clarity takes priority over decoration. The light workspace uses restrained blue as the primary interaction accent and semantic tones as supporting communication aids.

The interface must not feel playful, promotional, casino-like, overly futuristic, neon-heavy, crowded like a professional market-data terminal, emotionally manipulative, or visually suggestive that Gemini executes trading decisions.

This direction follows the PRD’s product definition: TradePilot AI is an AI trading analyst rather than an automated trading system; Gemini is advisory; user decisions and execution facts belong to the user; one session preserves one complete chronological trade story.

Only light mode is approved. Dark mode is not part of VD-2.

## 3. Design Principles

| Principle | Practical UI implication |
| --- | --- |
| Decision clarity | Present the currently available explicit user actions with clear labels and equal semantic respect where they are alternatives. Visual hierarchy must not silently turn a recommendation into a decision. |
| Factual authority | Confirmed user-owned facts use a stable factual treatment that is easy to scan and is never visually subordinate to advisory prose. |
| Advisory transparency | Gemini output is visibly labeled and differentiated as advisory; recommendations, probabilities, risks, plans, and conclusions must not look like execution confirmations. |
| Lifecycle legibility | Use text labels, structure, and restrained semantic tones to make the seven approved business statuses understandable without relying on color alone. |
| Calm information density | Use a small surface hierarchy, readable line lengths, deliberate grouping, and limited elevation. Avoid a wall of equally weighted cards. |
| Mobile-first readability | Design tokens support narrow screens first: readable type, full-width controls, wrapping-safe text, and touch-sized actions. Workspace rearrangement remains a later task. |
| Action safety | Primary, secondary, caution, destructive, disabled, and loading states communicate consequence and availability without automatic behavior or emotional pressure. |
| Consistency | Reuse semantic roles and token values instead of feature-specific color, spacing, radius, or shadow decisions. |
| Accessibility | Meaning is available through text and structure; focus is visible; labels and errors are associated; loading and errors can be announced; no formal compliance claim is made without verification. |

## 4. Information-Authority Model

| Information class | Authority owner | Visual emphasis | Recommended surface treatment | Prohibited treatment |
| --- | --- | --- | --- | --- |
| User-owned facts | User / persisted session data | High scanability, stable labels, strong text | Factual summary surface with clear labels, definition-list or field structure, standard border | Do not style as Gemini recommendation or allow advisory tone to visually override it. |
| Gemini advisory output | Gemini, advisory only | Readable but secondary to confirmed facts | Advisory surface with explicit “advisory” labeling, restrained information tone, readable long-form text | Do not use execution-like success styling, order-entry language, or stronger authority cues than facts. |
| System metadata | System | Compact, low emphasis | Inset or metadata treatment with muted text | Do not compete with ticker, status, facts, or next action. |
| User-entered notes | User | Contextual, readable | Inset factual treatment; preserve whitespace and attribution as user note | Do not merge into Gemini output or imply it was generated by Gemini. |
| Processing information | System | Temporarily prominent and clear | Processing feedback surface with text label and status structure | Do not create a new business status or imply a decision has occurred. |
| Warning information | System/product constraints | Noticeable but calm | Warning feedback surface with text, supporting explanation, and explicit next action where applicable | Do not use warning tone for ordinary WAIT meaning or treat caution as failure. |
| Errors | System/request | High enough to recover safely | Danger feedback surface with concise title, safe body, and manual retry/action slot | Do not represent failure as a permanent business status or hide the recovery path. |
| Terminal confirmations | User action plus persisted result | Clear finality and factual result | Success or neutral terminal surface with explicit status text and preserved history | Do not imply `CLOSED_SKIPPED` is a successful trade, or `CLOSED` is an error. |

## 5. Color System

All values below are light-mode semantic roles. The CSS implementation is in `frontend/src/app/globals.css`. Contrast must be checked for each text/background pairing when consumed; the restrained values are intended as a foundation, not a formal WCAG certification.

| Token | Value | Usage | Contrast consideration | Prohibited usage |
| --- | --- | --- | --- | --- |
| `--color-page-background` | `#f5f7fa` | Page canvas | Dark text is intended for readable body copy. | Do not use as a status tone. |
| `--color-elevated-background` | `#ffffff` | Raised/global surfaces | Pair with strong/default text and a border or elevation cue. | Do not imply success. |
| `--color-surface-standard` | `#ffffff` | Standard content surface | Use dark text and standard border. | Do not nest indefinitely. |
| `--color-surface-muted` | `#eef2f6` | Inset or low-priority content | Use strong/default text, not low-contrast text. | Do not use for active actions. |
| `--color-surface-factual` | `#f7fafc` | User-owned fact grouping | Use strong labels and default values. | Do not use for Gemini output. |
| `--color-surface-advisory` | `#f4f8ff` | Gemini advisory grouping | Pair with information label and readable dark text. | Do not imply authority or execution. |
| `--color-surface-action` | `#ffffff` | Action group background | Emphasize through hierarchy and borders, not saturation. | Do not make every section an action surface. |
| `--color-surface-feedback` | `#ffffff` | Feedback base | Combine with semantic border/tone. | Do not rely on white alone for meaning. |
| `--color-text-strong` | `#172033` | Headings, confirmed values, high-priority labels | Intended for high contrast on light surfaces. | Do not use for all metadata. |
| `--color-text-default` | `#334155` | Body and analysis text | Use for normal reading content. | Do not use as a semantic status by itself. |
| `--color-text-muted` | `#64748b` | Metadata, helper text, secondary labels | Check small-text contrast carefully. | Do not use for required labels or critical status. |
| `--color-text-inverse` | `#ffffff` | Text on sufficiently dark action backgrounds | Must only be used where background contrast is verified. | Do not place on pale semantic backgrounds. |
| `--color-border-default` | `#d8e0ea` | Standard divisions and controls | Must remain visible against page/surface backgrounds. | Do not use as the only status cue. |
| `--color-border-strong` | `#b8c5d4` | Emphasized facts, focus-adjacent structure | Supports stronger grouping without heavy decoration. | Do not create visual alarm. |
| `--color-action-primary` | `#2563a9` | Confirmed primary interaction | White label text requires contrast verification. | Do not imply BUY or financial success globally. |
| `--color-action-primary-hover` | `#1d4f87` | Hover state | Preserve label contrast. | Do not change product meaning. |
| `--color-action-primary-active` | `#163d69` | Pressed/active state | Use with visible focus where applicable. | Do not use for lifecycle status. |
| `--color-action-primary-subtle` | `#e8f1fb` | Subtle primary context | Pair with dark blue/strong text. | Do not use as a completed state. |
| `--color-focus-ring` | `#2f80c9` | Keyboard focus indication | Must remain visible against light surfaces. | Do not remove in favor of color-only hover. |
| `--color-status-success` | `#18794e` | Positive completion or valid confirmation | Pair with text and structure; verify small-text contrast. | Do not equate with BUY or trade profit. |
| `--color-status-success-subtle` | `#e9f7ef` | Success background | Use dark success text and a label. | Do not use for ordinary OPEN_POSITION. |
| `--color-status-warning` | `#9a6700` | Caution and warning | Use dark text/strong border pairing where needed. | Do not equate WAIT with an error. |
| `--color-status-warning-subtle` | `#fff7df` | Warning background | Must include text cue. | Do not use for all amber actions automatically. |
| `--color-status-danger` | `#b42318` | Errors and destructive confirmation | Pair with explicit danger text and recovery/confirmation structure. | Do not use for SKIP merely because it is terminal. |
| `--color-status-danger-subtle` | `#fff0ee` | Error/danger background | Use dark danger text and non-color cue. | Do not make a user choice look like system failure. |
| `--color-status-information` | `#235c9f` | Informational state and advisory cue | Pair with explicit text label. | Do not imply Gemini execution. |
| `--color-status-information-subtle` | `#eaf3ff` | Information background | Use readable dark text. | Do not use for user-owned fact authority. |
| `--color-status-processing` | `#5b4bb7` | Processing indicator | Include processing text and announcement. | Do not add a business status. |
| `--color-status-processing-subtle` | `#f0edff` | Processing background | Pair with text, not animation alone. | Do not imply success or failure. |

**Trading-decision guidance.** Later tasks may use the semantic roles as follows, with visible labels and structural cues: BUY may use the primary interaction role when it is the selected user action context; WAIT may use the warning/caution role because it communicates waiting or attention, not failure; SKIP may use a neutral or caution/destructive confirmation context depending on the confirmation consequence, but never danger solely because it ends a session; CLOSE may use a destructive confirmation context because it closes an open position, but never an error or failure context. None of these mappings defines financial success, recommendation, or automatic execution. BUY, WAIT, SKIP, and CLOSE remain explicit user actions.

## 6. Lifecycle Status System

The approved business statuses are copied from the PRD: `DRAFT`, `ANALYZING`, `ANALYZED`, `WAITING`, `OPEN_POSITION`, `CLOSED`, and `CLOSED_SKIPPED`. No status is added or renamed here.

| Status | Indonesian display label | Semantic visual role | Badge tone | Future icon intent | Required non-color cue |
| --- | --- | --- | --- | --- | --- |
| `DRAFT` | Draft | Information / neutral | Information-subtle | Document or unfinished-state icon | Visible “Draft” text and incomplete-flow structure. |
| `ANALYZING` | Menganalisis | Processing | Processing-subtle | Spinner/progress intent, if later approved | Visible “Menganalisis” text and processing announcement. |
| `ANALYZED` | Dianalisis | Information / ready | Information-subtle | Analysis/ready intent | Visible “Dianalisis” text and available-action structure. |
| `WAITING` | Menunggu | Caution / attention | Warning-subtle | Pause/clock intent | Visible “Menunggu” text and WAIT Update context. |
| `OPEN_POSITION` | Posisi Terbuka | Information / active | Information-subtle | Open-position intent | Visible status text and position facts. |
| `CLOSED` | Ditutup | Neutral terminal | Muted or success-neutral | Closed/archive intent | Visible “Ditutup” text, closure facts, and history. |
| `CLOSED_SKIPPED` | Ditutup (Skip) | Neutral terminal / skipped | Muted or warning-neutral | Skipped/ended-without-position intent | Visible “Ditutup (Skip)” text and clear no-position indication. |

The Indonesian labels above are already supported by the current approved UI’s `statusLabels` mapping in `frontend/src/features/trade-workspace/workspace.tsx`; they are not newly invented in VD-2. Request statuses such as `PENDING`, `PROCESSING`, `COMPLETED`, and `FAILED` are not business statuses and must remain separate.

## 7. Typography System

The system uses the existing local/system font approach. No external font is added. The default family remains `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif`.

| Role | Size | Line height | Weight | Letter-spacing guidance | Intended usage |
| --- | --- | --- | --- | --- | --- |
| Application title | `1.125rem` | `1.2` | 700 | Tight, not condensed | Product identity in shell. |
| Page title | `1.875rem` | `1.2` | 700 | Tight | Main page heading. |
| Section title | `1.25rem` | `1.2` | 650–700 | Normal | Major content section. |
| Card title | `1rem` | `1.2` | 600–700 | Normal | Surface heading. |
| Body | `1rem` | `1.5` | 400 | Normal | General UI and facts. |
| Compact body | `0.875rem` | `1.4` | 400–500 | Normal | Supporting descriptions and compact controls. |
| Label | `0.875rem` | `1.4` | 600 | Normal | Form and fact labels. |
| Metadata | `0.75rem` | `1.4` | 400–500 | Slightly open where uppercase is used | Timestamps and low-priority metadata. |
| Metric value | `1.5rem` | `1.2` | 650–700 | Tight | Numeric fact requiring emphasis. |
| Ticker | `0.875rem` | `1.4` | 700 | Small uppercase may be used sparingly | Security/session identifier. |
| Status label | `0.75rem` | `1.4` | 600–700 | Normal | Always paired with visible status text. |
| Button label | `0.875rem` | `1.4` | 600 | Normal | Action labels; do not rely on icon only. |
| Long-form Gemini analysis | `0.9375rem` | `1.7` | 400 | Normal | Indonesian advisory output and long paragraphs. |

Indonesian long-form analysis should use generous line height, a maximum readable width of `42rem`, preserved paragraph/list structure, and strong section labels. Avoid all-caps for sentences and avoid tight tracking that harms reading.

## 8. Spacing and Layout Foundations

The base spacing unit is `0.25rem` (4px). The scale is `1, 2, 3, 4, 5, 6, 8, 10, 12` units, represented by `--space-1` through `--space-12` where defined. Semantic aliases are preferred for future consumers.

| Foundation | Token/value | Intent |
| --- | --- | --- |
| Base unit | `--space-unit` / `0.25rem` | Smallest repeatable rhythm. |
| Mobile page gutter | `--layout-gutter-mobile` / `1rem` | Narrow and wider mobile default. |
| Tablet gutter | `--layout-gutter-tablet` / `1.5rem` | Tablet content inset. |
| Desktop gutter | `--layout-gutter-desktop` / `2rem` | Desktop content inset. |
| Section gap | `--space-section` / `1.5rem` | Separation between major content groups. |
| Card padding | `--space-card` / `1.25rem` | Standard surface content. |
| Compact card padding | `--space-card-compact` / `0.75rem` | Dense metadata/inset content. |
| Form field gap | `--space-field` / `0.75rem` | Label/control and field rhythm. |
| Action gap | `--space-action` / `0.5rem` | Related controls. |
| Maximum readable text width | `--layout-text-readable` / `42rem` | Long Indonesian analysis and explanatory text. |
| Maximum application width | `--layout-application-max` / `72rem` | Overall application canvas; not a workspace redesign. |

These foundations do not prescribe or change current workspace columns. VD-3 owns workspace layout.

## 9. Surface Hierarchy

| Level | Background role | Border role | Radius | Elevation | Padding intent | Appropriate use | Prohibited nesting |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Page canvas | `--color-page-background` | None or default at boundaries | None | None | Page gutters | Global background. | Do not use for content requiring grouping. |
| Primary workspace surface | `--color-elevated-background` | `--color-border-default` | `--radius-large` | `--elevation-low` | `--space-card` | Main selected-session or primary work area. | Do not place every child in another raised surface. |
| Section surface | `--color-surface-standard` | Default | `--radius-standard` | Low or none | Card padding | Evidence, action, history, or analysis section. | Avoid stacking identical section surfaces without hierarchy. |
| Inset surface | `--color-surface-muted` | Default or none | `--radius-compact` | None | Compact padding | Metadata, helper context, secondary details. | Do not use for primary actions or facts needing emphasis. |
| Factual summary surface | `--color-surface-factual` | `--color-border-strong` | Standard | Low | Card padding | User-owned facts and confirmed position/session data. | Do not put Gemini output inside without explicit separation. |
| Advisory surface | `--color-surface-advisory` | Information-toned border | Standard | None/low | Card padding | Gemini advisory output. | Do not use execution-success or confirmation styling. |
| Interactive action surface | `--color-surface-action` | Strong/default | Large or standard | Raised only when necessary | Card padding | Explicit user action group. | Do not make BUY globally dominant over WAIT/SKIP. |
| Feedback surface | `--color-surface-feedback` plus semantic subtle role | Semantic border | Standard | None/low | Compact or standard padding | Loading, processing, success, warning, error, retry. | Do not represent a feedback state as a business status. |

Avoid excessive cards inside cards. A nested surface must explain a real relationship, such as a compact metadata inset inside a factual summary, not simply add decoration.

## 10. Border, Radius, and Elevation System

| Role | Token/value | Use |
| --- | --- | --- |
| Standard border | `--color-border-default` | Controls, standard surfaces, quiet divisions. |
| Emphasized border | `--color-border-strong` | Confirmed facts, active grouping, stronger structure. |
| Compact radius | `--radius-compact` / `0.375rem` | Small controls, metadata chips, compact insets. |
| Standard radius | `--radius-standard` / `0.625rem` | Inputs, buttons, standard cards. |
| Large panel radius | `--radius-large` / `0.875rem` | Primary workspace or major panel. |
| Low elevation | `--elevation-low` | Subtle separation from page canvas. |
| Raised elevation | `--elevation-raised` | Exceptional overlay/primary surface use only. |
| Focus state | `--color-focus-ring`, `--focus-width`, `--focus-offset` | Visible keyboard focus with no layout shift. |

Shadows are soft, restrained, and never the only grouping cue. No decorative shadows, glass effects, gradients, or animation system are introduced by VD-2.

## 11. Button Hierarchy

| Variant | Intended use | Visual hierarchy |
| --- | --- | --- |
| Primary | A clearly selected progression or submit action in its local context | Restrained blue fill; visible text; one or a small number per context. |
| Secondary | Alternative explicit action | Neutral or outlined treatment; equal respect for alternative decisions. |
| Caution | Action requiring attention or waiting context | Warning-toned outline/subtle treatment with explanatory label. |
| Destructive | Confirmation of irreversible/terminal consequence | Danger-toned confirmation treatment; explicit consequence in label/body. |
| Ghost | Low-emphasis navigation or utility action | Minimal treatment; remains keyboard-visible and readable. |
| Link | Inline navigation or secondary reference | Text link with clear hover/focus; not for primary submission. |
| Disabled | Temporarily unavailable action | Reduced emphasis plus text/state explanation where necessary; not merely opacity. |
| Loading | Action currently processing | Preserve action width where possible, show text such as processing/saving, and expose busy state. |

All controls should target a minimum 44px touch height in later migrated screens. Labels remain explicit; icons, when later approved, sit beside text rather than replacing critical action labels. Focus uses the focus-ring tokens. Disabled controls do not receive ordinary interaction and must not imply that a business status changed.

Future decision mapping is contextual: BUY, WAIT, and SKIP are peer user choices after Initial Analysis; WAIT Update and Position Update are explicit forms; retry is a recovery action; CLOSE is a terminal user action. The design system must not prescribe BUY as primary in every lifecycle context.

## 12. Form-Control System

| Control/element | Treatment |
| --- | --- |
| Text input | Standard border/radius, readable body text, full-width by default on mobile, visible focus. |
| Number input | Same control grammar; preserve numeric input affordances and user-owned fact emphasis where confirmed. |
| Textarea | Same border/focus treatment, readable line height, sufficient minimum height, preserve Indonesian notes/newlines. |
| Select | Standard control with explicit label and readable selected value; no color-only required cue. |
| File input/upload trigger | Clear file purpose, accepted type/helper text, selected filename handling, full-width mobile trigger where later migrated. |
| Checkbox/confirmation control | Only where already product-supported; label and consequence remain explicit. No new contract is created. |
| Field label | Strong enough contrast, programmatically associated, placed before the control. |
| Required indicator | Text or symbol with accessible explanation; not color alone. |
| Helper text | Muted but readable text below label/control; supports input authority and format. |
| Validation error | Danger tone plus text, associated with field, announced where appropriate; never only a red border. |
| Disabled state | Reduced interaction and clear disabled state; preserve readable label and avoid excessive opacity. |
| Read-only confirmed fact | Factual summary treatment, not an editable control; preserve user-owned authority. |
| Focus state | Visible ring using `--color-focus-ring`; no removal of browser keyboard visibility. |

Later migrated controls should meet the 44px minimum touch height, avoid horizontal overflow, use `inputMode`/type appropriate to the existing contract, and preserve current field names, requiredness, labels, and lifecycle behavior.

## 13. Status, Feedback, and Empty-State System

| State | Tone/structure | Icon intent | Title/body hierarchy | Action and accessibility guidance |
| --- | --- | --- | --- | --- |
| Loading | Neutral/information surface with short status text | Loading intent | Brief title or live text, then context if needed | Use `aria-live="polite"` where appropriate; no fake business status. |
| Processing | Processing-subtle surface and explicit processing label | Progress intent | State first, expectation second | Announce state changes; do not rely on animation. |
| Success | Success-subtle or neutral terminal surface | Check/complete intent | Confirm completed user/system operation and result | `role="status"` where appropriate; retain history. |
| Warning | Warning-subtle surface | Caution intent | Explain risk/constraint, then next safe action | Text must state the meaning; WAIT is not an error. |
| Failure | Danger-subtle surface | Error intent | Safe error title, concise detail, recovery | `role="alert"` for urgent errors; manual retry remains outside primitive. |
| Manual retry | Feedback surface with explicit retry button | Retry intent | Explain what failed and that retry is manual | Do not implement automated retry in the visual foundation. |
| Empty state | Standard/inset surface with clear absence text | Empty/document intent | State what is absent and what explicit action can create it | Preserve keyboard access and avoid promotional copy. |
| Disabled action | Neutral disabled treatment | Disabled intent | Explain unavailable action where ambiguity exists | Must not look like completed or failed. |
| Completed/terminal | Neutral or success-neutral depending on operation, always labeled | Archive/complete intent | State terminal business status and preserved result | Keep `CLOSED` and `CLOSED_SKIPPED` distinguishable. |

## 14. Advisory Analysis Presentation

Later VD tasks must present Gemini output as advisory. Each analysis group should have a visible advisory label or equivalent structural cue, use the advisory surface role, and remain visually distinct from factual summary surfaces. The treatment must never make Gemini appear to authorize or execute BUY, WAIT, SKIP, Position Update, WAIT Update, or CLOSE.

Long-form Indonesian output should use the long-form analysis type scale, generous line height, readable width, paragraph/list preservation, clear section headings, and stable ordering. Probability and risk should be labeled as analysis output, not as guarantees. Trading-plan content should remain advisory and visually separated from confirmed entry/stop/target facts. User-owned facts must remain separately labeled and must not be overwritten or visually subordinated.

The thirteen Initial Analysis fields are not redesigned or migrated in VD-2.

## 15. Responsive Foundations

| Viewport category | Foundation rules |
| --- | --- |
| Narrow mobile, approximately 360–390px | Use 1rem gutters, body/analysis line heights, full-width controls, 44px touch targets, wrapping-safe labels/filenames, and no horizontal scrolling. |
| Wider mobile, approximately 414–430px | Retain mobile gutters and full-width action/form defaults; allow more breathing room without introducing a second competing hierarchy. |
| Tablet, approximately 768px | Increase gutters to 1.5rem; permit carefully considered field grouping only when labels and values remain readable; preserve vertical chronology. |
| Desktop, approximately 1280–1440px | Use up to 2rem gutters and the 72rem application maximum; readable analysis remains capped at 42rem. |

Across viewports: long text wraps at words, filenames break safely, controls do not overflow, action groups may wrap, and information density is reduced through spacing/typography discipline rather than hidden product facts. Sticky actions are eligible for future task consideration only when they do not obscure chronology or create an automatic-action impression. Workspace columns and final responsive behavior remain owned by VD-3 and VD-6; no responsive screen changes are implemented here.

## 16. Accessibility Foundations

- Target WCAG 2.2 AA intent for future migrated surfaces; this document does not claim formal compliance.
- Normal text and UI text should meet at least 4.5:1 contrast where applicable; large text should meet at least 3:1. Validate actual pairings during later implementation.
- Keyboard focus must be visible with the focus-ring tokens and must not depend on hover.
- Status, decision, authority, feedback, and lifecycle meaning must not rely on color alone; visible text and structure are required.
- Interactive targets should be at least 44px high/wide where practical on touch surfaces.
- Use semantic HTML: headings in order, buttons for actions, links for navigation, lists/definition lists for grouped facts, and sections with meaningful labels.
- Every form control requires an associated label; helper/error text must be programmatically associated when later migrated.
- Errors should use an appropriate alert/status pattern and identify the affected action or field.
- Loading/processing changes should use polite live announcements where appropriate; urgent errors may use alert semantics.
- Later motion must respect `prefers-reduced-motion`; VD-2 introduces only duration/easing tokens and no animation.
- Indonesian copy should remain readable with generous line height and approximately 42rem maximum line length for long analysis.

## 17. CSS Token Contract

All tokens below are introduced in `frontend/src/app/globals.css` under `:root`. They are semantic contracts for later VD tasks, not evidence that current screens consume them.

| Variable | Value | Semantic purpose | Expected consumers | Prohibited direct interpretation |
| --- | --- | --- | --- | --- |
| `--color-page-background` | `#f5f7fa` | Page canvas | Root/page shells | Not a status color. |
| `--color-elevated-background` | `#ffffff` | Elevated shell surface | Primary workspace surfaces | Not success. |
| `--color-surface-standard` | `#ffffff` | Standard content | Sections/cards | Do not imply authority by white alone. |
| `--color-surface-muted` | `#eef2f6` | Inset/low-priority surface | Metadata/helpers | Not disabled or error by itself. |
| `--color-surface-factual` | `#f7fafc` | User-owned facts | Fact summaries | Not Gemini output. |
| `--color-surface-advisory` | `#f4f8ff` | Gemini advisory output | Analysis sections | Not execution confirmation. |
| `--color-surface-action` | `#ffffff` | Explicit action grouping | Action panels | Not a decision recommendation. |
| `--color-surface-feedback` | `#ffffff` | Feedback base | Banners/states | Not a status by itself. |
| `--color-text-strong` | `#172033` | Strong headings/facts | Headings, values | Not a semantic outcome. |
| `--color-text-default` | `#334155` | Body text | UI and analysis | Not a status by itself. |
| `--color-text-muted` | `#64748b` | Metadata/helper text | Secondary content | Not for critical copy. |
| `--color-text-inverse` | `#ffffff` | Text on dark controls | Buttons | Only after contrast verification. |
| `--color-border-default` | `#d8e0ea` | Standard border | Controls/surfaces | Not the only semantic cue. |
| `--color-border-strong` | `#b8c5d4` | Emphasized border | Facts/focus-adjacent grouping | Not alarm. |
| `--color-action-primary` | `#2563a9` | Primary interaction | Contextual primary actions | Not universally BUY. |
| `--color-action-primary-hover` | `#1d4f87` | Hover interaction | Primary controls | Not a status. |
| `--color-action-primary-active` | `#163d69` | Pressed interaction | Primary controls | Not lifecycle meaning. |
| `--color-action-primary-subtle` | `#e8f1fb` | Subtle primary context | Active/selected context | Not completed. |
| `--color-focus-ring` | `#2f80c9` | Keyboard focus | All interactive controls | Not hover-only decoration. |
| `--color-status-success` | `#18794e` | Positive completion | Feedback/status | Not BUY or profit. |
| `--color-status-success-subtle` | `#e9f7ef` | Success background | Feedback/status | Not an open position. |
| `--color-status-warning` | `#9a6700` | Caution | Warning/status | Not WAIT failure. |
| `--color-status-warning-subtle` | `#fff7df` | Warning background | Warning/status | Not every amber action. |
| `--color-status-danger` | `#b42318` | Error/destructive confirmation | Errors/CLOSE confirmation | Not SKIP automatically. |
| `--color-status-danger-subtle` | `#fff0ee` | Danger background | Errors/destructive confirmation | Not business failure. |
| `--color-status-information` | `#235c9f` | Information/advisory cue | Info/status/advisory | Not Gemini execution. |
| `--color-status-information-subtle` | `#eaf3ff` | Information background | Info/status | Not fact authority. |
| `--color-status-processing` | `#5b4bb7` | Processing cue | Processing states | Not a business status. |
| `--color-status-processing-subtle` | `#f0edff` | Processing background | Processing states | Not success/failure. |
| `--font-family-sans` | Existing system stack | Local typography | Application text | No external font implication. |
| `--text-size-application-title` | `1.125rem` | Shell identity | Header/brand | Not a component mandate. |
| `--text-size-page-title` | `1.875rem` | Page heading | Page titles | Not every heading. |
| `--text-size-section-title` | `1.25rem` | Major section heading | Sections | Not a status. |
| `--text-size-card-title` | `1rem` | Surface heading | Cards | Not an authority cue. |
| `--text-size-body` | `1rem` | General reading | Body/facts | Not compact metadata. |
| `--text-size-compact-body` | `0.875rem` | Compact reading | Secondary UI | Not critical small print. |
| `--text-size-label` | `0.875rem` | Labels | Forms/facts | Not body copy. |
| `--text-size-metadata` | `0.75rem` | Metadata | Timestamps | Not required instructions. |
| `--text-size-metric` | `1.5rem` | Metric emphasis | Numeric facts | Not a recommendation. |
| `--text-size-ticker` | `0.875rem` | Ticker identifier | Session header | Not generic metadata. |
| `--text-size-status` | `0.75rem` | Status label | Badges | Must include visible text. |
| `--text-size-button` | `0.875rem` | Button label | Controls | Not icon-only. |
| `--text-size-analysis` | `0.9375rem` | Long-form advisory | Gemini output | Not fact authority. |
| `--text-line-body` | `1.5` | Body readability | Body/facts | Not heading rhythm. |
| `--text-line-compact` | `1.4` | Compact readability | Labels/metadata | Not long analysis. |
| `--text-line-heading` | `1.2` | Heading rhythm | Titles | Not body copy. |
| `--text-line-analysis` | `1.7` | Indonesian analysis readability | Gemini output | Not dense metadata. |
| `--space-unit` | `0.25rem` | Base rhythm | All spacing | Not a screen layout. |
| `--space-1`, `--space-2`, `--space-3`, `--space-4`, `--space-5`, `--space-6`, `--space-8`, `--space-10`, `--space-12` | `0.25rem`–`3rem` scale | Shared spacing scale | Later components | Do not infer lifecycle meaning. |
| `--space-section` | `1.5rem` | Major section gap | Sections | Not current layout migration. |
| `--space-card` | `1.25rem` | Standard surface padding | Surfaces | Not required for every card. |
| `--space-card-compact` | `0.75rem` | Compact surface padding | Insets/metadata | Not dense by default. |
| `--space-field` | `0.75rem` | Field rhythm | Forms | Does not alter current contracts. |
| `--space-action` | `0.5rem` | Action grouping | Buttons | Does not prioritize BUY. |
| `--layout-gutter-mobile` | `1rem` | Mobile page gutter | Later responsive surfaces | Not a workspace column. |
| `--layout-gutter-tablet` | `1.5rem` | Tablet page gutter | Later responsive surfaces | Not a breakpoint declaration. |
| `--layout-gutter-desktop` | `2rem` | Desktop page gutter | Later responsive surfaces | Not a workspace redesign. |
| `--layout-text-readable` | `42rem` | Maximum readable text | Long analysis | Not a hard component width. |
| `--layout-application-max` | `72rem` | App canvas maximum | Shell/layout | Not current grid migration. |
| `--radius-compact` | `0.375rem` | Compact geometry | Small controls/insets | Not status meaning. |
| `--radius-standard` | `0.625rem` | Standard geometry | Controls/surfaces | Not a component prescription. |
| `--radius-large` | `0.875rem` | Large panel geometry | Primary panels | Not decorative rounding. |
| `--elevation-low` | `0 1px 2px rgb(23 32 51 / 0.06)` | Subtle separation | Surfaces | Not authority or success. |
| `--elevation-raised` | `0 8px 24px rgb(23 32 51 / 0.08)` | Exceptional raised surface | Future overlays/panels | Not a default for all cards. |
| `--focus-width` | `3px` | Focus ring thickness | Keyboard focus | Not decorative outline. |
| `--focus-offset` | `2px` | Focus ring separation | Keyboard focus | Not spacing scale. |
| `--motion-duration-standard` | `160ms` | Future restrained motion | Later transitions | Must respect reduced motion. |
| `--motion-easing-standard` | `ease-out` | Future restrained motion | Later transitions | No animation is introduced here. |

## 18. Optional Primitive Contract

No optional primitives were created. `frontend/src/components/ui/` remains untouched. This keeps VD-2 foundational and avoids introducing an abstraction before VD-3/VD-5 establish the active component consumers. No existing screen was migrated in VD-2.

## 19. VD-1 Finding Coverage

| VD-1 finding | VD-2 disposition | Design-system decision |
| --- | --- | --- |
| VD1-F01 — Ambiguous component ownership | `DEFERRED TO VD-3` | The token foundation does not determine route ownership. VD-3 must verify the active Trade Workspace route before migration; legacy families are not deleted. |
| VD1-F02 — Decision hierarchy is asymmetric | `DEFERRED TO VD-3` | Button roles and peer-decision guidance are documented; existing decision UI is not migrated. |
| VD1-F03 — Long vertical information stack | `DEFERRED TO VD-6` | Readable width, spacing, wrapping, and touch foundations are defined; screen density remains unchanged until responsive/layout tasks. |
| VD1-F04 — Status styling is neutral and inconsistent | `ADDRESSED BY VD-2 FOUNDATION` | Semantic lifecycle roles, tones, labels, and non-color cues are defined without changing current badges. |
| VD1-F05 — No shared visual primitives or tokens | `ADDRESSED BY VD-2 FOUNDATION` | Semantic CSS custom properties are now available in `globals.css`; no component migration is performed. |
| VD1-F06 — Advisory output is not visibly separated from user facts | `ADDRESSED BY VD-2 FOUNDATION` | Factual and advisory surface/authority rules are documented for later consumption; current output remains unchanged. |
| VD1-F07 — Feedback markup is duplicated | `DEFERRED TO VD-5` | Feedback roles and structure are documented; no current banner or action panel is migrated. |
| VD1-F08 — Icon and typography systems are absent | `ADDRESSED BY VD-2 FOUNDATION` | System typography roles and future icon intent are documented; no icon dependency or library is added. |

“Addressed by foundation” means the design decision/token exists; it does not claim that an existing screen has been visually fixed.

## 20. Behavior-Preservation Guardrails

The following product guardrails are copied from the authoritative PRD and must be preserved by later visual work:

- One session equals one trading story and one possible trade.
- Gemini remains advisory; it may analyze evidence and provide recommendations, but all trading decisions and execution facts belong to the user.
- Facts and decisions remain user-owned and authoritative, including ticker, company, evidence, notes, current price, timestamps, BUY/WAIT/SKIP decisions, position facts, and closure facts.
- BUY, WAIT, SKIP, WAIT Update, Position Update, retry, and CLOSE remain explicit user actions where approved by the PRD.
- WAIT Updates remain distinct from Position Updates.
- Skipped sessions remain distinct from closed trades: `CLOSED_SKIPPED` is not `CLOSED`.
- Complete chronological history remains preserved and readable.
- No automatic execution or automatic BUY, WAIT, SKIP, or CLOSE may be introduced.
- No additional business status may be added. Approved statuses remain `DRAFT`, `ANALYZING`, `ANALYZED`, `WAITING`, `OPEN_POSITION`, `CLOSED`, and `CLOSED_SKIPPED`.
- No additional analysis type may be added. Approved analysis types remain `INITIAL_ANALYSIS`, `WAIT_UPDATE`, and `POSITION_UPDATE`.
- No additional AI provider, provider routing, or fallback may be added. Gemini remains the only AI provider.
- User-facing Gemini analysis remains in Indonesian.

## 21. Future Task Handoff

| Task | Authorized to consume | Not authorized by VD-2 |
| --- | --- | --- |
| VD-3 — Trade Workspace Layout Redesign | Use semantic tokens and direction to redesign the active Trade Workspace layout after route ownership is verified. | Do not add product behavior, statuses, analysis types, or migrate unverified legacy surfaces. |
| VD-4 — Session Header and Timeline Redesign | Use factual/advisory/status treatments and typography to refine header/timeline. | Do not alter chronology, status transitions, or history data. |
| VD-5 — Forms, Evidence Upload, and Action Panels | Use button, form, feedback, surface, and authority contracts. | Do not change field contracts, evidence rules, or explicit action semantics. |
| VD-6 — Responsive and Mobile Refinement | Use gutters, readable widths, touch targets, wrapping, and responsive foundations. | Do not silently remove facts/actions or redesign unrelated routes. |
| VD-7 — Visual Regression and Final Polish | Verify token use, contrast, focus, states, and consistency across migrated screens. | Do not treat tokens as proof that screens are already complete; do not add unapproved dependencies. |

VD-3 may consume the design tokens. Later tasks may migrate only active Trade Workspace components verified from the current route. Parallel legacy component families must not be deleted or migrated without separate ownership verification. The design tokens are foundational, not proof that screens are visually complete.

## 22. VD-2 Acceptance Checklist

- [x] All four Source Lock documents were read directly from the repository.
- [x] The accepted VD-1 baseline was verified.
- [x] One visual direction was documented.
- [x] The direction supports a calm, analytical, trustworthy, mobile-first workspace.
- [x] User-owned facts and Gemini advisory output have distinct documented treatments.
- [x] Semantic color roles were defined without changing product meaning.
- [x] Approved lifecycle statuses were read directly from the PRD and no status was added.
- [x] Typography, spacing, surfaces, borders, radius, elevation, buttons, forms, feedback, and responsive foundations were documented.
- [x] Accessibility foundations were documented without claiming certification.
- [x] Semantic CSS custom properties were added to `globals.css`.
- [x] Existing application behavior was preserved.
- [x] Existing workspace components were not migrated or redesigned.
- [x] No component library, icon library, font package, or other dependency was added.
- [x] No parallel legacy component was deleted or migrated.
- [x] VD-1 findings were mapped honestly to VD-2 or later tasks.
- [x] Exactly one design-system document was created.
- [x] Only explicitly allowed frontend foundation files were changed or created.
- [ ] Frontend lint passed: pre-existing errors remain in `frontend/src/features/evaluation/evaluation-dashboard.tsx`, `frontend/src/features/trade-workspace/polling-loop.test.tsx`, and `frontend/src/features/trade-workspace/workspace.tsx`; no VD-2 allowlisted screen/test file was modified.
- [x] Frontend type verification passed with `npm run typecheck`.
- [x] No real Gemini request was made.
- [x] No runtime record was mutated.
- [x] VD-3 was not started.

## 23. Final VD-2 Result

**PASS WITH DOCUMENTED LIMITATIONS**

The visual direction, semantic design-token contract, and implementation foundation are complete within the authorized scope. Existing screens were intentionally not migrated, so the VD-1 inconsistencies are addressed as system decisions rather than claimed as screen fixes. `git diff --check` and `npm run typecheck` passed. `npm run lint` did not pass because of six pre-existing errors in unrelated existing files; no lint fix was made because those files are outside VD-2 scope.

**VD-3 has not been started.**
