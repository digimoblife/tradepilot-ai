TASK: INITIAL ANALYSIS

Analyze the initial Trade Session evidence and create the first technical thesis.

You must:
1. Summarize available Open, High, Low, Last/Close, Average, bid, and offer data.
2. State which values are verified, extracted, inferred, or unavailable.
3. Analyze the current orderbook snapshot.
4. Analyze the three-month chart.
5. Analyze the six-month chart.
6. Identify support, resistance, invalidation, entry zones, chase limit, stop-loss proposal, and target proposals.
7. Create the initial thesis.
8. Estimate required probabilities with explicit horizons.
9. Calculate analysis confidence using the supplied evidence and context quality.
10. Provide bullish, neutral, and bearish scenarios.
11. State what the user should monitor next.
12. Disclose missing data and limitations.

There is no previous thesis to compare.
Do not invent historical movement that is not visible or provided.
The initial thesis should normally be INTACT. Use UNDER_REVIEW when evidence is materially incomplete or conflicting. Do not create INVALIDATED as the first thesis state.

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
