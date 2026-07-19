TASK: OPEN POSITION UPDATE

Analyze the user's actual current position.

Actual entry, average entry, remaining quantity, active stop, active targets, and recorded exits are authoritative.

You must explicitly answer:
1. What are the current Open, High, Low, Last/Close, and Average values?
2. What is visible in the latest orderbook?
3. What changed from the previous comparable update?
4. Is the position healthy?
5. Is the current thesis still valid?
6. Is each active target still realistic?
7. Is the active stop still technically appropriate?
8. Did target probability increase or decrease?
9. Did pullback probability increase or decrease?
10. Did stop-touch probability increase or decrease?
11. What should the user do until the next checkpoint?
12. Which actions should the user avoid?

Do not replace actual position values with earlier AI proposals.
Do not recommend additional entry when thesis status is INVALIDATED.
When thesis is UNDER_REVIEW, use a defensive posture and explicitly state what confirmation is required.
When recommending a stop, target, partial exit, or full exit change, mark that explicit user confirmation is required.

OPEN POSITION PRIORITY
1. Protect the accuracy of actual execution state.
2. Evaluate thesis validity.
3. Evaluate downside and stop risk.
4. Evaluate target realism.
5. Evaluate upside opportunity.
6. Recommend the next checkpoint plan.

Do not prioritize bullish narrative above risk clarity.

CONTEXT AUTHORITY
Use the following authority order when sources conflict:
1. User-confirmed actual execution records
2. Canonical application state
3. Verified structured market data
4. Current canonical thesis
5. Latest accepted analysis
6. Explicit user-provided facts
7. Reliable evidence extraction
8. AI interpretation
9. Older context summaries

Do not override a higher-authority source with a lower-authority source.

BEGIN_CONTEXT_PACKAGE
{session_identity}
{trade_state_json}
{market_snapshot_json}
{evidence_manifest_json}
{latest_analysis_json}
{user_notes}
END_CONTEXT_PACKAGE

OUTPUT CONTRACT
Return exactly one JSON object matching the provided JSON Schema.

Requirements:
- English property names.
- Exact English enum values.
- Bahasa Indonesia narrative text.
- Use null for unavailable values when allowed by schema.
- Do not omit required fields.
- Do not add properties outside the schema.
- Do not return Markdown.
- Do not wrap JSON in a code fence.
- Do not add explanation before or after JSON.
