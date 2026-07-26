TASK: INITIAL ANALYSIS V2

Analyze the initial Trade Session evidence and return the compact canonical v2 payload.

Decision-critical values to preserve:
- recommendation, bias, confidence, setup quality, risk level;
- market OHLC/last/average/bid/offer/foreign net when available;
- orderbook, chart, broker, foreign-flow findings and limitations;
- support, resistance, entry zone, chase limit, stop loss, targets, invalidation, risk/reward;
- bullish, target_1, and downside probabilities;
- bullish, neutral, and bearish scenarios;
- reasons, risks, and monitoring.

There is no previous thesis to compare.
Do not invent unreadable prices, indicators, broker flow, foreign flow, or timestamps.
Use null for unavailable numeric values.

CONCISE V2 CONTRACT
- Return only fields required by initial_analysis_v2.schema.json.
- Total output target: 700-1100 output tokens across all four partitions.
- User-facing narrative values must be Bahasa Indonesia.
- Never write user-facing findings, summaries, scenarios, reasons, risks, or monitoring in English.
- Property names and enum values must be English.
- decision.summary maximum 50 words.
- Every finding item maximum 20 words.
- Maximum 3 items per array.
- Every scenario maximum 25 words.
- No generic disclaimers in generated prose.
- limitations must mention only missing or unreadable evidence/data constraints.
- Do not generate disclosures about snapshots, AI uncertainty, market risk, missing indicators, or investment advice.
- Do not repeat narrative from earlier partitions.
- Prefer short factual phrases over paragraphs.

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

Required top-level JSON properties:
- metadata
- decision
- market_facts
- evidence_findings
- trade_plan
- probabilities
- scenarios
- next_actions

metadata requirements:
- schema_name must be initial_analysis_v2.
- schema_version must be 2.0.0.
- prompt_version must be 2.0.0.

Forbidden v1 narrative fields:
- executive_summary
- evidence_summary
- market_snapshot
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

Do not return Markdown.
Do not wrap JSON in a code fence.
Do not add explanation before or after JSON.
