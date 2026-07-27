TASK: CLOSING ANALYSIS

Analyze the completed trade session.

Actual entry price, entry timestamp, exit price, exit timestamp, quantity sold, realized return, and holding duration are authoritative and calculated by the application.

You must explicitly evaluate:
1. What was the final factual trade outcome (gain/loss, return percentage, duration)?
2. How accurate was the initial trade thesis?
3. How did the thesis evolve across watching and open position updates?
4. Was entry timing optimal, early, or late?
5. Was exit timing optimal, early, or late?
6. Did the active stop and target levels perform as planned?
7. Which evidence items were most useful vs unhelpful or misleading?
8. Were any warnings or invalidation signals missed during monitoring?
9. What worked well in this trade setup and execution?
10. What failed or needs improvement?
11. What are the key concise lessons for future trades?
12. How did the AI model perform (evaluation label, accuracy, mistakes)?

Do not recommend reopening the trade or starting a new position in this session.
Do not fabricate market data or indicators that were not provided.

CLOSING ANALYSIS PRIORITY
1. Protect the accuracy of actual execution state and calculated outcome metrics.
2. Evaluate thesis validity and evolution.
3. Evaluate entry and exit execution quality.
4. Identify model mistakes, missed warnings, and evidence usefulness.
5. Provide actionable lessons for future trade sessions.

CONTEXT AUTHORITY
Use the following authority order when sources conflict:
1. User-confirmed actual execution records and calculated outcome metrics
2. Canonical application state
3. Verified structured market data
4. Canonical thesis history
5. Latest accepted open position update
6. Latest accepted watching update
7. Accepted initial analysis
8. Explicit user-provided facts and notes
9. AI interpretation
10. Historical same-ticker sessions (secondary context)

Do not override a higher-authority source with a lower-authority source.

BEGIN_CONTEXT_PACKAGE
{session_identity}
{trade_state_json}
{market_snapshot_json}
{evidence_manifest_json}
{latest_analysis_json}
{same_ticker_history_summary_json}
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
