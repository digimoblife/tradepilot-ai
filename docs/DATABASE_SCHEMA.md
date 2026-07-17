# **TradePilot AI — Database Schema Specification**

**Document:** `DATABASE_SCHEMA.md`  
**Version:** 1.0  
**Status:** Final  
**Product Name:** TradePilot AI  
**Database Engine:** PostgreSQL  
**Primary References:** `PRD.md`, `PRODUCT_RULES.md`, `USER_FLOWS.md`, `ARCHITECTURE.md`, `DOMAIN_MODEL.md`, `SESSION_LIFECYCLE.md`  
**Purpose:** Define the logical PostgreSQL schema, tables, columns, relationships, constraints, indexes, versioning strategy, canonical-state representation, and data-integrity requirements.

---

## **1\. Document Purpose**

This document translates the TradePilot AI domain model into a logical PostgreSQL database design.

It defines:

* database conventions;  
* core tables;  
* supporting tables;  
* primary and foreign keys;  
* enum strategy;  
* canonical and historical data separation;  
* append-only records;  
* lifecycle constraints;  
* position accounting;  
* evidence metadata;  
* AI analysis storage;  
* thesis versioning;  
* journal versioning;  
* jobs and usage tracking;  
* timeline and audit records;  
* indexes;  
* deletion and retention rules;  
* migration expectations.

The executable PostgreSQL definition will be provided in:

* `DATABASE_SCHEMA.sql`

This document is the authoritative logical schema. The SQL implementation must remain consistent with it.

---

# **2\. Database Design Principles**

## **2.1 PostgreSQL Is the Source of Truth**

PostgreSQL is authoritative for:

* Trade Session state;  
* lifecycle status;  
* canonical thesis;  
* position state;  
* entries and exits;  
* active stop loss;  
* active targets;  
* evidence metadata;  
* analysis versions;  
* AI jobs;  
* journals;  
* audit history;  
* notifications;  
* AI usage.

Redis must not be the only storage location for business state.

---

## **2.2 Canonical State and Historical Records Are Separate**

The database must support fast access to current state while preserving immutable history.

Examples:

* `trade_sessions.latest_canonical_analysis_id` points to the current analysis;  
* all previous analyses remain in `analysis_versions`;  
* `trade_sessions.active_thesis_id` points to the current thesis;  
* all thesis versions remain in `trading_theses`;  
* `positions.active_stop_loss_id` points to the active stop;  
* all stop versions remain in `stop_loss_versions`.

Canonical references must never cause historical records to be overwritten.

---

## **2.3 Financial Values Use Exact Numeric Types**

Prices, monetary values, quantities, percentages, and estimated costs must use exact decimal types.

Floating-point types must not be used for authoritative financial calculations.

Recommended types:

prices                NUMERIC(20, 6\)  
monetary values       NUMERIC(24, 6\)  
quantities            NUMERIC(24, 6\)  
percentages           NUMERIC(7, 4\)  
probability scores    NUMERIC(7, 4\)  
estimated costs       NUMERIC(20, 8\)

The SQL specification may adjust precision where justified, but it must preserve exact arithmetic.

---

## **2.4 Timestamps Use UTC**

All system timestamps must use:

TIMESTAMPTZ

The application stores timestamps in UTC and displays them using the user’s configured timezone.

Market dates may additionally use:

DATE

---

## **2.5 UUID Primary Keys**

Business tables should use UUID primary keys.

Recommended PostgreSQL type:

UUID

UUID values should be generated server-side or database-side using a supported function.

---

## **2.6 English Database Identifiers**

All table names, column names, enum values, constraints, and index names must use English.

User-facing Indonesian labels belong to the application presentation layer.

---

## **2.7 Soft Deletion and Archiving**

Most business records must not be physically deleted during ordinary use.

Use explicit status fields such as:

* `archived_at`;  
* `excluded_at`;  
* `superseded_at`;  
* `outdated_at`;  
* `deleted_at`, only where a deletion workflow is required.

Physical deletion should be limited to:

* temporary files;  
* expired sessions;  
* operational cleanup;  
* explicit administrative data deletion.

---

# **3\. PostgreSQL Extensions**

Recommended extensions:

pgcrypto  
citext

Possible uses:

* `pgcrypto` for UUID generation and cryptographic helpers;  
* `citext` for case-insensitive email handling.

Optional future extensions:

pg\_trgm

For efficient partial text search.

---

# **4\. Enum Strategy**

## **4.1 Recommended Approach**

Use PostgreSQL native enums for stable, tightly controlled domain values.

Examples:

* session lifecycle status;  
* thesis status;  
* analysis type;  
* position status;  
* job status.

Use text plus check constraints only where values are expected to change frequently.

---

## **4.2 Migration Rule**

Adding enum values must occur through an explicit migration.

Enums must not be changed manually in production.

---

## **4.3 Required Enum Types**

The SQL schema should define at least:

account\_status\_enum  
market\_enum  
session\_status\_enum  
archive\_state\_enum  
update\_classification\_enum  
evidence\_type\_enum  
evidence\_status\_enum  
extraction\_status\_enum  
data\_source\_enum  
data\_quality\_enum  
analysis\_type\_enum  
analysis\_request\_status\_enum  
analysis\_canonical\_status\_enum  
analysis\_validation\_status\_enum  
contradiction\_status\_enum  
thesis\_status\_enum  
thesis\_change\_type\_enum  
directional\_bias\_enum  
price\_level\_type\_enum  
price\_level\_source\_enum  
price\_level\_status\_enum  
position\_status\_enum  
entry\_type\_enum  
entry\_classification\_enum  
exit\_type\_enum  
exit\_reason\_enum  
target\_type\_enum  
target\_status\_enum  
confidence\_classification\_enum  
probability\_type\_enum  
probability\_change\_enum  
uncertainty\_level\_enum  
recommended\_action\_enum  
risk\_level\_enum  
position\_health\_enum  
journal\_status\_enum  
journal\_canonical\_status\_enum  
timeline\_category\_enum  
actor\_type\_enum  
job\_type\_enum  
job\_status\_enum  
job\_progress\_stage\_enum  
provider\_enum  
notification\_type\_enum  
notification\_priority\_enum  
currency\_enum  
quantity\_unit\_enum

---

# **5\. Table Inventory**

The MVP schema must include at least the following tables:

## **5.1 Identity and Settings**

1. `users`  
2. `user_sessions`  
3. `ai_provider_configurations`  
4. `application_settings`

## **5.2 Trade Session Domain**

5. `trade_sessions`  
6. `session_updates`  
7. `market_snapshots`  
8. `context_summaries`

## **5.3 Evidence Domain**

9. `evidence`  
10. `evidence_variants`  
11. `session_update_evidence`

## **5.4 Analysis Domain**

12. `analysis_requests`  
13. `analysis_versions`  
14. `analysis_evidence_links`  
15. `analysis_probability_assessments`

## **5.5 Thesis and Levels**

16. `trading_theses`  
17. `thesis_evidence_links`  
18. `price_levels`

## **5.6 Position Domain**

19. `positions`  
20. `position_entries`  
21. `position_exits`  
22. `stop_loss_versions`  
23. `position_targets`

## **5.7 Journal Domain**

24. `trading_journals`  
25. `user_reflections`

## **5.8 Operations and History**

26. `timeline_events`  
27. `audit_records`  
28. `background_jobs`  
29. `job_attempts`  
30. `outbox_events`  
31. `notifications`  
32. `ai_usage_records`

Additional implementation tables may be added when justified.

---

# **6\. `users`**

## **6.1 Purpose**

Stores authenticated application users.

Although the MVP is designed for one primary user, ownership must remain explicit.

---

## **6.2 Columns**

| Column | Type | Null | Description |
| ----- | ----- | ----- | ----- |
| `id` | UUID | No | Primary key |
| `email` | CITEXT | No | Unique login email |
| `username` | CITEXT | Yes | Optional unique username |
| `password_hash` | TEXT | No | Secure password hash |
| `account_status` | `account_status_enum` | No | Account state |
| `preferred_ui_language` | VARCHAR(10) | No | Defaults to `id-ID` |
| `timezone` | VARCHAR(64) | No | Defaults to `Asia/Jakarta` |
| `last_login_at` | TIMESTAMPTZ | Yes | Last successful login |
| `created_at` | TIMESTAMPTZ | No | Creation time |
| `updated_at` | TIMESTAMPTZ | No | Last update |
| `disabled_at` | TIMESTAMPTZ | Yes | Account disable time |

---

## **6.3 Constraints**

* unique `email`;  
* unique non-null `username`;  
* `preferred_ui_language` must not be empty;  
* `timezone` must not be empty.

---

## **6.4 Indexes**

* unique index on `email`;  
* unique partial index on `username` where not null;  
* index on `account_status`.

---

# **7\. `user_sessions`**

## **7.1 Purpose**

Stores server-managed authentication sessions.

---

## **7.2 Columns**

| Column | Type | Null | Description |
| ----- | ----- | ----- | ----- |
| `id` | UUID | No | Primary key |
| `user_id` | UUID | No | Owner |
| `token_hash` | TEXT | No | Hashed session token |
| `expires_at` | TIMESTAMPTZ | No | Expiry |
| `last_used_at` | TIMESTAMPTZ | Yes | Last activity |
| `created_at` | TIMESTAMPTZ | No | Creation |
| `revoked_at` | TIMESTAMPTZ | Yes | Revocation |
| `ip_address` | INET | Yes | Optional security metadata |
| `user_agent` | TEXT | Yes | Optional security metadata |

---

## **7.3 Constraints**

* foreign key to `users`;  
* unique `token_hash`;  
* `expires_at > created_at`.

---

## **7.4 Deletion Rule**

Deleting a user may cascade to authentication sessions, but business-data deletion requires a separate controlled workflow.

---

# **8\. `trade_sessions`**

## **8.1 Purpose**

Stores the current canonical state and identity of one trade story.

---

## **8.2 Columns**

| Column | Type | Null | Description |
| ----- | ----- | ----- | ----- |
| `id` | UUID | No | Primary key |
| `owner_id` | UUID | No | Owning user |
| `ticker` | VARCHAR(32) | No | Normalized ticker |
| `company_name` | VARCHAR(255) | Yes | Company name |
| `market` | `market_enum` | No | Market |
| `currency` | `currency_enum` | No | Trading currency |
| `title` | VARCHAR(255) | Yes | Session title |
| `initial_note` | TEXT | Yes | Initial note |
| `lifecycle_status` | `session_status_enum` | No | Current visible state |
| `stable_status` | `session_status_enum` | No | Underlying stable state |
| `pre_archive_status` | `session_status_enum` | Yes | State before archive |
| `active_thesis_id` | UUID | Yes | Canonical thesis |
| `active_position_id` | UUID | Yes | Active or historical position |
| `latest_canonical_analysis_id` | UUID | Yes | Latest canonical analysis |
| `canonical_context_summary_id` | UUID | Yes | Current context summary |
| `latest_update_id` | UUID | Yes | Latest session update |
| `latest_confidence_score` | NUMERIC(7,4) | Yes | Dashboard cache |
| `latest_target_probability` | NUMERIC(7,4) | Yes | Dashboard cache |
| `latest_thesis_status` | `thesis_status_enum` | Yes | Dashboard cache |
| `latest_risk_level` | `risk_level_enum` | Yes | Dashboard cache |
| `latest_recommended_action` | `recommended_action_enum` | Yes | Dashboard cache |
| `latest_market_price` | NUMERIC(20,6) | Yes | Latest known price |
| `last_evidence_at` | TIMESTAMPTZ | Yes | Latest evidence |
| `last_analysis_at` | TIMESTAMPTZ | Yes | Latest valid analysis |
| `last_position_event_at` | TIMESTAMPTZ | Yes | Latest position mutation |
| `created_at` | TIMESTAMPTZ | No | Creation |
| `updated_at` | TIMESTAMPTZ | No | Last update |
| `closed_at` | TIMESTAMPTZ | Yes | Business closure |
| `cancelled_at` | TIMESTAMPTZ | Yes | Cancellation |
| `archived_at` | TIMESTAMPTZ | Yes | Archive timestamp |
| `version` | BIGINT | No | Optimistic-lock version |

---

## **8.3 Constraints**

### **Session Identity**

* `ticker` must not be empty;  
* `market` must be valid;  
* `currency` must be valid.

### **Confidence and Probability**

0 \<= latest\_confidence\_score \<= 100  
0 \<= latest\_target\_probability \<= 100

### **Stable Status**

`stable_status` must not be:

* `ANALYZING`;  
* `ARCHIVED`.

### **Archive State**

When `lifecycle_status = ARCHIVED`:

* `pre_archive_status` must not be null;  
* `archived_at` must not be null.

When not archived:

* `pre_archive_status` should normally be null.

### **Closure State**

When lifecycle status is a closed state:

* `closed_at` must not be null;  
* `active_position_id` must not be null.

When lifecycle status is `CANCELLED`:

* `cancelled_at` must not be null;  
* no position may exist.

Some cross-table constraints require transaction-level domain validation or deferred triggers.

---

## **8.4 Foreign Keys**

Deferred foreign keys may be needed because canonical references point to tables that also reference the session.

References:

* `owner_id → users.id`  
* `active_thesis_id → trading_theses.id`  
* `active_position_id → positions.id`  
* `latest_canonical_analysis_id → analysis_versions.id`  
* `canonical_context_summary_id → context_summaries.id`  
* `latest_update_id → session_updates.id`

Canonical-reference foreign keys should use:

ON DELETE RESTRICT

or `SET NULL` only for exceptional administrative deletion.

---

## **8.5 Indexes**

Required indexes:

(owner\_id, lifecycle\_status)  
(owner\_id, stable\_status)  
(owner\_id, ticker)  
(owner\_id, archived\_at)  
(owner\_id, latest\_thesis\_status)  
(owner\_id, last\_analysis\_at DESC)  
(owner\_id, updated\_at DESC)

Recommended partial indexes:

* active position sessions;  
* watching sessions;  
* closed sessions;  
* sessions requiring update;  
* non-archived sessions.

---

# **9\. `session_updates`**

## **9.1 Purpose**

Groups evidence and market data into one chronological observation point.

---

## **9.2 Columns**

| Column | Type | Null | Description |
| ----- | ----- | ----- | ----- |
| `id` | UUID | No | Primary key |
| `session_id` | UUID | No | Parent session |
| `classification` | `update_classification_enum` | No | Update type |
| `custom_label` | VARCHAR(255) | Yes | Required for custom |
| `trading_date` | DATE | Yes | Market date |
| `market_timestamp` | TIMESTAMPTZ | Yes | Observation time |
| `user_note` | TEXT | Yes | User context |
| `market_snapshot_id` | UUID | Yes | Structured market values |
| `created_by` | UUID | No | User |
| `created_at` | TIMESTAMPTZ | No | Creation |
| `analysis_requested_at` | TIMESTAMPTZ | Yes | Request time |
| `version` | BIGINT | No | Optimistic locking |

---

## **9.3 Constraints**

* `CUSTOM` requires `custom_label`;  
* `INITIAL` must occur at most once per session;  
* `created_by` must own or be authorized for the session.

Recommended unique partial index:

UNIQUE(session\_id)  
WHERE classification \= 'INITIAL'

---

## **9.4 Indexes**

(session\_id, created\_at DESC)  
(session\_id, trading\_date DESC)  
(session\_id, classification, created\_at DESC)

---

# **10\. `market_snapshots`**

## **10.1 Purpose**

Stores structured market data associated with a session update.

---

## **10.2 Columns**

| Column | Type | Null |
| ----- | ----- | ----- |
| `id` | UUID | No |
| `session_id` | UUID | No |
| `session_update_id` | UUID | Yes |
| `open_price` | NUMERIC(20,6) | Yes |
| `high_price` | NUMERIC(20,6) | Yes |
| `low_price` | NUMERIC(20,6) | Yes |
| `last_price` | NUMERIC(20,6) | Yes |
| `close_price` | NUMERIC(20,6) | Yes |
| `previous_close` | NUMERIC(20,6) | Yes |
| `average_price` | NUMERIC(20,6) | Yes |
| `absolute_change` | NUMERIC(20,6) | Yes |
| `percentage_change` | NUMERIC(10,6) | Yes |
| `volume` | NUMERIC(24,6) | Yes |
| `transaction_value` | NUMERIC(24,6) | Yes |
| `best_bid` | NUMERIC(20,6) | Yes |
| `best_offer` | NUMERIC(20,6) | Yes |
| `bid_quantity` | NUMERIC(24,6) | Yes |
| `offer_quantity` | NUMERIC(24,6) | Yes |
| `observed_at` | TIMESTAMPTZ | Yes |
| `data_source` | `data_source_enum` | No |
| `data_quality` | `data_quality_enum` | No |
| `source_evidence_id` | UUID | Yes |
| `created_at` | TIMESTAMPTZ | No |

---

## **10.3 Constraints**

* all prices must be positive when present;  
* volume and transaction values must be non-negative;  
* high price should not be below low price when both are available;  
* unknown values remain null;  
* extracted data must retain evidence source where applicable.

---

# **11\. `evidence`**

## **11.1 Purpose**

Stores metadata for screenshots, notes, and structured evidence.

---

## **11.2 Columns**

| Column | Type | Null |
| ----- | ----- | ----- |
| `id` | UUID | No |
| `session_id` | UUID | No |
| `owner_id` | UUID | No |
| `evidence_type` | `evidence_type_enum` | No |
| `evidence_status` | `evidence_status_enum` | No |
| `update_classification` | `update_classification_enum` | Yes |
| `original_filename` | TEXT | Yes |
| `storage_object_key` | TEXT | Yes |
| `mime_type` | VARCHAR(255) | Yes |
| `file_size_bytes` | BIGINT | Yes |
| `checksum_sha256` | CHAR(64) | Yes |
| `market_timestamp` | TIMESTAMPTZ | Yes |
| `caption` | TEXT | Yes |
| `source_note` | TEXT | Yes |
| `text_content` | TEXT | Yes |
| `extraction_status` | `extraction_status_enum` | No |
| `extraction_payload` | JSONB | Yes |
| `extraction_confidence` | NUMERIC(7,4) | Yes |
| `supersedes_evidence_id` | UUID | Yes |
| `exclusion_reason` | TEXT | Yes |
| `excluded_at` | TIMESTAMPTZ | Yes |
| `uploaded_at` | TIMESTAMPTZ | No |
| `created_at` | TIMESTAMPTZ | No |
| `updated_at` | TIMESTAMPTZ | No |
| `deleted_at` | TIMESTAMPTZ | Yes |

---

## **11.3 Constraints**

### **File Evidence**

Image evidence must normally have:

* `storage_object_key`;  
* `mime_type`;  
* `file_size_bytes`;  
* checksum.

### **Text Evidence**

`USER_NOTE` may use `text_content` without a file.

### **Confidence**

0 \<= extraction\_confidence \<= 100

### **Excluded Evidence**

When status is `EXCLUDED`:

* `exclusion_reason` must be present;  
* `excluded_at` must be present.

### **Superseded Evidence**

When status is `SUPERSEDED`:

* it should be referenced by a replacement or have a supersession explanation.

---

## **11.4 Indexes**

(session\_id, uploaded\_at DESC)  
(session\_id, evidence\_type, evidence\_status)  
(owner\_id, checksum\_sha256)  
(session\_id, market\_timestamp DESC)

Recommended unique or duplicate-detection index:

(session\_id, checksum\_sha256)  
WHERE checksum\_sha256 IS NOT NULL  
AND deleted\_at IS NULL

This may remain non-unique if the user is allowed to retain timestamped duplicates.

---

# **12\. `evidence_variants`**

## **12.1 Purpose**

Stores generated file variants.

---

## **12.2 Columns**

| Column | Type | Null |
| ----- | ----- | ----- |
| `id` | UUID | No |
| `evidence_id` | UUID | No |
| `variant_type` | VARCHAR(32) | No |
| `storage_object_key` | TEXT | No |
| `mime_type` | VARCHAR(255) | No |
| `file_size_bytes` | BIGINT | No |
| `width` | INTEGER | Yes |
| `height` | INTEGER | Yes |
| `checksum_sha256` | CHAR(64) | Yes |
| `created_at` | TIMESTAMPTZ | No |

---

## **12.3 Constraints**

Unique:

(evidence\_id, variant\_type)

unless multiple processing versions are intentionally supported.

---

# **13\. `session_update_evidence`**

## **13.1 Purpose**

Many-to-many link between Session Updates and Evidence.

---

## **13.2 Columns**

| Column | Type | Null |
| ----- | ----- | ----- |
| `session_update_id` | UUID | No |
| `evidence_id` | UUID | No |
| `display_order` | INTEGER | No |
| `created_at` | TIMESTAMPTZ | No |

---

## **13.3 Primary Key**

Composite:

(session\_update\_id, evidence\_id)

---

## **13.4 Constraint**

The update and evidence must belong to the same Trade Session.

This may require application validation or a database trigger.

---

# **14\. `analysis_requests`**

## **14.1 Purpose**

Stores one logical request for AI processing.

---

## **14.2 Columns**

| Column | Type | Null |
| ----- | ----- | ----- |
| `id` | UUID | No |
| `session_id` | UUID | No |
| `session_update_id` | UUID | Yes |
| `requested_by` | UUID | No |
| `analysis_type` | `analysis_type_enum` | No |
| `request_status` | `analysis_request_status_enum` | No |
| `idempotency_key` | VARCHAR(255) | No |
| `requested_provider` | `provider_enum` | Yes |
| `requested_model` | VARCHAR(255) | Yes |
| `fallback_allowed` | BOOLEAN | No |
| `prompt_name` | VARCHAR(255) | No |
| `prompt_version` | VARCHAR(64) | No |
| `schema_version` | VARCHAR(64) | No |
| `context_summary_version` | INTEGER | Yes |
| `session_version_snapshot` | BIGINT | No |
| `position_version_snapshot` | BIGINT | Yes |
| `created_at` | TIMESTAMPTZ | No |
| `queued_at` | TIMESTAMPTZ | Yes |
| `started_at` | TIMESTAMPTZ | Yes |
| `completed_at` | TIMESTAMPTZ | Yes |
| `failed_at` | TIMESTAMPTZ | Yes |
| `cancelled_at` | TIMESTAMPTZ | Yes |

---

## **14.3 Constraints**

Unique:

idempotency\_key

or unique within the user/application scope.

The request state timestamps must be consistent with status.

---

## **14.4 Indexes**

(session\_id, created\_at DESC)  
(session\_id, request\_status)  
(idempotency\_key)

Partial index for active requests:

(session\_id, analysis\_type)  
WHERE request\_status IN ('QUEUED', 'PROCESSING')

---

# **15\. `analysis_versions`**

## **15.1 Purpose**

Stores immutable normalized AI analysis results.

---

## **15.2 Columns**

| Column | Type | Null |
| ----- | ----- | ----- |
| `id` | UUID | No |
| `session_id` | UUID | No |
| `analysis_request_id` | UUID | No |
| `analysis_type` | `analysis_type_enum` | No |
| `version_number` | INTEGER | No |
| `canonical_status` | `analysis_canonical_status_enum` | No |
| `validation_status` | `analysis_validation_status_enum` | No |
| `provider` | `provider_enum` | No |
| `model` | VARCHAR(255) | No |
| `provider_request_id` | TEXT | Yes |
| `prompt_name` | VARCHAR(255) | No |
| `prompt_version` | VARCHAR(64) | No |
| `schema_version` | VARCHAR(64) | No |
| `context_summary_version` | INTEGER | Yes |
| `session_status_snapshot` | `session_status_enum` | No |
| `session_version_snapshot` | BIGINT | No |
| `position_version_snapshot` | BIGINT | Yes |
| `position_snapshot` | JSONB | Yes |
| `structured_payload` | JSONB | No |
| `narrative_language` | VARCHAR(16) | No |
| `contradiction_status` | `contradiction_status_enum` | No |
| `contradiction_details` | JSONB | Yes |
| `generated_at` | TIMESTAMPTZ | No |
| `validated_at` | TIMESTAMPTZ | Yes |
| `canonicalized_at` | TIMESTAMPTZ | Yes |
| `created_at` | TIMESTAMPTZ | No |

---

## **15.3 Constraints**

Unique:

(session\_id, version\_number)

Potential additional unique constraint:

analysis\_request\_id

when one request produces at most one stored normalized version.

If retries may produce multiple candidate versions, use a separate candidate or attempt relation.

### **Canonical Analysis**

Only one analysis per session may have:

canonical\_status \= CANONICAL

if canonical means latest overall.

However, preserving older analyses as historically canonical at their generation time is important.

Recommended approach:

* completed accepted analyses remain `CANONICAL` as valid historical versions;  
* `trade_sessions.latest_canonical_analysis_id` identifies the current one.

Alternatively, use `ACCEPTED` and `REJECTED` status naming in SQL.

To avoid ambiguity, the SQL implementation should define:

ACCEPTED  
NON\_CANONICAL  
REJECTED  
SUPERSEDED

and use the session pointer for the latest accepted analysis.

The exact enum naming must remain consistent across documents and code.

### **Payload Validation**

`structured_payload` must be a JSON object.

### **Language**

User-facing narrative language should equal:

id

or `id-ID`, according to final convention.

---

## **15.4 Indexes**

(session\_id, version\_number DESC)  
(session\_id, generated\_at DESC)  
(session\_id, analysis\_type, generated\_at DESC)  
(analysis\_request\_id)  
(validation\_status)  
(contradiction\_status)

GIN index on `structured_payload` is optional and should be added only for real query requirements.

---

# **16\. `analysis_evidence_links`**

## **16.1 Purpose**

Records the exact evidence used by an analysis.

---

## **16.2 Columns**

| Column | Type | Null |
| ----- | ----- | ----- |
| `analysis_version_id` | UUID | No |
| `evidence_id` | UUID | No |
| `evidence_role` | VARCHAR(64) | No |
| `context_priority` | INTEGER | Yes |
| `included_as_image` | BOOLEAN | No |
| `included_as_extracted_text` | BOOLEAN | No |
| `created_at` | TIMESTAMPTZ | No |

---

## **16.3 Primary Key**

(analysis\_version\_id, evidence\_id)

---

## **16.4 Constraints**

The analysis and evidence must belong to the same Trade Session.

Historical links must not be deleted merely because evidence later becomes excluded.

---

# **17\. `analysis_probability_assessments`**

## **17.1 Purpose**

Stores queryable probability values from an analysis.

The complete analysis payload remains in JSONB, but key values should also be normalized for comparison and reporting.

---

## **17.2 Columns**

| Column | Type | Null |
| ----- | ----- | ----- |
| `id` | UUID | No |
| `analysis_version_id` | UUID | No |
| `probability_type` | `probability_type_enum` | No |
| `percentage` | NUMERIC(7,4) | No |
| `previous_percentage` | NUMERIC(7,4) | Yes |
| `change_direction` | `probability_change_enum` | No |
| `reasoning` | TEXT | No |
| `supporting_evidence` | JSONB | Yes |
| `uncertainty_level` | `uncertainty_level_enum` | No |
| `created_at` | TIMESTAMPTZ | No |

---

## **17.3 Constraints**

0 \<= percentage \<= 100  
0 \<= previous\_percentage \<= 100

Unique:

(analysis\_version\_id, probability\_type)

---

# **18\. `trading_theses`**

## **18.1 Purpose**

Stores immutable thesis versions.

---

## **18.2 Columns**

| Column | Type | Null |
| ----- | ----- | ----- |
| `id` | UUID | No |
| `session_id` | UUID | No |
| `version_number` | INTEGER | No |
| `thesis_status` | `thesis_status_enum` | No |
| `directional_bias` | `directional_bias_enum` | No |
| `thesis_statement` | TEXT | No |
| `technical_rationale` | TEXT | No |
| `supporting_evidence_summary` | TEXT | Yes |
| `conflicting_evidence_summary` | TEXT | Yes |
| `key_support_level_id` | UUID | Yes |
| `key_resistance_level_id` | UUID | Yes |
| `invalidation_level_id` | UUID | Yes |
| `invalidation_condition` | TEXT | No |
| `expected_scenario` | TEXT | Yes |
| `confidence_score` | NUMERIC(7,4) | No |
| `source_analysis_version_id` | UUID | No |
| `previous_thesis_id` | UUID | Yes |
| `change_type` | `thesis_change_type_enum` | No |
| `change_reason` | TEXT | Yes |
| `effective_at` | TIMESTAMPTZ | No |
| `created_at` | TIMESTAMPTZ | No |

---

## **18.3 Constraints**

Unique:

(session\_id, version\_number)

Confidence:

0 \<= confidence\_score \<= 100

Material thesis changes require `change_reason`.

`previous_thesis_id` must belong to the same session.

---

## **18.4 Indexes**

(session\_id, version\_number DESC)  
(session\_id, thesis\_status, effective\_at DESC)  
(source\_analysis\_version\_id)

---

# **19\. `thesis_evidence_links`**

## **19.1 Purpose**

Links a thesis version to supporting or conflicting evidence.

---

## **19.2 Columns**

| Column | Type | Null |
| ----- | ----- | ----- |
| `thesis_id` | UUID | No |
| `evidence_id` | UUID | No |
| `relationship_type` | VARCHAR(32) | No |
| `created_at` | TIMESTAMPTZ | No |

---

## **19.3 Relationship Types**

Recommended values:

SUPPORTING  
CONFLICTING  
INVALIDATING  
REFERENCE

---

## **19.4 Primary Key**

(thesis\_id, evidence\_id, relationship\_type)

---

# **20\. `price_levels`**

## **20.1 Purpose**

Stores thesis, analysis, stop, target, entry, support, and resistance price levels or zones.

---

## **20.2 Columns**

| Column | Type | Null |
| ----- | ----- | ----- |
| `id` | UUID | No |
| `session_id` | UUID | No |
| `analysis_version_id` | UUID | Yes |
| `thesis_id` | UUID | Yes |
| `exact_price` | NUMERIC(20,6) | Yes |
| `lower_bound` | NUMERIC(20,6) | Yes |
| `upper_bound` | NUMERIC(20,6) | Yes |
| `level_type` | `price_level_type_enum` | No |
| `basis` | TEXT | No |
| `source_type` | `price_level_source_enum` | No |
| `level_status` | `price_level_status_enum` | No |
| `confidence_score` | NUMERIC(7,4) | Yes |
| `observed_at` | TIMESTAMPTZ | Yes |
| `superseded_at` | TIMESTAMPTZ | Yes |
| `created_at` | TIMESTAMPTZ | No |

---

## **20.3 Constraints**

A level must have either:

* `exact_price`; or  
* both `lower_bound` and `upper_bound`.

It must not have an invalid zone:

lower\_bound \<= upper\_bound

All prices must be positive.

---

## **20.4 Indexes**

(session\_id, level\_type, created\_at DESC)  
(analysis\_version\_id)  
(thesis\_id)

---

# **21\. `positions`**

## **21.1 Purpose**

Stores the canonical actual position for one Trade Session.

---

## **21.2 Columns**

| Column | Type | Null |
| ----- | ----- | ----- |
| `id` | UUID | No |
| `session_id` | UUID | No |
| `position_status` | `position_status_enum` | No |
| `currency` | `currency_enum` | No |
| `quantity_unit` | `quantity_unit_enum` | No |
| `total_entry_quantity` | NUMERIC(24,6) | Yes |
| `remaining_quantity` | NUMERIC(24,6) | Yes |
| `weighted_average_entry` | NUMERIC(20,6) | No |
| `total_entry_cost` | NUMERIC(24,6) | Yes |
| `realized_proceeds` | NUMERIC(24,6) | Yes |
| `realized_profit_loss` | NUMERIC(24,6) | Yes |
| `unrealized_profit_loss` | NUMERIC(24,6) | Yes |
| `total_profit_loss` | NUMERIC(24,6) | Yes |
| `return_percentage` | NUMERIC(12,6) | Yes |
| `active_stop_loss_id` | UUID | Yes |
| `opened_at` | TIMESTAMPTZ | No |
| `partially_closed_at` | TIMESTAMPTZ | Yes |
| `closed_at` | TIMESTAMPTZ | Yes |
| `created_at` | TIMESTAMPTZ | No |
| `updated_at` | TIMESTAMPTZ | No |
| `version` | BIGINT | No |

---

## **21.3 Constraints**

Unique:

session\_id

This enforces at most one Position per Trade Session.

### **Quantities**

When present:

total\_entry\_quantity \> 0  
remaining\_quantity \>= 0  
remaining\_quantity \<= total\_entry\_quantity

### **Open Position**

When status is `OPEN` or `PARTIALLY_CLOSED`:

* `active_stop_loss_id` must not be null;  
* remaining quantity must be positive when quantity tracking is enabled.

### **Closed Position**

When status is `CLOSED`:

* `closed_at` must not be null;  
* remaining quantity must be zero when quantity tracking is enabled.

Some rules require deferred triggers because targets are stored in another table.

---

## **21.4 Indexes**

(position\_status)  
(opened\_at DESC)  
(closed\_at DESC)

---

# **22\. `position_entries`**

## **22.1 Purpose**

Stores immutable actual entry transactions.

---

## **22.2 Columns**

| Column | Type | Null |
| ----- | ----- | ----- |
| `id` | UUID | No |
| `position_id` | UUID | No |
| `entry_sequence` | INTEGER | No |
| `entry_type` | `entry_type_enum` | No |
| `entry_classification` | `entry_classification_enum` | Yes |
| `price` | NUMERIC(20,6) | No |
| `quantity` | NUMERIC(24,6) | Yes |
| `gross_value` | NUMERIC(24,6) | Yes |
| `broker_fee` | NUMERIC(24,6) | Yes |
| `net_cost` | NUMERIC(24,6) | Yes |
| `executed_at` | TIMESTAMPTZ | No |
| `user_reason` | TEXT | Yes |
| `related_analysis_version_id` | UUID | Yes |
| `planned_entry_reference` | JSONB | Yes |
| `corrects_entry_id` | UUID | Yes |
| `created_at` | TIMESTAMPTZ | No |

---

## **22.3 Constraints**

Unique:

(position\_id, entry\_sequence)

Only one non-correction initial entry:

UNIQUE(position\_id)  
WHERE entry\_type \= 'INITIAL'

Price must be positive.

Quantity must be positive when provided.

---

# **23\. `position_exits`**

## **23.1 Purpose**

Stores immutable partial and final exit transactions.

---

## **23.2 Columns**

| Column | Type | Null |
| ----- | ----- | ----- |
| `id` | UUID | No |
| `position_id` | UUID | No |
| `exit_sequence` | INTEGER | No |
| `exit_type` | `exit_type_enum` | No |
| `exit_reason` | `exit_reason_enum` | No |
| `price` | NUMERIC(20,6) | No |
| `quantity` | NUMERIC(24,6) | Yes |
| `gross_value` | NUMERIC(24,6) | Yes |
| `broker_fee` | NUMERIC(24,6) | Yes |
| `net_proceeds` | NUMERIC(24,6) | Yes |
| `realized_profit_loss` | NUMERIC(24,6) | Yes |
| `executed_at` | TIMESTAMPTZ | No |
| `user_note` | TEXT | Yes |
| `related_analysis_version_id` | UUID | Yes |
| `active_stop_snapshot` | JSONB | Yes |
| `active_target_snapshot` | JSONB | Yes |
| `corrects_exit_id` | UUID | Yes |
| `created_at` | TIMESTAMPTZ | No |

---

## **23.3 Constraints**

Unique:

(position\_id, exit\_sequence)

At most one active final exit:

UNIQUE(position\_id)  
WHERE exit\_type \= 'FINAL'  
AND corrects\_exit\_id IS NULL

Price must be positive.

Quantity must be positive when provided.

Cross-transaction exit-quantity validation must be handled transactionally.

---

# **24\. `stop_loss_versions`**

## **24.1 Purpose**

Stores user-confirmed stop-loss history.

---

## **24.2 Columns**

| Column | Type | Null |
| ----- | ----- | ----- |
| `id` | UUID | No |
| `position_id` | UUID | No |
| `version_number` | INTEGER | No |
| `price` | NUMERIC(20,6) | No |
| `technical_basis` | TEXT | No |
| `change_reason` | TEXT | Yes |
| `risk_amount` | NUMERIC(24,6) | Yes |
| `risk_percentage` | NUMERIC(12,6) | Yes |
| `is_wider_than_previous` | BOOLEAN | No |
| `recommended_by_analysis_id` | UUID | Yes |
| `confirmed_by_user_id` | UUID | No |
| `effective_from` | TIMESTAMPTZ | No |
| `effective_to` | TIMESTAMPTZ | Yes |
| `is_active` | BOOLEAN | No |
| `created_at` | TIMESTAMPTZ | No |

---

## **24.3 Constraints**

Unique:

(position\_id, version\_number)

Only one active stop:

UNIQUE(position\_id)  
WHERE is\_active \= TRUE

If `is_wider_than_previous = TRUE`, `change_reason` is required.

Price must be positive.

---

# **25\. `position_targets`**

## **25.1 Purpose**

Stores versioned user-confirmed targets.

---

## **25.2 Columns**

| Column | Type | Null |
| ----- | ----- | ----- |
| `id` | UUID | No |
| `position_id` | UUID | No |
| `target_group_id` | UUID | No |
| `version_number` | INTEGER | No |
| `priority` | INTEGER | No |
| `price` | NUMERIC(20,6) | No |
| `target_type` | `target_type_enum` | No |
| `technical_basis` | TEXT | No |
| `planned_quantity` | NUMERIC(24,6) | Yes |
| `planned_percentage` | NUMERIC(7,4) | Yes |
| `target_status` | `target_status_enum` | No |
| `change_reason` | TEXT | Yes |
| `recommended_by_analysis_id` | UUID | Yes |
| `confirmed_by_user_id` | UUID | No |
| `effective_from` | TIMESTAMPTZ | No |
| `effective_to` | TIMESTAMPTZ | Yes |
| `reached_at` | TIMESTAMPTZ | Yes |
| `is_active` | BOOLEAN | No |
| `created_at` | TIMESTAMPTZ | No |

---

## **25.3 Constraints**

Unique:

(position\_id, target\_group\_id, version\_number)

One active version per logical target:

UNIQUE(position\_id, target\_group\_id)  
WHERE is\_active \= TRUE

Price must be positive.

If planned percentage is present:

0 \< planned\_percentage \<= 100

The application must enforce at least one active target for an active position.

---

# **26\. `context_summaries`**

## **26.1 Purpose**

Stores versioned structured summaries for long AI context.

---

## **26.2 Columns**

| Column | Type | Null |
| ----- | ----- | ----- |
| `id` | UUID | No |
| `session_id` | UUID | No |
| `version_number` | INTEGER | No |
| `active_thesis_summary` | JSONB | No |
| `position_summary` | JSONB | Yes |
| `key_level_summary` | JSONB | Yes |
| `update_history_summary` | JSONB | Yes |
| `thesis_change_summary` | JSONB | Yes |
| `current_risks` | JSONB | Yes |
| `unresolved_questions` | JSONB | Yes |
| `latest_plan_summary` | JSONB | Yes |
| `source_analysis_version_ids` | UUID\[\] | Yes |
| `source_timeline_cutoff` | TIMESTAMPTZ | Yes |
| `generated_by_analysis_request_id` | UUID | Yes |
| `generated_at` | TIMESTAMPTZ | No |
| `superseded_at` | TIMESTAMPTZ | Yes |
| `created_at` | TIMESTAMPTZ | No |

---

## **26.3 Constraints**

Unique:

(session\_id, version\_number)

A summary must reference source history sufficiently to remain auditable.

---

# **27\. `trading_journals`**

## **27.1 Purpose**

Stores immutable AI Trading Journal versions.

---

## **27.2 Columns**

| Column | Type | Null |
| ----- | ----- | ----- |
| `id` | UUID | No |
| `session_id` | UUID | No |
| `version_number` | INTEGER | No |
| `journal_status` | `journal_status_enum` | No |
| `canonical_status` | `journal_canonical_status_enum` | No |
| `source_position_version` | BIGINT | No |
| `source_analysis_cutoff` | TIMESTAMPTZ | No |
| `structured_payload` | JSONB | No |
| `narrative_language` | VARCHAR(16) | No |
| `generated_by_analysis_request_id` | UUID | No |
| `generated_at` | TIMESTAMPTZ | No |
| `outdated_at` | TIMESTAMPTZ | Yes |
| `outdated_reason` | TEXT | Yes |
| `created_at` | TIMESTAMPTZ | No |

---

## **27.3 Constraints**

Unique:

(session\_id, version\_number)

Only one current canonical journal per session:

UNIQUE(session\_id)  
WHERE canonical\_status \= 'CANONICAL'

If status is `OUTDATED`:

* `outdated_at` and `outdated_reason` are required.

Narrative language must be Indonesian.

---

# **28\. `user_reflections`**

## **28.1 Purpose**

Stores user-authored post-trade reflections separately from AI journal content.

---

## **28.2 Columns**

| Column | Type | Null |
| ----- | ----- | ----- |
| `id` | UUID | No |
| `session_id` | UUID | No |
| `journal_id` | UUID | Yes |
| `emotional_state` | TEXT | Yes |
| `personal_entry_reason` | TEXT | Yes |
| `personal_exit_reason` | TEXT | Yes |
| `mistakes` | TEXT | Yes |
| `lessons` | TEXT | Yes |
| `trade_rating` | INTEGER | Yes |
| `final_note` | TEXT | Yes |
| `created_at` | TIMESTAMPTZ | No |
| `updated_at` | TIMESTAMPTZ | No |
| `version` | BIGINT | No |

---

## **28.3 Constraints**

Recommended rating range:

1 \<= trade\_rating \<= 10

A session may have one current reflection or multiple versioned reflections. For MVP simplicity, one editable reflection with audit history is acceptable.

---

# **29\. `timeline_events`**

## **29.1 Purpose**

Stores user-visible chronological events.

---

## **29.2 Columns**

| Column | Type | Null |
| ----- | ----- | ----- |
| `id` | UUID | No |
| `session_id` | UUID | No |
| `event_type` | VARCHAR(100) | No |
| `event_category` | `timeline_category_enum` | No |
| `actor_type` | `actor_type_enum` | No |
| `actor_id` | UUID | Yes |
| `title` | TEXT | No |
| `description` | TEXT | Yes |
| `related_entity_type` | VARCHAR(100) | Yes |
| `related_entity_id` | UUID | Yes |
| `change_summary` | JSONB | Yes |
| `occurred_at` | TIMESTAMPTZ | No |
| `created_at` | TIMESTAMPTZ | No |

---

## **29.3 Indexes**

(session\_id, occurred\_at DESC)  
(session\_id, event\_category, occurred\_at DESC)  
(event\_type, occurred\_at DESC)

Timeline records should be append-only.

---

# **30\. `audit_records`**

## **30.1 Purpose**

Stores technical audit history.

---

## **30.2 Columns**

| Column | Type | Null |
| ----- | ----- | ----- |
| `id` | UUID | No |
| `owner_id` | UUID | Yes |
| `session_id` | UUID | Yes |
| `actor_type` | `actor_type_enum` | No |
| `actor_id` | UUID | Yes |
| `action` | VARCHAR(100) | No |
| `entity_type` | VARCHAR(100) | No |
| `entity_id` | UUID | Yes |
| `previous_values` | JSONB | Yes |
| `new_values` | JSONB | Yes |
| `reason` | TEXT | Yes |
| `request_id` | UUID | Yes |
| `correlation_id` | UUID | Yes |
| `job_id` | UUID | Yes |
| `source_ip` | INET | Yes |
| `user_agent` | TEXT | Yes |
| `created_at` | TIMESTAMPTZ | No |

---

## **30.3 Indexes**

(session\_id, created\_at DESC)  
(entity\_type, entity\_id, created\_at DESC)  
(correlation\_id)  
(job\_id)

Audit records must be append-only.

---

# **31\. `background_jobs`**

## **31.1 Purpose**

Stores authoritative background-job state.

---

## **31.2 Columns**

| Column | Type | Null |
| ----- | ----- | ----- |
| `id` | UUID | No |
| `owner_id` | UUID | Yes |
| `session_id` | UUID | Yes |
| `analysis_request_id` | UUID | Yes |
| `job_type` | `job_type_enum` | No |
| `job_status` | `job_status_enum` | No |
| `progress_stage` | `job_progress_stage_enum` | Yes |
| `idempotency_key` | VARCHAR(255) | No |
| `priority` | SMALLINT | No |
| `attempt_count` | INTEGER | No |
| `max_attempts` | INTEGER | No |
| `requested_by` | UUID | Yes |
| `payload_reference` | JSONB | Yes |
| `result_reference` | JSONB | Yes |
| `error_code` | VARCHAR(100) | Yes |
| `error_message` | TEXT | Yes |
| `retryable` | BOOLEAN | No |
| `queued_at` | TIMESTAMPTZ | Yes |
| `started_at` | TIMESTAMPTZ | Yes |
| `heartbeat_at` | TIMESTAMPTZ | Yes |
| `completed_at` | TIMESTAMPTZ | Yes |
| `failed_at` | TIMESTAMPTZ | Yes |
| `cancelled_at` | TIMESTAMPTZ | Yes |
| `created_at` | TIMESTAMPTZ | No |
| `updated_at` | TIMESTAMPTZ | No |

---

## **31.3 Constraints**

Unique:

idempotency\_key

or unique within logical job scope.

attempt\_count \>= 0  
max\_attempts \>= 1  
attempt\_count \<= max\_attempts

State timestamps must be consistent.

---

## **31.4 Indexes**

(job\_status, priority, created\_at)  
(session\_id, created\_at DESC)  
(analysis\_request\_id)  
(idempotency\_key)  
(heartbeat\_at)

---

# **32\. `job_attempts`**

## **32.1 Purpose**

Stores every worker/provider attempt, including fallback attempts.

---

## **32.2 Columns**

| Column | Type | Null |
| ----- | ----- | ----- |
| `id` | UUID | No |
| `job_id` | UUID | No |
| `attempt_number` | INTEGER | No |
| `provider` | `provider_enum` | Yes |
| `model` | VARCHAR(255) | Yes |
| `attempt_status` | VARCHAR(32) | No |
| `provider_request_id` | TEXT | Yes |
| `error_code` | VARCHAR(100) | Yes |
| `error_message` | TEXT | Yes |
| `latency_ms` | BIGINT | Yes |
| `input_tokens` | BIGINT | Yes |
| `output_tokens` | BIGINT | Yes |
| `image_count` | INTEGER | Yes |
| `estimated_cost` | NUMERIC(20,8) | Yes |
| `started_at` | TIMESTAMPTZ | No |
| `completed_at` | TIMESTAMPTZ | Yes |
| `created_at` | TIMESTAMPTZ | No |

---

## **32.3 Constraints**

Unique:

(job\_id, attempt\_number)

Non-negative metrics.

---

# **33\. `outbox_events`**

## **33.1 Purpose**

Supports reliable transactional dispatch to Redis or other asynchronous consumers.

---

## **33.2 Columns**

| Column | Type | Null |
| ----- | ----- | ----- |
| `id` | UUID | No |
| `aggregate_type` | VARCHAR(100) | No |
| `aggregate_id` | UUID | No |
| `event_type` | VARCHAR(100) | No |
| `payload` | JSONB | No |
| `status` | VARCHAR(32) | No |
| `attempt_count` | INTEGER | No |
| `available_at` | TIMESTAMPTZ | No |
| `published_at` | TIMESTAMPTZ | Yes |
| `last_error` | TEXT | Yes |
| `created_at` | TIMESTAMPTZ | No |
| `updated_at` | TIMESTAMPTZ | No |

---

## **33.3 Status Values**

Recommended:

PENDING  
PROCESSING  
PUBLISHED  
FAILED

---

## **33.4 Indexes**

(status, available\_at)  
(aggregate\_type, aggregate\_id)

---

# **34\. `ai_provider_configurations`**

## **34.1 Purpose**

Stores non-secret provider configuration and secure secret references.

---

## **34.2 Columns**

| Column | Type | Null |
| ----- | ----- | ----- |
| `id` | UUID | No |
| `owner_id` | UUID | No |
| `provider` | `provider_enum` | No |
| `model` | VARCHAR(255) | No |
| `is_primary` | BOOLEAN | No |
| `is_fallback` | BOOLEAN | No |
| `enabled` | BOOLEAN | No |
| `supports_vision` | BOOLEAN | No |
| `supports_structured_output` | BOOLEAN | No |
| `supports_long_context` | BOOLEAN | No |
| `encrypted_secret_reference` | TEXT | No |
| `timeout_seconds` | INTEGER | No |
| `max_attempts` | INTEGER | No |
| `temperature` | NUMERIC(5,4) | No |
| `max_output_tokens` | INTEGER | No |
| `last_validation_status` | VARCHAR(32) | Yes |
| `last_validated_at` | TIMESTAMPTZ | Yes |
| `created_at` | TIMESTAMPTZ | No |
| `updated_at` | TIMESTAMPTZ | No |

---

## **34.3 Constraints**

Only one enabled primary provider per user:

UNIQUE(owner\_id)  
WHERE is\_primary \= TRUE  
AND enabled \= TRUE

Only one enabled fallback provider per user may be enforced for MVP.

Temperature must remain within provider-neutral configured bounds.

Secrets must not be stored as plaintext API keys.

---

# **35\. `application_settings`**

## **35.1 Purpose**

Stores user-changeable application settings that are not secrets.

---

## **35.2 Columns**

| Column | Type | Null |
| ----- | ----- | ----- |
| `id` | UUID | No |
| `owner_id` | UUID | No |
| `setting_key` | VARCHAR(100) | No |
| `setting_value` | JSONB | No |
| `created_at` | TIMESTAMPTZ | No |
| `updated_at` | TIMESTAMPTZ | No |

---

## **35.3 Constraint**

Unique:

(owner\_id, setting\_key)

Examples:

* output language;  
* reminder interval;  
* theme;  
* default market;  
* fallback enabled.

---

# **36\. `ai_usage_records`**

## **36.1 Purpose**

Stores provider usage and estimated costs.

---

## **36.2 Columns**

| Column | Type | Null |
| ----- | ----- | ----- |
| `id` | UUID | No |
| `owner_id` | UUID | No |
| `session_id` | UUID | Yes |
| `job_id` | UUID | Yes |
| `job_attempt_id` | UUID | Yes |
| `analysis_version_id` | UUID | Yes |
| `provider` | `provider_enum` | No |
| `model` | VARCHAR(255) | No |
| `request_type` | `analysis_type_enum` | Yes |
| `input_tokens` | BIGINT | Yes |
| `output_tokens` | BIGINT | Yes |
| `image_count` | INTEGER | No |
| `latency_ms` | BIGINT | Yes |
| `estimated_cost` | NUMERIC(20,8) | Yes |
| `cost_currency` | `currency_enum` | Yes |
| `pricing_version` | VARCHAR(64) | Yes |
| `request_status` | VARCHAR(32) | No |
| `recorded_at` | TIMESTAMPTZ | No |

---

## **36.3 Indexes**

(owner\_id, recorded\_at DESC)  
(session\_id, recorded\_at DESC)  
(provider, model, recorded\_at DESC)  
(job\_id)

---

# **37\. `notifications`**

## **37.1 Purpose**

Stores in-app notifications.

---

## **37.2 Columns**

| Column | Type | Null |
| ----- | ----- | ----- |
| `id` | UUID | No |
| `owner_id` | UUID | No |
| `session_id` | UUID | Yes |
| `notification_type` | `notification_type_enum` | No |
| `priority` | `notification_priority_enum` | No |
| `title` | TEXT | No |
| `message` | TEXT | No |
| `related_entity_type` | VARCHAR(100) | Yes |
| `related_entity_id` | UUID | Yes |
| `deduplication_key` | VARCHAR(255) | Yes |
| `read_at` | TIMESTAMPTZ | Yes |
| `dismissed_at` | TIMESTAMPTZ | Yes |
| `created_at` | TIMESTAMPTZ | No |

---

## **37.3 Constraints**

Optional unique partial index:

UNIQUE(owner\_id, deduplication\_key)  
WHERE deduplication\_key IS NOT NULL  
AND dismissed\_at IS NULL

This prevents duplicate active notifications for the same event.

---

# **38\. Foreign Key Deletion Strategy**

## **38.1 User Ownership**

Normal application operations must not physically delete a user.

If administrative deletion is implemented, it must use a coordinated privacy-deletion workflow.

---

## **38.2 Trade Sessions**

Business child tables should generally use:

ON DELETE RESTRICT

or:

ON DELETE CASCADE

only when deleting a Trade Session is an explicit full-data deletion operation.

Ordinary session archiving must not delete rows.

---

## **38.3 Evidence**

Deleting evidence metadata while historical analyses reference it is prohibited in ordinary workflows.

Use status transitions instead.

---

## **38.4 Analyses and Theses**

Historical analyses and theses must use `ON DELETE RESTRICT`.

---

## **38.5 Position Transactions**

Entries, exits, stops, and targets must use `ON DELETE RESTRICT` or controlled cascade from an explicit full-session deletion.

---

# **39\. Canonical Reference Integrity**

## **39.1 Session Canonical Analysis**

`trade_sessions.latest_canonical_analysis_id` must reference an analysis:

* belonging to the same session;  
* valid for canonical use;  
* not rejected.

---

## **39.2 Active Thesis**

`trade_sessions.active_thesis_id` must reference a thesis belonging to the same session.

---

## **39.3 Active Position**

`trade_sessions.active_position_id` must reference the unique Position belonging to the same session.

The name may later be changed to `position_id`, because closed sessions still retain the reference.

---

## **39.4 Active Stop**

`positions.active_stop_loss_id` must reference:

* a stop for the same Position;  
* `is_active = TRUE`.

---

## **39.5 Canonical Context Summary**

The session’s canonical context-summary reference must belong to the same session and represent the latest accepted summary.

---

## **39.6 Enforcement**

Because PostgreSQL foreign keys alone cannot enforce all same-parent conditions, use a combination of:

* composite foreign keys where practical;  
* deferred constraint triggers;  
* transactional application validation;  
* automated consistency tests.

---

# **40\. Required Partial Unique Indexes**

The SQL implementation should provide partial unique indexes for at least:

one initial session update per session  
one position per session  
one initial entry per position  
one final exit per position  
one active stop per position  
one active version per logical target  
one canonical journal per session  
one enabled primary AI provider per user  
one enabled fallback provider per user, if MVP limits it

---

# **41\. Optimistic Locking**

The following canonical mutable tables should include a `version` BIGINT column:

* `trade_sessions`;  
* `positions`;  
* `session_updates`, where concurrent editing matters;  
* `user_reflections`;  
* selected settings tables.

Mutation pattern:

UPDATE positions  
SET ..., version \= version \+ 1  
WHERE id \= :id  
AND version \= :expected\_version

When zero rows are updated, return a concurrency conflict.

---

# **42\. Append-Only Tables**

The following tables should be append-only through normal application APIs:

* `analysis_versions`;  
* `trading_theses`;  
* `position_entries`;  
* `position_exits`;  
* `stop_loss_versions`;  
* `position_targets`;  
* `trading_journals`;  
* `timeline_events`;  
* `audit_records`;  
* `job_attempts`;  
* `ai_usage_records`.

Updates may be allowed only for controlled state fields such as:

* canonical status;  
* outdated status;  
* effective end timestamp;  
* job completion fields.

Core historical values must not be rewritten.

---

# **43\. JSONB Usage Rules**

## **43.1 Appropriate JSONB Uses**

Use JSONB for:

* complete structured AI payloads;  
* evidence extraction results;  
* position snapshots;  
* contradiction details;  
* context summaries;  
* timeline change summaries;  
* audit previous and new values;  
* outbox payloads.

---

## **43.2 Values That Must Be Typed Columns**

Do not keep commonly filtered canonical values only inside JSONB.

Typed columns are required for:

* session status;  
* thesis status;  
* confidence;  
* target probability;  
* risk level;  
* recommended action;  
* analysis type;  
* provider;  
* model;  
* timestamps;  
* position status;  
* average entry;  
* stop loss;  
* target prices;  
* P/L values.

---

## **43.3 JSON Schema Versioning**

Every structured JSON payload must be associated with a schema version.

Existing payloads must remain readable after schema evolution.

---

# **44\. Search Strategy**

## **44.1 Basic Search**

Searchable fields include:

* ticker;  
* company name;  
* session title;  
* initial note;  
* thesis statement;  
* journal narrative;  
* user reflection.

---

## **44.2 MVP Search Implementation**

Use PostgreSQL:

* `ILIKE`;  
* full-text search;  
* optional trigram indexes.

Recommended future generated `tsvector` columns may be added for:

* session content;  
* thesis content;  
* journal content.

---

# **45\. Dashboard Query Optimization**

The session table must contain denormalized current fields needed for dashboard rendering:

* latest thesis status;  
* confidence;  
* target probability;  
* risk;  
* recommended action;  
* latest price;  
* last analysis time.

These values must be updated transactionally when canonical analysis changes.

The detailed source remains:

* analysis version;  
* thesis version;  
* probability assessments;  
* market snapshot.

---

# **46\. Position Calculation Strategy**

## **46.1 Source Transactions**

Authoritative calculations derive from:

* `position_entries`;  
* `position_exits`;  
* broker fees;  
* current price.

---

## **46.2 Cached Position Values**

The `positions` table may cache:

* weighted average entry;  
* total quantity;  
* remaining quantity;  
* realized P/L;  
* unrealized P/L;  
* total P/L;  
* return percentage.

---

## **46.3 Recalculation**

The application must provide a deterministic recalculation service.

Cached values must be recalculable from source transactions.

Historical corrections must trigger recalculation.

---

## **46.4 Quantity-Free Tracking**

When the user omits quantity:

* `weighted_average_entry` remains required;  
* quantity-dependent fields remain null;  
* percentage-based analysis may still be available;  
* absolute P/L remains unavailable.

The schema must not use zero as a substitute.

---

# **47\. Lifecycle Data Integrity**

## **47.1 Draft and Ready**

Before canonical initial analysis:

* lifecycle may be `DRAFT` or `READY_FOR_ANALYSIS`;  
* no Position may exist.

---

## **47.2 Watching**

When `WATCHING`:

* canonical initial analysis must exist;  
* active thesis must exist;  
* no Position may exist.

---

## **47.3 Open Position**

When `OPEN_POSITION`:

* Position must exist;  
* Position status must be `OPEN`;  
* active stop must exist;  
* at least one active target must exist.

---

## **47.4 Partially Closed**

When `PARTIALLY_CLOSED`:

* Position status must be `PARTIALLY_CLOSED`;  
* at least one partial exit must exist;  
* active quantity must remain.

---

## **47.5 Closed**

When a closed session status is used:

* Position status must be `CLOSED`;  
* final exit must exist;  
* closed timestamp must exist.

---

## **47.6 Cancelled**

When `CANCELLED`:

* no Position may exist;  
* cancellation timestamp must exist.

---

## **47.7 Enforcement Strategy**

Complex lifecycle integrity should be enforced through:

1. domain service transaction;  
2. database foreign keys;  
3. check constraints;  
4. deferred constraint triggers for cross-table invariants;  
5. periodic integrity checks;  
6. test coverage.

Avoid placing all business logic in triggers.

---

# **48\. Analysis Canonicalization Transaction**

Canonicalizing an accepted analysis should occur in one transaction.

The transaction may:

1. insert `analysis_versions`;  
2. insert probability assessments;  
3. insert price levels;  
4. insert a new thesis version when applicable;  
5. update `trade_sessions.active_thesis_id`;  
6. update `trade_sessions.latest_canonical_analysis_id`;  
7. update dashboard cache columns;  
8. update last-analysis timestamp;  
9. restore stable session status;  
10. insert timeline events;  
11. insert audit records;  
12. insert notification;  
13. create context-summary outbox event when required.

If the transaction fails, no partial canonical state may remain.

---

# **49\. Position Opening Transaction**

Opening a position must atomically:

1. insert `positions`;  
2. insert initial `position_entries`;  
3. insert active `stop_loss_versions`;  
4. insert one or more `position_targets`;  
5. update `positions.active_stop_loss_id`;  
6. update `trade_sessions.active_position_id`;  
7. update session status to `OPEN_POSITION`;  
8. increment versions;  
9. create timeline event;  
10. create audit record.

---

# **50\. Final Exit Transaction**

Final closure must atomically:

1. lock the Position row;  
2. validate remaining quantity;  
3. insert final `position_exits`;  
4. recalculate the Position;  
5. close the active stop;  
6. update target statuses;  
7. set Position status `CLOSED`;  
8. update session closed status;  
9. set `closed_at`;  
10. create timeline and audit records;  
11. create closing-analysis outbox event.

---

# **51\. Historical Correction Strategy**

Corrections must not silently update historical rows.

Recommended model:

* insert correction transaction referencing original row;  
* mark the original as corrected through reference or status;  
* recalculate canonical Position values;  
* record audit;  
* mark journal outdated;  
* optionally trigger closing-analysis regeneration.

The SQL implementation may include:

corrects\_entry\_id  
corrects\_exit\_id

A correction chain must not become circular.

---

# **52\. Data Retention**

## **52.1 Indefinite Business Retention**

Retain indefinitely by default:

* sessions;  
* evidence metadata;  
* analysis versions;  
* theses;  
* position transactions;  
* journals;  
* timeline;  
* audit records.

---

## **52.2 Temporary Data**

Temporary data eligible for cleanup:

* incomplete upload records;  
* temporary storage objects;  
* expired authentication sessions;  
* old queue progress data;  
* processed outbox records after retention period.

---

## **52.3 Job Records**

Job records should be retained long enough for:

* debugging;  
* cost analysis;  
* audit;  
* AI evaluation.

A configurable retention policy may later archive old operational logs.

---

# **53\. Database Security**

## **53.1 Credentials**

Use separate database users where practical:

* migration role;  
* application role;  
* backup role;  
* read-only reporting role, future.

---

## **53.2 Application Permissions**

The runtime application role should not have permission to:

* create or drop databases;  
* alter schema;  
* manage roles;  
* bypass row ownership logic.

---

## **53.3 Network Access**

PostgreSQL must be reachable only from the private application network.

---

## **53.4 Sensitive Fields**

Sensitive values include:

* password hashes;  
* secret references;  
* IP addresses;  
* user agent metadata;  
* private notes.

Access must be limited and logs must not expose them unnecessarily.

---

# **54\. Migration Rules**

## **54.1 Migration Tool**

Use Alembic.

---

## **54.2 Migration Requirements**

Every schema change must:

* have a migration;  
* support production execution;  
* define rollback where safe;  
* preserve historical AI payloads;  
* preserve enum compatibility;  
* include data migration when needed;  
* be reviewed before deployment.

---

## **54.3 Destructive Changes**

Destructive migrations require:

* backup confirmation;  
* explicit data migration;  
* deployment plan;  
* rollback plan;  
* validation query.

---

## **54.4 Enum Changes**

PostgreSQL enum changes must be handled carefully because removing values is not straightforward.

Prefer additive changes and controlled data migrations.

---

# **55\. Seed and Development Data**

Development seeds should include:

* one active user;  
* draft session;  
* ready session;  
* watching session;  
* open position;  
* partially closed position;  
* weakening thesis;  
* invalidated thesis;  
* closed take-profit session;  
* closed stop-loss session;  
* completed journal;  
* failed analysis job;  
* archived session.

Seed data must not contain real credentials or private production trading data.

---

# **56\. Database Integrity Checks**

Recommended scheduled or administrative checks:

1. sessions with invalid stable statuses;  
2. archived sessions without pre-archive state;  
3. watching sessions without canonical analysis;  
4. open positions without active stop;  
5. active positions without target;  
6. closed positions with positive remaining quantity;  
7. cancelled sessions with a Position;  
8. canonical analysis pointing to another session;  
9. active thesis pointing to another session;  
10. duplicate active stop versions;  
11. duplicate active target versions;  
12. analysis evidence linked across sessions;  
13. journal generated for non-closed session;  
14. orphaned evidence files;  
15. stale processing jobs without heartbeat.

---

# **57\. Recommended Database Views**

The implementation may create read views for common queries.

## **57.1 `active_trade_sessions_view`**

Combines:

* Trade Session;  
* position summary;  
* current thesis;  
* latest analysis;  
* nearest target;  
* active stop.

---

## **57.2 `session_analysis_history_view`**

Provides:

* analysis version;  
* timestamp;  
* thesis status;  
* confidence;  
* target probability;  
* provider;  
* update classification.

---

## **57.3 `position_performance_view`**

Provides:

* entries;  
* exits;  
* average entry;  
* average exit;  
* realized P/L;  
* return;  
* holding duration.

---

## **57.4 `ai_usage_monthly_view`**

Aggregates AI requests and estimated costs.

Views must not replace authoritative tables.

---

# **58\. Database Naming Conventions**

## **58.1 Tables**

Use plural snake\_case:

trade\_sessions  
analysis\_versions  
position\_entries

---

## **58.2 Primary Keys**

Use:

id

---

## **58.3 Foreign Keys**

Use:

\<entity\>\_id

Examples:

session\_id  
position\_id  
analysis\_version\_id

---

## **58.4 Timestamps**

Use:

created\_at  
updated\_at  
opened\_at  
closed\_at  
archived\_at

---

## **58.5 Booleans**

Use positive names:

is\_active  
is\_primary  
fallback\_allowed

Avoid ambiguous negative names.

---

## **58.6 Constraint and Index Names**

Recommended patterns:

pk\_\<table\>  
fk\_\<table\>\_\<column\>  
uq\_\<table\>\_\<columns\>  
ck\_\<table\>\_\<rule\>  
ix\_\<table\>\_\<columns\>

---

# **59\. Database Testing Requirements**

## **59.1 Constraint Tests**

Test:

* duplicate position per session;  
* duplicate active stop;  
* duplicate active target version;  
* invalid confidence;  
* invalid probability;  
* negative quantity;  
* invalid price zone;  
* custom update without label;  
* invalid archive state.

---

## **59.2 Transaction Tests**

Test rollback for:

* position opening;  
* partial exit;  
* final exit;  
* stop change;  
* target change;  
* analysis canonicalization;  
* journal regeneration.

---

## **59.3 Concurrency Tests**

Test:

* optimistic-lock failure;  
* double-click position opening;  
* simultaneous final exits;  
* stop update racing with exit;  
* duplicate analysis requests;  
* duplicate outbox publishing.

---

## **59.4 Query Tests**

Test performance for:

* active dashboard;  
* session timeline;  
* analysis history;  
* evidence gallery;  
* journal search;  
* monthly AI usage.

---

## **59.5 Migration Tests**

Test migrations against:

* empty database;  
* seeded development database;  
* previous production-like schema snapshot.

---

# **60\. Database Acceptance Criteria**

The database design is accepted when:

1. PostgreSQL stores all authoritative business state;  
2. one Trade Session can have at most one Position;  
3. canonical state and history are separated;  
4. analyses and theses are versioned;  
5. analysis evidence is traceable;  
6. entries and exits are append-only;  
7. stop-loss and target changes create versions;  
8. one active stop is enforced;  
9. active target versions are unambiguous;  
10. position calculations are reproducible;  
11. unknown values remain null;  
12. closed sessions cannot contain active quantities;  
13. cancelled sessions cannot contain positions;  
14. AI jobs are persisted independently of Redis;  
15. idempotency keys prevent duplicate logical jobs;  
16. journal versions are preserved;  
17. user reflection remains separate from AI content;  
18. timeline and audit history are retained;  
19. canonical dashboard fields are efficiently queryable;  
20. all business tables use English identifiers;  
21. all timestamps are timezone-aware;  
22. financial values use exact numeric types;  
23. private evidence is stored outside PostgreSQL while metadata remains traceable;  
24. schema changes are migration-controlled;  
25. the logical schema can be implemented cleanly in `DATABASE_SCHEMA.sql`.

---

# **61\. Final Database Statement**

The TradePilot AI PostgreSQL schema must preserve both the current operational state and the complete historical story of every trade.

The database must make it possible to answer:

* what the current session state is;  
* which analysis is currently authoritative;  
* how the thesis changed;  
* which evidence supported each analysis;  
* what the user actually executed;  
* how stop loss and targets changed;  
* why the position was closed;  
* how the final journal was produced.

No critical trading decision or AI conclusion may exist only as temporary UI state, queue data, or unversioned text.

