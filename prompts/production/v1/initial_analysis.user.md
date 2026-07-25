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
- No additional top-level properties are allowed.
- Do not return Markdown.
- Do not wrap JSON in a code fence.
- Do not add explanation before or after JSON.

Required top-level JSON properties (exact names, no extras):
- metadata
- evidence_summary
- market_snapshot
- executive_summary
- orderbook_analysis
- chart_3_month_analysis
- chart_6_month_analysis
- combined_chart_analysis
- price_levels
- entry_plan
- stop_loss_plan
- target_plan
- initial_thesis
- trading_plan
- ai_assessment
- warnings_and_missing_information

Minimal top-level JSON skeleton:
```json
{{
  "metadata": {{}},
  "evidence_summary": {{}},
  "market_snapshot": {{}},
  "executive_summary": {{}},
  "orderbook_analysis": {{}},
  "chart_3_month_analysis": {{}},
  "chart_6_month_analysis": {{}},
  "combined_chart_analysis": {{}},
  "price_levels": {{}},
  "entry_plan": {{}},
  "stop_loss_plan": {{}},
  "target_plan": {{}},
  "initial_thesis": {{}},
  "trading_plan": {{}},
  "ai_assessment": {{}},
  "warnings_and_missing_information": {{}}
}}
```

Forbidden legacy top-level aliases:
- chart_analysis_3m
- chart_analysis_6m
- data_gaps_and_limitations

Nested ai_assessment contract (exact fields, no extras):
- bias
- confidence
- setup_quality
- bullish_probability
- target_probability
- downside_probability
- risk_level
- setup_valid
- summary

ai_assessment enum values:
- bias: STRONGLY_BULLISH | BULLISH | NEUTRAL | BEARISH | STRONGLY_BEARISH | UNCERTAIN
- setup_quality: EXCELLENT | GOOD | FAIR | WEAK | INVALID | UNKNOWN
- risk_level: LOW | MODERATE | HIGH | VERY_HIGH | UNKNOWN

ai_assessment field types:
- confidence: integer 0..100
- bullish_probability: integer 0..100 or null
- target_probability: integer 0..100 or null
- downside_probability: integer 0..100 or null
- setup_valid: boolean
- summary: non-empty Indonesian string

No additional ai_assessment properties are allowed.

Minimal ai_assessment JSON skeleton:
```json
"ai_assessment": {{
  "bias": "NEUTRAL",
  "confidence": 50,
  "setup_quality": "UNKNOWN",
  "bullish_probability": null,
  "target_probability": null,
  "downside_probability": null,
  "risk_level": "UNKNOWN",
  "setup_valid": false,
  "summary": "Ringkasan penilaian AI dalam Bahasa Indonesia."
}}
```

Forbidden legacy ai_assessment fields:
- invalidation_conditions
- next_milestones_to_monitor
