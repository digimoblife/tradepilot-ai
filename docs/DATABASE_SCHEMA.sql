```sql
-- ============================================================================
-- TradePilot AI
-- DATABASE_SCHEMA.sql
-- Version: 1.0
-- Status: Final Baseline Schema
-- Database: PostgreSQL 15+
--
-- Primary references:
-- - PRD.md
-- - PRODUCT_RULES.md
-- - DOMAIN_MODEL.md
-- - SESSION_LIFECYCLE.md
-- - DATABASE_SCHEMA.md
--
-- Notes:
-- 1. All timestamps use TIMESTAMPTZ and must be written in UTC.
-- 2. All financial values use NUMERIC, never floating-point types.
-- 3. User-facing Indonesian content is stored as narrative data.
-- 4. Internal identifiers, enum values, and schema names use English.
-- 5. Evidence binary files are stored outside PostgreSQL.
-- ============================================================================

BEGIN;

-- ============================================================================
-- EXTENSIONS
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;

-- Optional for future fuzzy search:
-- CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================================
-- ENUM TYPES
-- ============================================================================

CREATE TYPE account_status_enum AS ENUM (
    'ACTIVE',
    'LOCKED',
    'DISABLED'
);

CREATE TYPE market_enum AS ENUM (
    'IDX',
    'NASDAQ',
    'NYSE',
    'AMEX',
    'OTHER'
);

CREATE TYPE currency_enum AS ENUM (
    'IDR',
    'USD',
    'OTHER'
);

CREATE TYPE quantity_unit_enum AS ENUM (
    'SHARE',
    'LOT',
    'UNKNOWN'
);

CREATE TYPE session_status_enum AS ENUM (
    'DRAFT',
    'READY_FOR_ANALYSIS',
    'ANALYZING',
    'WATCHING',
    'OPEN_POSITION',
    'PARTIALLY_CLOSED',
    'CLOSED_TAKE_PROFIT',
    'CLOSED_STOP_LOSS',
    'CLOSED_MANUAL',
    'CANCELLED',
    'ARCHIVED'
);

CREATE TYPE update_classification_enum AS ENUM (
    'INITIAL',
    'MORNING',
    'MIDDAY',
    'CLOSING',
    'CUSTOM'
);

CREATE TYPE evidence_type_enum AS ENUM (
    'ORDERBOOK_SCREENSHOT',
    'CHART_THREE_MONTH',
    'CHART_SIX_MONTH',
    'CHART_DAILY',
    'CHART_INTRADAY',
    'BROKER_SUMMARY',
    'FOREIGN_FLOW',
    'NEWS_SCREENSHOT',
    'CUSTOM_IMAGE',
    'USER_NOTE',
    'MARKET_DATA_SNAPSHOT'
);

CREATE TYPE evidence_status_enum AS ENUM (
    'PENDING',
    'AVAILABLE',
    'PROCESSING',
    'UNREADABLE',
    'SUPERSEDED',
    'EXCLUDED',
    'DUPLICATE',
    'FAILED',
    'DELETED'
);

CREATE TYPE extraction_status_enum AS ENUM (
    'NOT_REQUESTED',
    'PENDING',
    'PROCESSING',
    'COMPLETED',
    'PARTIAL',
    'FAILED'
);

CREATE TYPE data_source_enum AS ENUM (
    'USER_PROVIDED',
    'AI_EXTRACTED',
    'SYSTEM_CALCULATED',
    'MARKET_API',
    'UNKNOWN'
);

CREATE TYPE data_quality_enum AS ENUM (
    'VERIFIED',
    'HIGH_CONFIDENCE',
    'MODERATE_CONFIDENCE',
    'LOW_CONFIDENCE',
    'UNREADABLE',
    'UNKNOWN'
);

CREATE TYPE analysis_type_enum AS ENUM (
    'INITIAL_ANALYSIS',
    'WATCHING_UPDATE',
    'OPEN_POSITION_UPDATE',
    'PARTIAL_EXIT_REVIEW',
    'CLOSING_ANALYSIS',
    'TRADING_JOURNAL',
    'CONTEXT_SUMMARY',
    'THESIS_REVIEW'
);

CREATE TYPE analysis_request_status_enum AS ENUM (
    'CREATED',
    'QUEUED',
    'PROCESSING',
    'COMPLETED',
    'FAILED',
    'CANCELLED'
);

CREATE TYPE analysis_canonical_status_enum AS ENUM (
    'PENDING',
    'ACCEPTED',
    'NON_CANONICAL',
    'SUPERSEDED',
    'REJECTED'
);

CREATE TYPE analysis_validation_status_enum AS ENUM (
    'PENDING',
    'VALID',
    'VALID_WITH_WARNINGS',
    'INVALID_SCHEMA',
    'INVALID_LANGUAGE',
    'INVALID_LOGIC',
    'CONTRADICTORY',
    'FAILED'
);

CREATE TYPE contradiction_status_enum AS ENUM (
    'NOT_CHECKED',
    'PASS',
    'PASS_WITH_EXPLANATION',
    'REVIEW_REQUIRED',
    'REJECT'
);

CREATE TYPE thesis_status_enum AS ENUM (
    'STRENGTHENING',
    'INTACT',
    'INTACT_BUT_WEAKENING',
    'UNDER_REVIEW',
    'INVALIDATED'
);

CREATE TYPE thesis_change_type_enum AS ENUM (
    'CREATED',
    'STRENGTHENED',
    'UNCHANGED',
    'WEAKENED',
    'PLACED_UNDER_REVIEW',
    'INVALIDATED',
    'CORRECTED'
);

CREATE TYPE directional_bias_enum AS ENUM (
    'BULLISH',
    'NEUTRAL',
    'BEARISH',
    'MIXED'
);

CREATE TYPE price_level_type_enum AS ENUM (
    'IMMEDIATE_SUPPORT',
    'MAJOR_SUPPORT',
    'THESIS_INVALIDATION',
    'IMMEDIATE_RESISTANCE',
    'MAJOR_RESISTANCE',
    'BREAKOUT_CONFIRMATION',
    'ENTRY_ZONE',
    'CHASE_LIMIT',
    'STOP_LOSS',
    'TARGET'
);

CREATE TYPE price_level_source_enum AS ENUM (
    'ORDERBOOK',
    'CHART_STRUCTURE',
    'SWING_HIGH',
    'SWING_LOW',
    'HISTORICAL_RANGE',
    'AVERAGE_PRICE',
    'VOLUME_ZONE',
    'PSYCHOLOGICAL_LEVEL',
    'USER_DEFINED',
    'AI_INFERRED'
);

CREATE TYPE price_level_status_enum AS ENUM (
    'ACTIVE',
    'BEING_TESTED',
    'BROKEN',
    'CONFIRMED',
    'NO_LONGER_RELEVANT',
    'UNCONFIRMED'
);

CREATE TYPE position_status_enum AS ENUM (
    'OPEN',
    'PARTIALLY_CLOSED',
    'CLOSED'
);

CREATE TYPE entry_type_enum AS ENUM (
    'INITIAL',
    'ADDITIONAL',
    'CORRECTION'
);

CREATE TYPE entry_classification_enum AS ENUM (
    'AVERAGING_UP',
    'AVERAGING_DOWN',
    'NEUTRAL_ADDITION',
    'UNKNOWN'
);

CREATE TYPE exit_type_enum AS ENUM (
    'PARTIAL',
    'FINAL',
    'CORRECTION'
);

CREATE TYPE exit_reason_enum AS ENUM (
    'TAKE_PROFIT',
    'STOP_LOSS',
    'THESIS_INVALIDATED',
    'RISK_REDUCTION',
    'TIME_BASED_EXIT',
    'TRAILING_STOP',
    'MANUAL_DISCRETION',
    'OTHER'
);

CREATE TYPE target_type_enum AS ENUM (
    'TP1',
    'TP2',
    'TP3',
    'CUSTOM'
);

CREATE TYPE target_status_enum AS ENUM (
    'ACTIVE',
    'PARTIALLY_ACHIEVED',
    'ACHIEVED',
    'DEACTIVATED',
    'SUPERSEDED',
    'MISSED'
);

CREATE TYPE confidence_classification_enum AS ENUM (
    'LOW',
    'MODERATE',
    'HIGH'
);

CREATE TYPE probability_type_enum AS ENUM (
    'BULLISH_CONTINUATION',
    'TARGET_ACHIEVEMENT',
    'PULLBACK',
    'STOP_LOSS_TOUCH',
    'THESIS_REMAINS_VALID',
    'THESIS_INVALIDATION',
    'MAJOR_SUPPORT_BREAK'
);

CREATE TYPE probability_change_enum AS ENUM (
    'INCREASED',
    'DECREASED',
    'UNCHANGED',
    'NOT_COMPARABLE'
);

CREATE TYPE uncertainty_level_enum AS ENUM (
    'LOW',
    'MODERATE',
    'HIGH'
);

CREATE TYPE recommended_action_enum AS ENUM (
    'WAIT_FOR_CONFIRMATION',
    'HOLD_POSITION',
    'HOLD_WITH_CAUTION',
    'CONSIDER_PARTIAL_PROFIT',
    'REDUCE_RISK',
    'REVIEW_EXIT',
    'DO_NOT_ADD',
    'CANCEL_SETUP',
    'NO_MATERIAL_CHANGE'
);

CREATE TYPE risk_level_enum AS ENUM (
    'LOW',
    'MODERATE',
    'ELEVATED',
    'HIGH',
    'CRITICAL'
);

CREATE TYPE position_health_enum AS ENUM (
    'HEALTHY',
    'HEALTHY_BUT_VOLATILE',
    'WEAKENING',
    'HIGH_RISK',
    'EXIT_CONDITION_TRIGGERED',
    'NOT_APPLICABLE'
);

CREATE TYPE journal_status_enum AS ENUM (
    'PENDING',
    'GENERATING',
    'COMPLETED',
    'FAILED',
    'OUTDATED'
);

CREATE TYPE journal_canonical_status_enum AS ENUM (
    'CANONICAL',
    'SUPERSEDED',
    'REJECTED'
);

CREATE TYPE timeline_category_enum AS ENUM (
    'SESSION',
    'EVIDENCE',
    'ANALYSIS',
    'THESIS',
    'POSITION',
    'STOP_LOSS',
    'TARGET',
    'EXIT',
    'JOURNAL',
    'SYSTEM'
);

CREATE TYPE actor_type_enum AS ENUM (
    'USER',
    'SYSTEM',
    'AI',
    'WORKER',
    'ADMIN'
);

CREATE TYPE job_type_enum AS ENUM (
    'INITIAL_ANALYSIS',
    'WATCHING_UPDATE_ANALYSIS',
    'OPEN_POSITION_UPDATE_ANALYSIS',
    'PARTIAL_EXIT_REVIEW',
    'CLOSING_ANALYSIS',
    'TRADING_JOURNAL_GENERATION',
    'CONTEXT_SUMMARY_REFRESH',
    'EVIDENCE_VARIANT_GENERATION',
    'EVIDENCE_EXTRACTION',
    'CLEANUP',
    'BACKUP',
    'NOTIFICATION_DELIVERY'
);

CREATE TYPE job_status_enum AS ENUM (
    'CREATED',
    'QUEUED',
    'PROCESSING',
    'RETRYING',
    'COMPLETED',
    'FAILED',
    'CANCELLED'
);

CREATE TYPE job_progress_stage_enum AS ENUM (
    'PREPARING_EVIDENCE',
    'BUILDING_CONTEXT',
    'CALLING_PROVIDER',
    'VALIDATING_OUTPUT',
    'CHECKING_CONTRADICTIONS',
    'SAVING_RESULT',
    'COMPLETED'
);

CREATE TYPE provider_enum AS ENUM (
    'GEMINI',
    'DEEPSEEK',
    'MOCK'
);

CREATE TYPE notification_type_enum AS ENUM (
    'ANALYSIS_COMPLETED',
    'ANALYSIS_FAILED',
    'THESIS_WEAKENED',
    'THESIS_INVALIDATED',
    'SESSION_REQUIRES_UPDATE',
    'JOURNAL_GENERATED',
    'PROVIDER_CONFIGURATION_ERROR'
);

CREATE TYPE notification_priority_enum AS ENUM (
    'INFORMATIONAL',
    'SUCCESS',
    'WARNING',
    'CRITICAL'
);

CREATE TYPE outbox_status_enum AS ENUM (
    'PENDING',
    'PROCESSING',
    'PUBLISHED',
    'FAILED'
);

CREATE TYPE evidence_role_enum AS ENUM (
    'PRIMARY_CURRENT',
    'PRIMARY_PREVIOUS',
    'INITIAL_REFERENCE',
    'HISTORICAL_REFERENCE',
    'SUPPORTING',
    'CONTRADICTORY',
    'USER_NOTE_REFERENCE'
);

CREATE TYPE thesis_evidence_relationship_enum AS ENUM (
    'SUPPORTING',
    'CONFLICTING',
    'INVALIDATING',
    'REFERENCE'
);

CREATE TYPE evidence_variant_type_enum AS ENUM (
    'ORIGINAL',
    'THUMBNAIL',
    'PREVIEW',
    'AI_INPUT',
    'NORMALIZED'
);

CREATE TYPE job_attempt_status_enum AS ENUM (
    'PROCESSING',
    'COMPLETED',
    'FAILED',
    'CANCELLED'
);

-- ============================================================================
-- SHARED FUNCTIONS
-- ============================================================================

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION increment_row_version()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.version = OLD.version + 1;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION prevent_core_history_update()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        'Historical record in table % is immutable',
        TG_TABLE_NAME
        USING ERRCODE = '55000';
END;
$$;

CREATE OR REPLACE FUNCTION prevent_history_delete()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        'Historical record in table % cannot be deleted through normal operations',
        TG_TABLE_NAME
        USING ERRCODE = '55000';
END;
$$;

-- ============================================================================
-- USERS AND AUTHENTICATION
-- ============================================================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email CITEXT NOT NULL,
    username CITEXT,
    password_hash TEXT NOT NULL,
    account_status account_status_enum NOT NULL DEFAULT 'ACTIVE',
    preferred_ui_language VARCHAR(10) NOT NULL DEFAULT 'id-ID',
    timezone VARCHAR(64) NOT NULL DEFAULT 'Asia/Jakarta',
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    disabled_at TIMESTAMPTZ,

    CONSTRAINT uq_users_email UNIQUE (email),
    CONSTRAINT ck_users_email_not_empty
        CHECK (BTRIM(email::TEXT) <> ''),
    CONSTRAINT ck_users_language_not_empty
        CHECK (BTRIM(preferred_ui_language) <> ''),
    CONSTRAINT ck_users_timezone_not_empty
        CHECK (BTRIM(timezone) <> ''),
    CONSTRAINT ck_users_disabled_state
        CHECK (
            account_status <> 'DISABLED'
            OR disabled_at IS NOT NULL
        )
);

CREATE UNIQUE INDEX uq_users_username_not_null
    ON users (username)
    WHERE username IS NOT NULL;

CREATE INDEX ix_users_account_status
    ON users (account_status);

CREATE TRIGGER trg_users_set_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();


CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    token_hash TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMPTZ,
    ip_address INET,
    user_agent TEXT,

    CONSTRAINT fk_user_sessions_user
        FOREIGN KEY (user_id)
        REFERENCES users (id)
        ON DELETE CASCADE,

    CONSTRAINT uq_user_sessions_token_hash
        UNIQUE (token_hash),

    CONSTRAINT ck_user_sessions_expiry
        CHECK (expires_at > created_at),

    CONSTRAINT ck_user_sessions_revocation
        CHECK (
            revoked_at IS NULL
            OR revoked_at >= created_at
        )
);

CREATE INDEX ix_user_sessions_user_expires
    ON user_sessions (user_id, expires_at DESC);

CREATE INDEX ix_user_sessions_active
    ON user_sessions (user_id, expires_at)
    WHERE revoked_at IS NULL;

-- ============================================================================
-- TRADE SESSIONS
-- Canonical-reference foreign keys are added later because of circular relations.
-- ============================================================================

CREATE TABLE trade_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL,
    ticker VARCHAR(32) NOT NULL,
    company_name VARCHAR(255),
    market market_enum NOT NULL DEFAULT 'IDX',
    currency currency_enum NOT NULL DEFAULT 'IDR',
    title VARCHAR(255),
    initial_note TEXT,

    lifecycle_status session_status_enum NOT NULL DEFAULT 'DRAFT',
    stable_status session_status_enum NOT NULL DEFAULT 'DRAFT',
    pre_archive_status session_status_enum,

    active_thesis_id UUID,
    active_position_id UUID,
    latest_canonical_analysis_id UUID,
    canonical_context_summary_id UUID,
    latest_update_id UUID,

    latest_confidence_score NUMERIC(7,4),
    latest_target_probability NUMERIC(7,4),
    latest_thesis_status thesis_status_enum,
    latest_risk_level risk_level_enum,
    latest_recommended_action recommended_action_enum,
    latest_market_price NUMERIC(20,6),

    last_evidence_at TIMESTAMPTZ,
    last_analysis_at TIMESTAMPTZ,
    last_position_event_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    archived_at TIMESTAMPTZ,

    version BIGINT NOT NULL DEFAULT 1,

    CONSTRAINT fk_trade_sessions_owner
        FOREIGN KEY (owner_id)
        REFERENCES users (id)
        ON DELETE RESTRICT,

    CONSTRAINT ck_trade_sessions_ticker_not_empty
        CHECK (BTRIM(ticker) <> ''),

    CONSTRAINT ck_trade_sessions_ticker_uppercase
        CHECK (ticker = UPPER(ticker)),

    CONSTRAINT ck_trade_sessions_confidence
        CHECK (
            latest_confidence_score IS NULL
            OR latest_confidence_score BETWEEN 0 AND 100
        ),

    CONSTRAINT ck_trade_sessions_target_probability
        CHECK (
            latest_target_probability IS NULL
            OR latest_target_probability BETWEEN 0 AND 100
        ),

    CONSTRAINT ck_trade_sessions_latest_price
        CHECK (
            latest_market_price IS NULL
            OR latest_market_price > 0
        ),

    CONSTRAINT ck_trade_sessions_version
        CHECK (version >= 1),

    CONSTRAINT ck_trade_sessions_stable_status
        CHECK (
            stable_status NOT IN ('ANALYZING', 'ARCHIVED')
        ),

    CONSTRAINT ck_trade_sessions_archive_state
        CHECK (
            (
                lifecycle_status = 'ARCHIVED'
                AND pre_archive_status IS NOT NULL
                AND archived_at IS NOT NULL
            )
            OR
            (
                lifecycle_status <> 'ARCHIVED'
                AND pre_archive_status IS NULL
            )
        ),

    CONSTRAINT ck_trade_sessions_closed_timestamp
        CHECK (
            lifecycle_status NOT IN (
                'CLOSED_TAKE_PROFIT',
                'CLOSED_STOP_LOSS',
                'CLOSED_MANUAL'
            )
            OR closed_at IS NOT NULL
        ),

    CONSTRAINT ck_trade_sessions_cancelled_timestamp
        CHECK (
            lifecycle_status <> 'CANCELLED'
            OR cancelled_at IS NOT NULL
        ),

    CONSTRAINT ck_trade_sessions_analyzing_stable_status
        CHECK (
            lifecycle_status <> 'ANALYZING'
            OR stable_status NOT IN ('ANALYZING', 'ARCHIVED')
        )
);

CREATE INDEX ix_trade_sessions_owner_lifecycle
    ON trade_sessions (owner_id, lifecycle_status);

CREATE INDEX ix_trade_sessions_owner_stable
    ON trade_sessions (owner_id, stable_status);

CREATE INDEX ix_trade_sessions_owner_ticker
    ON trade_sessions (owner_id, ticker);

CREATE INDEX ix_trade_sessions_owner_updated
    ON trade_sessions (owner_id, updated_at DESC);

CREATE INDEX ix_trade_sessions_owner_analysis
    ON trade_sessions (owner_id, last_analysis_at DESC);

CREATE INDEX ix_trade_sessions_owner_thesis
    ON trade_sessions (owner_id, latest_thesis_status);

CREATE INDEX ix_trade_sessions_active
    ON trade_sessions (owner_id, updated_at DESC)
    WHERE lifecycle_status <> 'ARCHIVED'
      AND stable_status IN (
          'DRAFT',
          'READY_FOR_ANALYSIS',
          'WATCHING',
          'OPEN_POSITION',
          'PARTIALLY_CLOSED'
      );

CREATE INDEX ix_trade_sessions_open_positions
    ON trade_sessions (owner_id, updated_at DESC)
    WHERE stable_status IN ('OPEN_POSITION', 'PARTIALLY_CLOSED')
      AND lifecycle_status <> 'ARCHIVED';

CREATE INDEX ix_trade_sessions_closed
    ON trade_sessions (owner_id, closed_at DESC)
    WHERE stable_status IN (
        'CLOSED_TAKE_PROFIT',
        'CLOSED_STOP_LOSS',
        'CLOSED_MANUAL'
    );

CREATE INDEX ix_trade_sessions_archived
    ON trade_sessions (owner_id, archived_at DESC)
    WHERE lifecycle_status = 'ARCHIVED';

CREATE TRIGGER trg_trade_sessions_set_updated_at
BEFORE UPDATE ON trade_sessions
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_trade_sessions_increment_version
BEFORE UPDATE ON trade_sessions
FOR EACH ROW
EXECUTE FUNCTION increment_row_version();

-- ============================================================================
-- SESSION UPDATES AND MARKET SNAPSHOTS
-- ============================================================================

CREATE TABLE session_updates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    classification update_classification_enum NOT NULL,
    custom_label VARCHAR(255),
    trading_date DATE,
    market_timestamp TIMESTAMPTZ,
    user_note TEXT,
    market_snapshot_id UUID,
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    analysis_requested_at TIMESTAMPTZ,
    version BIGINT NOT NULL DEFAULT 1,

    CONSTRAINT fk_session_updates_session
        FOREIGN KEY (session_id)
        REFERENCES trade_sessions (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_session_updates_created_by
        FOREIGN KEY (created_by)
        REFERENCES users (id)
        ON DELETE RESTRICT,

    CONSTRAINT ck_session_updates_custom_label
        CHECK (
            classification <> 'CUSTOM'
            OR (
                custom_label IS NOT NULL
                AND BTRIM(custom_label) <> ''
            )
        ),

    CONSTRAINT ck_session_updates_version
        CHECK (version >= 1)
);

CREATE UNIQUE INDEX uq_session_updates_initial
    ON session_updates (session_id)
    WHERE classification = 'INITIAL';

CREATE INDEX ix_session_updates_session_created
    ON session_updates (session_id, created_at DESC);

CREATE INDEX ix_session_updates_session_date
    ON session_updates (session_id, trading_date DESC);

CREATE INDEX ix_session_updates_session_classification
    ON session_updates (session_id, classification, created_at DESC);

CREATE TRIGGER trg_session_updates_increment_version
BEFORE UPDATE ON session_updates
FOR EACH ROW
EXECUTE FUNCTION increment_row_version();


CREATE TABLE market_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    session_update_id UUID,

    open_price NUMERIC(20,6),
    high_price NUMERIC(20,6),
    low_price NUMERIC(20,6),
    last_price NUMERIC(20,6),
    close_price NUMERIC(20,6),
    previous_close NUMERIC(20,6),
    average_price NUMERIC(20,6),
    absolute_change NUMERIC(20,6),
    percentage_change NUMERIC(10,6),
    volume NUMERIC(24,6),
    transaction_value NUMERIC(24,6),
    best_bid NUMERIC(20,6),
    best_offer NUMERIC(20,6),
    bid_quantity NUMERIC(24,6),
    offer_quantity NUMERIC(24,6),

    observed_at TIMESTAMPTZ,
    data_source data_source_enum NOT NULL DEFAULT 'UNKNOWN',
    data_quality data_quality_enum NOT NULL DEFAULT 'UNKNOWN',
    source_evidence_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_market_snapshots_session
        FOREIGN KEY (session_id)
        REFERENCES trade_sessions (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_market_snapshots_update
        FOREIGN KEY (session_update_id)
        REFERENCES session_updates (id)
        ON DELETE RESTRICT,

    CONSTRAINT ck_market_snapshots_prices_positive
        CHECK (
            (open_price IS NULL OR open_price > 0)
            AND (high_price IS NULL OR high_price > 0)
            AND (low_price IS NULL OR low_price > 0)
            AND (last_price IS NULL OR last_price > 0)
            AND (close_price IS NULL OR close_price > 0)
            AND (previous_close IS NULL OR previous_close > 0)
            AND (average_price IS NULL OR average_price > 0)
            AND (best_bid IS NULL OR best_bid > 0)
            AND (best_offer IS NULL OR best_offer > 0)
        ),

    CONSTRAINT ck_market_snapshots_non_negative_values
        CHECK (
            (volume IS NULL OR volume >= 0)
            AND (transaction_value IS NULL OR transaction_value >= 0)
            AND (bid_quantity IS NULL OR bid_quantity >= 0)
            AND (offer_quantity IS NULL OR offer_quantity >= 0)
        ),

    CONSTRAINT ck_market_snapshots_high_low
        CHECK (
            high_price IS NULL
            OR low_price IS NULL
            OR high_price >= low_price
        )
);

CREATE INDEX ix_market_snapshots_session_observed
    ON market_snapshots (session_id, observed_at DESC);

CREATE INDEX ix_market_snapshots_update
    ON market_snapshots (session_update_id);

ALTER TABLE session_updates
    ADD CONSTRAINT fk_session_updates_market_snapshot
    FOREIGN KEY (market_snapshot_id)
    REFERENCES market_snapshots (id)
    DEFERRABLE INITIALLY DEFERRED
    ON DELETE SET NULL;

-- ============================================================================
-- EVIDENCE
-- ============================================================================

CREATE TABLE evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    owner_id UUID NOT NULL,
    evidence_type evidence_type_enum NOT NULL,
    evidence_status evidence_status_enum NOT NULL DEFAULT 'PENDING',
    update_classification update_classification_enum,

    original_filename TEXT,
    storage_object_key TEXT,
    mime_type VARCHAR(255),
    file_size_bytes BIGINT,
    checksum_sha256 CHAR(64),

    market_timestamp TIMESTAMPTZ,
    caption TEXT,
    source_note TEXT,
    text_content TEXT,

    extraction_status extraction_status_enum NOT NULL DEFAULT 'NOT_REQUESTED',
    extraction_payload JSONB,
    extraction_confidence NUMERIC(7,4),

    supersedes_evidence_id UUID,
    exclusion_reason TEXT,
    excluded_at TIMESTAMPTZ,

    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    CONSTRAINT fk_evidence_session
        FOREIGN KEY (session_id)
        REFERENCES trade_sessions (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_evidence_owner
        FOREIGN KEY (owner_id)
        REFERENCES users (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_evidence_supersedes
        FOREIGN KEY (supersedes_evidence_id)
        REFERENCES evidence (id)
        ON DELETE RESTRICT,

    CONSTRAINT ck_evidence_file_size
        CHECK (
            file_size_bytes IS NULL
            OR file_size_bytes >= 0
        ),

    CONSTRAINT ck_evidence_extraction_confidence
        CHECK (
            extraction_confidence IS NULL
            OR extraction_confidence BETWEEN 0 AND 100
        ),

    CONSTRAINT ck_evidence_excluded
        CHECK (
            evidence_status <> 'EXCLUDED'
            OR (
                exclusion_reason IS NOT NULL
                AND BTRIM(exclusion_reason) <> ''
                AND excluded_at IS NOT NULL
            )
        ),

    CONSTRAINT ck_evidence_user_note_content
        CHECK (
            evidence_type <> 'USER_NOTE'
            OR (
                text_content IS NOT NULL
                AND BTRIM(text_content) <> ''
            )
        ),

    CONSTRAINT ck_evidence_file_metadata
        CHECK (
            evidence_type = 'USER_NOTE'
            OR evidence_status IN ('PENDING', 'FAILED', 'DELETED')
            OR (
                storage_object_key IS NOT NULL
                AND mime_type IS NOT NULL
            )
        ),

    CONSTRAINT ck_evidence_checksum_format
        CHECK (
            checksum_sha256 IS NULL
            OR checksum_sha256 ~ '^[0-9a-fA-F]{64}$'
        )
);

CREATE INDEX ix_evidence_session_uploaded
    ON evidence (session_id, uploaded_at DESC);

CREATE INDEX ix_evidence_session_type_status
    ON evidence (session_id, evidence_type, evidence_status);

CREATE INDEX ix_evidence_owner_checksum
    ON evidence (owner_id, checksum_sha256)
    WHERE checksum_sha256 IS NOT NULL;

CREATE INDEX ix_evidence_session_market_time
    ON evidence (session_id, market_timestamp DESC);

CREATE INDEX ix_evidence_active_initial
    ON evidence (session_id, evidence_type)
    WHERE evidence_status = 'AVAILABLE'
      AND deleted_at IS NULL
      AND evidence_type IN (
          'ORDERBOOK_SCREENSHOT',
          'CHART_THREE_MONTH',
          'CHART_SIX_MONTH'
      );

CREATE TRIGGER trg_evidence_set_updated_at
BEFORE UPDATE ON evidence
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();


CREATE TABLE evidence_variants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evidence_id UUID NOT NULL,
    variant_type evidence_variant_type_enum NOT NULL,
    storage_object_key TEXT NOT NULL,
    mime_type VARCHAR(255) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    width INTEGER,
    height INTEGER,
    checksum_sha256 CHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_evidence_variants_evidence
        FOREIGN KEY (evidence_id)
        REFERENCES evidence (id)
        ON DELETE RESTRICT,

    CONSTRAINT uq_evidence_variants_type
        UNIQUE (evidence_id, variant_type),

    CONSTRAINT ck_evidence_variants_file_size
        CHECK (file_size_bytes >= 0),

    CONSTRAINT ck_evidence_variants_dimensions
        CHECK (
            (width IS NULL OR width > 0)
            AND (height IS NULL OR height > 0)
        ),

    CONSTRAINT ck_evidence_variants_checksum
        CHECK (
            checksum_sha256 IS NULL
            OR checksum_sha256 ~ '^[0-9a-fA-F]{64}$'
        )
);

CREATE INDEX ix_evidence_variants_evidence
    ON evidence_variants (evidence_id);


CREATE TABLE session_update_evidence (
    session_update_id UUID NOT NULL,
    evidence_id UUID NOT NULL,
    display_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_session_update_evidence
        PRIMARY KEY (session_update_id, evidence_id),

    CONSTRAINT fk_session_update_evidence_update
        FOREIGN KEY (session_update_id)
        REFERENCES session_updates (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_session_update_evidence_evidence
        FOREIGN KEY (evidence_id)
        REFERENCES evidence (id)
        ON DELETE RESTRICT,

    CONSTRAINT ck_session_update_evidence_order
        CHECK (display_order >= 0)
);

CREATE INDEX ix_session_update_evidence_evidence
    ON session_update_evidence (evidence_id);

ALTER TABLE market_snapshots
    ADD CONSTRAINT fk_market_snapshots_source_evidence
    FOREIGN KEY (source_evidence_id)
    REFERENCES evidence (id)
    ON DELETE SET NULL;

-- ============================================================================
-- ANALYSIS REQUESTS
-- ============================================================================

CREATE TABLE analysis_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    session_update_id UUID,
    requested_by UUID NOT NULL,

    analysis_type analysis_type_enum NOT NULL,
    request_status analysis_request_status_enum NOT NULL DEFAULT 'CREATED',
    idempotency_key VARCHAR(255) NOT NULL,

    requested_provider provider_enum,
    requested_model VARCHAR(255),
    fallback_allowed BOOLEAN NOT NULL DEFAULT FALSE,

    prompt_name VARCHAR(255) NOT NULL,
    prompt_version VARCHAR(64) NOT NULL,
    schema_version VARCHAR(64) NOT NULL,
    context_summary_version INTEGER,

    session_version_snapshot BIGINT NOT NULL,
    position_version_snapshot BIGINT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    queued_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,

    CONSTRAINT fk_analysis_requests_session
        FOREIGN KEY (session_id)
        REFERENCES trade_sessions (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_analysis_requests_update
        FOREIGN KEY (session_update_id)
        REFERENCES session_updates (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_analysis_requests_user
        FOREIGN KEY (requested_by)
        REFERENCES users (id)
        ON DELETE RESTRICT,

    CONSTRAINT uq_analysis_requests_idempotency
        UNIQUE (idempotency_key),

    CONSTRAINT ck_analysis_requests_snapshot_versions
        CHECK (
            session_version_snapshot >= 1
            AND (
                position_version_snapshot IS NULL
                OR position_version_snapshot >= 1
            )
        ),

    CONSTRAINT ck_analysis_requests_prompt_fields
        CHECK (
            BTRIM(prompt_name) <> ''
            AND BTRIM(prompt_version) <> ''
            AND BTRIM(schema_version) <> ''
        ),

    CONSTRAINT ck_analysis_requests_status_timestamps
        CHECK (
            (request_status <> 'QUEUED' OR queued_at IS NOT NULL)
            AND (request_status <> 'PROCESSING' OR started_at IS NOT NULL)
            AND (request_status <> 'COMPLETED' OR completed_at IS NOT NULL)
            AND (request_status <> 'FAILED' OR failed_at IS NOT NULL)
            AND (request_status <> 'CANCELLED' OR cancelled_at IS NOT NULL)
        )
);

CREATE INDEX ix_analysis_requests_session_created
    ON analysis_requests (session_id, created_at DESC);

CREATE INDEX ix_analysis_requests_session_status
    ON analysis_requests (session_id, request_status);

CREATE INDEX ix_analysis_requests_update
    ON analysis_requests (session_update_id);

CREATE INDEX ix_analysis_requests_active
    ON analysis_requests (session_id, analysis_type, created_at)
    WHERE request_status IN ('QUEUED', 'PROCESSING');

-- ============================================================================
-- ANALYSIS VERSIONS
-- ============================================================================

CREATE TABLE analysis_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    analysis_request_id UUID NOT NULL,
    analysis_type analysis_type_enum NOT NULL,
    version_number INTEGER NOT NULL,

    canonical_status analysis_canonical_status_enum NOT NULL DEFAULT 'PENDING',
    validation_status analysis_validation_status_enum NOT NULL DEFAULT 'PENDING',

    provider provider_enum NOT NULL,
    model VARCHAR(255) NOT NULL,
    provider_request_id TEXT,

    prompt_name VARCHAR(255) NOT NULL,
    prompt_version VARCHAR(64) NOT NULL,
    schema_version VARCHAR(64) NOT NULL,
    context_summary_version INTEGER,

    session_status_snapshot session_status_enum NOT NULL,
    session_version_snapshot BIGINT NOT NULL,
    position_version_snapshot BIGINT,
    position_snapshot JSONB,

    structured_payload JSONB NOT NULL,
    narrative_language VARCHAR(16) NOT NULL DEFAULT 'id-ID',

    contradiction_status contradiction_status_enum NOT NULL DEFAULT 'NOT_CHECKED',
    contradiction_details JSONB,

    generated_at TIMESTAMPTZ NOT NULL,
    validated_at TIMESTAMPTZ,
    canonicalized_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_analysis_versions_session
        FOREIGN KEY (session_id)
        REFERENCES trade_sessions (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_analysis_versions_request
        FOREIGN KEY (analysis_request_id)
        REFERENCES analysis_requests (id)
        ON DELETE RESTRICT,

    CONSTRAINT uq_analysis_versions_session_version
        UNIQUE (session_id, version_number),

    CONSTRAINT ck_analysis_versions_version
        CHECK (version_number >= 1),

    CONSTRAINT ck_analysis_versions_snapshot_versions
        CHECK (
            session_version_snapshot >= 1
            AND (
                position_version_snapshot IS NULL
                OR position_version_snapshot >= 1
            )
        ),

    CONSTRAINT ck_analysis_versions_payload_object
        CHECK (jsonb_typeof(structured_payload) = 'object'),

    CONSTRAINT ck_analysis_versions_language
        CHECK (
            narrative_language IN ('id', 'id-ID')
        ),

    CONSTRAINT ck_analysis_versions_acceptance
        CHECK (
            canonical_status <> 'ACCEPTED'
            OR (
                validation_status IN ('VALID', 'VALID_WITH_WARNINGS')
                AND contradiction_status IN ('PASS', 'PASS_WITH_EXPLANATION')
                AND validated_at IS NOT NULL
                AND canonicalized_at IS NOT NULL
            )
        ),

    CONSTRAINT ck_analysis_versions_rejected
        CHECK (
            canonical_status <> 'REJECTED'
            OR validation_status NOT IN ('VALID', 'VALID_WITH_WARNINGS')
            OR contradiction_status IN ('REVIEW_REQUIRED', 'REJECT')
        )
);

CREATE INDEX ix_analysis_versions_session_version
    ON analysis_versions (session_id, version_number DESC);

CREATE INDEX ix_analysis_versions_session_generated
    ON analysis_versions (session_id, generated_at DESC);

CREATE INDEX ix_analysis_versions_session_type
    ON analysis_versions (session_id, analysis_type, generated_at DESC);

CREATE INDEX ix_analysis_versions_request
    ON analysis_versions (analysis_request_id);

CREATE INDEX ix_analysis_versions_validation
    ON analysis_versions (validation_status);

CREATE INDEX ix_analysis_versions_contradiction
    ON analysis_versions (contradiction_status);

CREATE INDEX ix_analysis_versions_accepted
    ON analysis_versions (session_id, generated_at DESC)
    WHERE canonical_status = 'ACCEPTED';

-- Preserve core historical values.
CREATE TRIGGER trg_analysis_versions_prevent_delete
BEFORE DELETE ON analysis_versions
FOR EACH ROW
EXECUTE FUNCTION prevent_history_delete();

-- ============================================================================
-- ANALYSIS EVIDENCE AND PROBABILITIES
-- ============================================================================

CREATE TABLE analysis_evidence_links (
    analysis_version_id UUID NOT NULL,
    evidence_id UUID NOT NULL,
    evidence_role evidence_role_enum NOT NULL,
    context_priority INTEGER,
    included_as_image BOOLEAN NOT NULL DEFAULT FALSE,
    included_as_extracted_text BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_analysis_evidence_links
        PRIMARY KEY (analysis_version_id, evidence_id),

    CONSTRAINT fk_analysis_evidence_analysis
        FOREIGN KEY (analysis_version_id)
        REFERENCES analysis_versions (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_analysis_evidence_evidence
        FOREIGN KEY (evidence_id)
        REFERENCES evidence (id)
        ON DELETE RESTRICT,

    CONSTRAINT ck_analysis_evidence_priority
        CHECK (
            context_priority IS NULL
            OR context_priority >= 0
        ),

    CONSTRAINT ck_analysis_evidence_inclusion
        CHECK (
            included_as_image = TRUE
            OR included_as_extracted_text = TRUE
        )
);

CREATE INDEX ix_analysis_evidence_evidence
    ON analysis_evidence_links (evidence_id);


CREATE TABLE analysis_probability_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_version_id UUID NOT NULL,
    probability_type probability_type_enum NOT NULL,
    percentage NUMERIC(7,4) NOT NULL,
    previous_percentage NUMERIC(7,4),
    change_direction probability_change_enum NOT NULL,
    reasoning TEXT NOT NULL,
    supporting_evidence JSONB,
    uncertainty_level uncertainty_level_enum NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_probability_analysis
        FOREIGN KEY (analysis_version_id)
        REFERENCES analysis_versions (id)
        ON DELETE RESTRICT,

    CONSTRAINT uq_probability_analysis_type
        UNIQUE (analysis_version_id, probability_type),

    CONSTRAINT ck_probability_percentage
        CHECK (percentage BETWEEN 0 AND 100),

    CONSTRAINT ck_probability_previous
        CHECK (
            previous_percentage IS NULL
            OR previous_percentage BETWEEN 0 AND 100
        ),

    CONSTRAINT ck_probability_reasoning
        CHECK (BTRIM(reasoning) <> '')
);

CREATE INDEX ix_probability_type_analysis
    ON analysis_probability_assessments (
        probability_type,
        analysis_version_id
    );

-- ============================================================================
-- PRICE LEVELS AND TRADING THESES
-- ============================================================================

CREATE TABLE price_levels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    analysis_version_id UUID,
    thesis_id UUID,

    exact_price NUMERIC(20,6),
    lower_bound NUMERIC(20,6),
    upper_bound NUMERIC(20,6),

    level_type price_level_type_enum NOT NULL,
    basis TEXT NOT NULL,
    source_type price_level_source_enum NOT NULL,
    level_status price_level_status_enum NOT NULL DEFAULT 'ACTIVE',
    confidence_score NUMERIC(7,4),
    observed_at TIMESTAMPTZ,
    superseded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_price_levels_session
        FOREIGN KEY (session_id)
        REFERENCES trade_sessions (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_price_levels_analysis
        FOREIGN KEY (analysis_version_id)
        REFERENCES analysis_versions (id)
        ON DELETE RESTRICT,

    CONSTRAINT ck_price_levels_value
        CHECK (
            (
                exact_price IS NOT NULL
                AND lower_bound IS NULL
                AND upper_bound IS NULL
            )
            OR
            (
                exact_price IS NULL
                AND lower_bound IS NOT NULL
                AND upper_bound IS NOT NULL
            )
        ),

    CONSTRAINT ck_price_levels_positive
        CHECK (
            (exact_price IS NULL OR exact_price > 0)
            AND (lower_bound IS NULL OR lower_bound > 0)
            AND (upper_bound IS NULL OR upper_bound > 0)
        ),

    CONSTRAINT ck_price_levels_zone
        CHECK (
            lower_bound IS NULL
            OR upper_bound IS NULL
            OR lower_bound <= upper_bound
        ),

    CONSTRAINT ck_price_levels_basis
        CHECK (BTRIM(basis) <> ''),

    CONSTRAINT ck_price_levels_confidence
        CHECK (
            confidence_score IS NULL
            OR confidence_score BETWEEN 0 AND 100
        )
);

CREATE INDEX ix_price_levels_session_type
    ON price_levels (session_id, level_type, created_at DESC);

CREATE INDEX ix_price_levels_analysis
    ON price_levels (analysis_version_id);

CREATE INDEX ix_price_levels_thesis
    ON price_levels (thesis_id);


CREATE TABLE trading_theses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    version_number INTEGER NOT NULL,

    thesis_status thesis_status_enum NOT NULL,
    directional_bias directional_bias_enum NOT NULL,
    thesis_statement TEXT NOT NULL,
    technical_rationale TEXT NOT NULL,
    supporting_evidence_summary TEXT,
    conflicting_evidence_summary TEXT,

    key_support_level_id UUID,
    key_resistance_level_id UUID,
    invalidation_level_id UUID,
    invalidation_condition TEXT NOT NULL,
    expected_scenario TEXT,

    confidence_score NUMERIC(7,4) NOT NULL,

    source_analysis_version_id UUID NOT NULL,
    previous_thesis_id UUID,
    change_type thesis_change_type_enum NOT NULL,
    change_reason TEXT,

    effective_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_trading_theses_session
        FOREIGN KEY (session_id)
        REFERENCES trade_sessions (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_trading_theses_analysis
        FOREIGN KEY (source_analysis_version_id)
        REFERENCES analysis_versions (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_trading_theses_previous
        FOREIGN KEY (previous_thesis_id)
        REFERENCES trading_theses (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_trading_theses_support
        FOREIGN KEY (key_support_level_id)
        REFERENCES price_levels (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_trading_theses_resistance
        FOREIGN KEY (key_resistance_level_id)
        REFERENCES price_levels (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_trading_theses_invalidation
        FOREIGN KEY (invalidation_level_id)
        REFERENCES price_levels (id)
        ON DELETE RESTRICT,

    CONSTRAINT uq_trading_theses_session_version
        UNIQUE (session_id, version_number),

    CONSTRAINT ck_trading_theses_version
        CHECK (version_number >= 1),

    CONSTRAINT ck_trading_theses_statement
        CHECK (BTRIM(thesis_statement) <> ''),

    CONSTRAINT ck_trading_theses_rationale
        CHECK (BTRIM(technical_rationale) <> ''),

    CONSTRAINT ck_trading_theses_invalidation_condition
        CHECK (BTRIM(invalidation_condition) <> ''),

    CONSTRAINT ck_trading_theses_confidence
        CHECK (confidence_score BETWEEN 0 AND 100),

    CONSTRAINT ck_trading_theses_change_reason
        CHECK (
            change_type IN ('CREATED', 'UNCHANGED')
            OR (
                change_reason IS NOT NULL
                AND BTRIM(change_reason) <> ''
            )
        ),

    CONSTRAINT ck_trading_theses_previous_version
        CHECK (
            version_number = 1
            OR previous_thesis_id IS NOT NULL
        )
);

CREATE INDEX ix_trading_theses_session_version
    ON trading_theses (session_id, version_number DESC);

CREATE INDEX ix_trading_theses_session_status
    ON trading_theses (session_id, thesis_status, effective_at DESC);

CREATE INDEX ix_trading_theses_analysis
    ON trading_theses (source_analysis_version_id);

CREATE TRIGGER trg_trading_theses_prevent_update
BEFORE UPDATE ON trading_theses
FOR EACH ROW
EXECUTE FUNCTION prevent_core_history_update();

CREATE TRIGGER trg_trading_theses_prevent_delete
BEFORE DELETE ON trading_theses
FOR EACH ROW
EXECUTE FUNCTION prevent_history_delete();


ALTER TABLE price_levels
    ADD CONSTRAINT fk_price_levels_thesis
    FOREIGN KEY (thesis_id)
    REFERENCES trading_theses (id)
    DEFERRABLE INITIALLY DEFERRED
    ON DELETE RESTRICT;


CREATE TABLE thesis_evidence_links (
    thesis_id UUID NOT NULL,
    evidence_id UUID NOT NULL,
    relationship_type thesis_evidence_relationship_enum NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_thesis_evidence_links
        PRIMARY KEY (thesis_id, evidence_id, relationship_type),

    CONSTRAINT fk_thesis_evidence_thesis
        FOREIGN KEY (thesis_id)
        REFERENCES trading_theses (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_thesis_evidence_evidence
        FOREIGN KEY (evidence_id)
        REFERENCES evidence (id)
        ON DELETE RESTRICT
);

CREATE INDEX ix_thesis_evidence_evidence
    ON thesis_evidence_links (evidence_id);

-- ============================================================================
-- POSITIONS
-- ============================================================================

CREATE TABLE positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,

    position_status position_status_enum NOT NULL DEFAULT 'OPEN',
    currency currency_enum NOT NULL DEFAULT 'IDR',
    quantity_unit quantity_unit_enum NOT NULL DEFAULT 'SHARE',

    total_entry_quantity NUMERIC(24,6),
    remaining_quantity NUMERIC(24,6),
    weighted_average_entry NUMERIC(20,6) NOT NULL,
    total_entry_cost NUMERIC(24,6),

    realized_proceeds NUMERIC(24,6),
    realized_profit_loss NUMERIC(24,6),
    unrealized_profit_loss NUMERIC(24,6),
    total_profit_loss NUMERIC(24,6),
    return_percentage NUMERIC(12,6),

    active_stop_loss_id UUID,

    opened_at TIMESTAMPTZ NOT NULL,
    partially_closed_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version BIGINT NOT NULL DEFAULT 1,

    CONSTRAINT fk_positions_session
        FOREIGN KEY (session_id)
        REFERENCES trade_sessions (id)
        ON DELETE RESTRICT,

    CONSTRAINT uq_positions_session
        UNIQUE (session_id),

    CONSTRAINT ck_positions_average_entry
        CHECK (weighted_average_entry > 0),

    CONSTRAINT ck_positions_quantities
        CHECK (
            (total_entry_quantity IS NULL OR total_entry_quantity > 0)
            AND (remaining_quantity IS NULL OR remaining_quantity >= 0)
            AND (
                total_entry_quantity IS NULL
                OR remaining_quantity IS NULL
                OR remaining_quantity <= total_entry_quantity
            )
        ),

    CONSTRAINT ck_positions_version
        CHECK (version >= 1),

    CONSTRAINT ck_positions_closed
        CHECK (
            position_status <> 'CLOSED'
            OR closed_at IS NOT NULL
        ),

    CONSTRAINT ck_positions_partial_timestamp
        CHECK (
            position_status <> 'PARTIALLY_CLOSED'
            OR partially_closed_at IS NOT NULL
        ),

    CONSTRAINT ck_positions_closed_quantity
        CHECK (
            position_status <> 'CLOSED'
            OR remaining_quantity IS NULL
            OR remaining_quantity = 0
        ),

    CONSTRAINT ck_positions_active_quantity
        CHECK (
            position_status = 'CLOSED'
            OR remaining_quantity IS NULL
            OR remaining_quantity > 0
        )
);

CREATE INDEX ix_positions_status
    ON positions (position_status);

CREATE INDEX ix_positions_opened
    ON positions (opened_at DESC);

CREATE INDEX ix_positions_closed
    ON positions (closed_at DESC);

CREATE TRIGGER trg_positions_set_updated_at
BEFORE UPDATE ON positions
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_positions_increment_version
BEFORE UPDATE ON positions
FOR EACH ROW
EXECUTE FUNCTION increment_row_version();


CREATE TABLE position_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    position_id UUID NOT NULL,
    entry_sequence INTEGER NOT NULL,
    entry_type entry_type_enum NOT NULL,
    entry_classification entry_classification_enum,

    price NUMERIC(20,6) NOT NULL,
    quantity NUMERIC(24,6),
    gross_value NUMERIC(24,6),
    broker_fee NUMERIC(24,6),
    net_cost NUMERIC(24,6),

    executed_at TIMESTAMPTZ NOT NULL,
    user_reason TEXT,
    related_analysis_version_id UUID,
    planned_entry_reference JSONB,
    corrects_entry_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_position_entries_position
        FOREIGN KEY (position_id)
        REFERENCES positions (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_position_entries_analysis
        FOREIGN KEY (related_analysis_version_id)
        REFERENCES analysis_versions (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_position_entries_correction
        FOREIGN KEY (corrects_entry_id)
        REFERENCES position_entries (id)
        ON DELETE RESTRICT,

    CONSTRAINT uq_position_entries_sequence
        UNIQUE (position_id, entry_sequence),

    CONSTRAINT ck_position_entries_sequence
        CHECK (entry_sequence >= 1),

    CONSTRAINT ck_position_entries_price
        CHECK (price > 0),

    CONSTRAINT ck_position_entries_quantity
        CHECK (
            quantity IS NULL
            OR quantity > 0
        ),

    CONSTRAINT ck_position_entries_values
        CHECK (
            (gross_value IS NULL OR gross_value >= 0)
            AND (broker_fee IS NULL OR broker_fee >= 0)
            AND (net_cost IS NULL OR net_cost >= 0)
        ),

    CONSTRAINT ck_position_entries_correction
        CHECK (
            entry_type <> 'CORRECTION'
            OR corrects_entry_id IS NOT NULL
        )
);

CREATE UNIQUE INDEX uq_position_entries_initial
    ON position_entries (position_id)
    WHERE entry_type = 'INITIAL'
      AND corrects_entry_id IS NULL;

CREATE INDEX ix_position_entries_position_time
    ON position_entries (position_id, executed_at);

CREATE INDEX ix_position_entries_analysis
    ON position_entries (related_analysis_version_id);

CREATE TRIGGER trg_position_entries_prevent_update
BEFORE UPDATE ON position_entries
FOR EACH ROW
EXECUTE FUNCTION prevent_core_history_update();

CREATE TRIGGER trg_position_entries_prevent_delete
BEFORE DELETE ON position_entries
FOR EACH ROW
EXECUTE FUNCTION prevent_history_delete();


CREATE TABLE position_exits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    position_id UUID NOT NULL,
    exit_sequence INTEGER NOT NULL,
    exit_type exit_type_enum NOT NULL,
    exit_reason exit_reason_enum NOT NULL,

    price NUMERIC(20,6) NOT NULL,
    quantity NUMERIC(24,6),
    gross_value NUMERIC(24,6),
    broker_fee NUMERIC(24,6),
    net_proceeds NUMERIC(24,6),
    realized_profit_loss NUMERIC(24,6),

    executed_at TIMESTAMPTZ NOT NULL,
    user_note TEXT,
    related_analysis_version_id UUID,

    active_stop_snapshot JSONB,
    active_target_snapshot JSONB,

    corrects_exit_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_position_exits_position
        FOREIGN KEY (position_id)
        REFERENCES positions (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_position_exits_analysis
        FOREIGN KEY (related_analysis_version_id)
        REFERENCES analysis_versions (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_position_exits_correction
        FOREIGN KEY (corrects_exit_id)
        REFERENCES position_exits (id)
        ON DELETE RESTRICT,

    CONSTRAINT uq_position_exits_sequence
        UNIQUE (position_id, exit_sequence),

    CONSTRAINT ck_position_exits_sequence
        CHECK (exit_sequence >= 1),

    CONSTRAINT ck_position_exits_price
        CHECK (price > 0),

    CONSTRAINT ck_position_exits_quantity
        CHECK (
            quantity IS NULL
            OR quantity > 0
        ),

    CONSTRAINT ck_position_exits_values
        CHECK (
            (gross_value IS NULL OR gross_value >= 0)
            AND (broker_fee IS NULL OR broker_fee >= 0)
            AND (net_proceeds IS NULL OR net_proceeds >= 0)
        ),

    CONSTRAINT ck_position_exits_correction
        CHECK (
            exit_type <> 'CORRECTION'
            OR corrects_exit_id IS NOT NULL
        )
);

CREATE UNIQUE INDEX uq_position_exits_final
    ON position_exits (position_id)
    WHERE exit_type = 'FINAL'
      AND corrects_exit_id IS NULL;

CREATE INDEX ix_position_exits_position_time
    ON position_exits (position_id, executed_at);

CREATE INDEX ix_position_exits_analysis
    ON position_exits (related_analysis_version_id);

CREATE TRIGGER trg_position_exits_prevent_update
BEFORE UPDATE ON position_exits
FOR EACH ROW
EXECUTE FUNCTION prevent_core_history_update();

CREATE TRIGGER trg_position_exits_prevent_delete
BEFORE DELETE ON position_exits
FOR EACH ROW
EXECUTE FUNCTION prevent_history_delete();


CREATE TABLE stop_loss_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    position_id UUID NOT NULL,
    version_number INTEGER NOT NULL,
    price NUMERIC(20,6) NOT NULL,

    technical_basis TEXT NOT NULL,
    change_reason TEXT,
    risk_amount NUMERIC(24,6),
    risk_percentage NUMERIC(12,6),
    is_wider_than_previous BOOLEAN NOT NULL DEFAULT FALSE,

    recommended_by_analysis_id UUID,
    confirmed_by_user_id UUID NOT NULL,

    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_stop_loss_position
        FOREIGN KEY (position_id)
        REFERENCES positions (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_stop_loss_analysis
        FOREIGN KEY (recommended_by_analysis_id)
        REFERENCES analysis_versions (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_stop_loss_user
        FOREIGN KEY (confirmed_by_user_id)
        REFERENCES users (id)
        ON DELETE RESTRICT,

    CONSTRAINT uq_stop_loss_version
        UNIQUE (position_id, version_number),

    CONSTRAINT ck_stop_loss_version
        CHECK (version_number >= 1),

    CONSTRAINT ck_stop_loss_price
        CHECK (price > 0),

    CONSTRAINT ck_stop_loss_basis
        CHECK (BTRIM(technical_basis) <> ''),

    CONSTRAINT ck_stop_loss_wider_reason
        CHECK (
            is_wider_than_previous = FALSE
            OR (
                change_reason IS NOT NULL
                AND BTRIM(change_reason) <> ''
            )
        ),

    CONSTRAINT ck_stop_loss_effective_range
        CHECK (
            effective_to IS NULL
            OR effective_to >= effective_from
        ),

    CONSTRAINT ck_stop_loss_active_range
        CHECK (
            is_active = FALSE
            OR effective_to IS NULL
        )
);

CREATE UNIQUE INDEX uq_stop_loss_active
    ON stop_loss_versions (position_id)
    WHERE is_active = TRUE;

CREATE INDEX ix_stop_loss_position_version
    ON stop_loss_versions (position_id, version_number DESC);

CREATE INDEX ix_stop_loss_analysis
    ON stop_loss_versions (recommended_by_analysis_id);


ALTER TABLE positions
    ADD CONSTRAINT fk_positions_active_stop
    FOREIGN KEY (active_stop_loss_id)
    REFERENCES stop_loss_versions (id)
    DEFERRABLE INITIALLY DEFERRED
    ON DELETE RESTRICT;


CREATE TABLE position_targets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    position_id UUID NOT NULL,
    target_group_id UUID NOT NULL DEFAULT gen_random_uuid(),
    version_number INTEGER NOT NULL,
    priority INTEGER NOT NULL,

    price NUMERIC(20,6) NOT NULL,
    target_type target_type_enum NOT NULL,
    technical_basis TEXT NOT NULL,

    planned_quantity NUMERIC(24,6),
    planned_percentage NUMERIC(7,4),

    target_status target_status_enum NOT NULL DEFAULT 'ACTIVE',
    change_reason TEXT,

    recommended_by_analysis_id UUID,
    confirmed_by_user_id UUID NOT NULL,

    effective_from TIMESTAMPTZ NOT NULL,
    effective_to TIMESTAMPTZ,
    reached_at TIMESTAMPTZ,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_position_targets_position
        FOREIGN KEY (position_id)
        REFERENCES positions (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_position_targets_analysis
        FOREIGN KEY (recommended_by_analysis_id)
        REFERENCES analysis_versions (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_position_targets_user
        FOREIGN KEY (confirmed_by_user_id)
        REFERENCES users (id)
        ON DELETE RESTRICT,

    CONSTRAINT uq_position_targets_version
        UNIQUE (position_id, target_group_id, version_number),

    CONSTRAINT ck_position_targets_version
        CHECK (version_number >= 1),

    CONSTRAINT ck_position_targets_priority
        CHECK (priority >= 1),

    CONSTRAINT ck_position_targets_price
        CHECK (price > 0),

    CONSTRAINT ck_position_targets_basis
        CHECK (BTRIM(technical_basis) <> ''),

    CONSTRAINT ck_position_targets_quantity
        CHECK (
            planned_quantity IS NULL
            OR planned_quantity > 0
        ),

    CONSTRAINT ck_position_targets_percentage
        CHECK (
            planned_percentage IS NULL
            OR planned_percentage > 0
               AND planned_percentage <= 100
        ),

    CONSTRAINT ck_position_targets_effective_range
        CHECK (
            effective_to IS NULL
            OR effective_to >= effective_from
        ),

    CONSTRAINT ck_position_targets_active_range
        CHECK (
            is_active = FALSE
            OR effective_to IS NULL
        )
);

CREATE UNIQUE INDEX uq_position_targets_active_group
    ON position_targets (position_id, target_group_id)
    WHERE is_active = TRUE;

CREATE INDEX ix_position_targets_active
    ON position_targets (position_id, priority)
    WHERE is_active = TRUE;

CREATE INDEX ix_position_targets_analysis
    ON position_targets (recommended_by_analysis_id);

-- ============================================================================
-- CONTEXT SUMMARIES
-- ============================================================================

CREATE TABLE context_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    version_number INTEGER NOT NULL,

    active_thesis_summary JSONB NOT NULL,
    position_summary JSONB,
    key_level_summary JSONB,
    update_history_summary JSONB,
    thesis_change_summary JSONB,
    current_risks JSONB,
    unresolved_questions JSONB,
    latest_plan_summary JSONB,

    source_analysis_version_ids UUID[],
    source_timeline_cutoff TIMESTAMPTZ,
    generated_by_analysis_request_id UUID,

    generated_at TIMESTAMPTZ NOT NULL,
    superseded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_context_summaries_session
        FOREIGN KEY (session_id)
        REFERENCES trade_sessions (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_context_summaries_request
        FOREIGN KEY (generated_by_analysis_request_id)
        REFERENCES analysis_requests (id)
        ON DELETE RESTRICT,

    CONSTRAINT uq_context_summaries_version
        UNIQUE (session_id, version_number),

    CONSTRAINT ck_context_summaries_version
        CHECK (version_number >= 1),

    CONSTRAINT ck_context_summaries_thesis_object
        CHECK (jsonb_typeof(active_thesis_summary) = 'object')
);

CREATE INDEX ix_context_summaries_session_version
    ON context_summaries (session_id, version_number DESC);

CREATE TRIGGER trg_context_summaries_prevent_delete
BEFORE DELETE ON context_summaries
FOR EACH ROW
EXECUTE FUNCTION prevent_history_delete();

-- ============================================================================
-- TRADING JOURNALS AND USER REFLECTIONS
-- ============================================================================

CREATE TABLE trading_journals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    version_number INTEGER NOT NULL,

    journal_status journal_status_enum NOT NULL DEFAULT 'PENDING',
    canonical_status journal_canonical_status_enum NOT NULL DEFAULT 'CANONICAL',

    source_position_version BIGINT NOT NULL,
    source_analysis_cutoff TIMESTAMPTZ NOT NULL,

    structured_payload JSONB NOT NULL,
    narrative_language VARCHAR(16) NOT NULL DEFAULT 'id-ID',

    generated_by_analysis_request_id UUID NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL,

    outdated_at TIMESTAMPTZ,
    outdated_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_trading_journals_session
        FOREIGN KEY (session_id)
        REFERENCES trade_sessions (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_trading_journals_request
        FOREIGN KEY (generated_by_analysis_request_id)
        REFERENCES analysis_requests (id)
        ON DELETE RESTRICT,

    CONSTRAINT uq_trading_journals_version
        UNIQUE (session_id, version_number),

    CONSTRAINT ck_trading_journals_version
        CHECK (version_number >= 1),

    CONSTRAINT ck_trading_journals_position_version
        CHECK (source_position_version >= 1),

    CONSTRAINT ck_trading_journals_payload
        CHECK (jsonb_typeof(structured_payload) = 'object'),

    CONSTRAINT ck_trading_journals_language
        CHECK (narrative_language IN ('id', 'id-ID')),

    CONSTRAINT ck_trading_journals_outdated
        CHECK (
            journal_status <> 'OUTDATED'
            OR (
                outdated_at IS NOT NULL
                AND outdated_reason IS NOT NULL
                AND BTRIM(outdated_reason) <> ''
            )
        ),

    CONSTRAINT ck_trading_journals_completed
        CHECK (
            journal_status <> 'COMPLETED'
            OR generated_at IS NOT NULL
        )
);

CREATE UNIQUE INDEX uq_trading_journals_canonical
    ON trading_journals (session_id)
    WHERE canonical_status = 'CANONICAL';

CREATE INDEX ix_trading_journals_session_version
    ON trading_journals (session_id, version_number DESC);

CREATE INDEX ix_trading_journals_status
    ON trading_journals (journal_status);

CREATE TRIGGER trg_trading_journals_prevent_delete
BEFORE DELETE ON trading_journals
FOR EACH ROW
EXECUTE FUNCTION prevent_history_delete();


CREATE TABLE user_reflections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    journal_id UUID,

    emotional_state TEXT,
    personal_entry_reason TEXT,
    personal_exit_reason TEXT,
    mistakes TEXT,
    lessons TEXT,
    trade_rating INTEGER,
    final_note TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version BIGINT NOT NULL DEFAULT 1,

    CONSTRAINT fk_user_reflections_session
        FOREIGN KEY (session_id)
        REFERENCES trade_sessions (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_user_reflections_journal
        FOREIGN KEY (journal_id)
        REFERENCES trading_journals (id)
        ON DELETE RESTRICT,

    CONSTRAINT uq_user_reflections_session
        UNIQUE (session_id),

    CONSTRAINT ck_user_reflections_rating
        CHECK (
            trade_rating IS NULL
            OR trade_rating BETWEEN 1 AND 10
        ),

    CONSTRAINT ck_user_reflections_version
        CHECK (version >= 1)
);

CREATE TRIGGER trg_user_reflections_set_updated_at
BEFORE UPDATE ON user_reflections
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_user_reflections_increment_version
BEFORE UPDATE ON user_reflections
FOR EACH ROW
EXECUTE FUNCTION increment_row_version();

-- ============================================================================
-- TIMELINE AND AUDIT
-- ============================================================================

CREATE TABLE timeline_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_category timeline_category_enum NOT NULL,
    actor_type actor_type_enum NOT NULL,
    actor_id UUID,

    title TEXT NOT NULL,
    description TEXT,

    related_entity_type VARCHAR(100),
    related_entity_id UUID,
    change_summary JSONB,

    occurred_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_timeline_events_session
        FOREIGN KEY (session_id)
        REFERENCES trade_sessions (id)
        ON DELETE RESTRICT,

    CONSTRAINT ck_timeline_events_type
        CHECK (BTRIM(event_type) <> ''),

    CONSTRAINT ck_timeline_events_title
        CHECK (BTRIM(title) <> '')
);

CREATE INDEX ix_timeline_events_session_time
    ON timeline_events (session_id, occurred_at DESC);

CREATE INDEX ix_timeline_events_session_category
    ON timeline_events (
        session_id,
        event_category,
        occurred_at DESC
    );

CREATE INDEX ix_timeline_events_type
    ON timeline_events (event_type, occurred_at DESC);

CREATE TRIGGER trg_timeline_events_prevent_update
BEFORE UPDATE ON timeline_events
FOR EACH ROW
EXECUTE FUNCTION prevent_core_history_update();

CREATE TRIGGER trg_timeline_events_prevent_delete
BEFORE DELETE ON timeline_events
FOR EACH ROW
EXECUTE FUNCTION prevent_history_delete();


CREATE TABLE audit_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID,
    session_id UUID,

    actor_type actor_type_enum NOT NULL,
    actor_id UUID,

    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id UUID,

    previous_values JSONB,
    new_values JSONB,
    reason TEXT,

    request_id UUID,
    correlation_id UUID,
    job_id UUID,

    source_ip INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_audit_records_owner
        FOREIGN KEY (owner_id)
        REFERENCES users (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_audit_records_session
        FOREIGN KEY (session_id)
        REFERENCES trade_sessions (id)
        ON DELETE RESTRICT,

    CONSTRAINT ck_audit_records_action
        CHECK (BTRIM(action) <> ''),

    CONSTRAINT ck_audit_records_entity_type
        CHECK (BTRIM(entity_type) <> '')
);

CREATE INDEX ix_audit_records_session_time
    ON audit_records (session_id, created_at DESC);

CREATE INDEX ix_audit_records_entity
    ON audit_records (
        entity_type,
        entity_id,
        created_at DESC
    );

CREATE INDEX ix_audit_records_correlation
    ON audit_records (correlation_id);

CREATE INDEX ix_audit_records_job
    ON audit_records (job_id);

CREATE TRIGGER trg_audit_records_prevent_update
BEFORE UPDATE ON audit_records
FOR EACH ROW
EXECUTE FUNCTION prevent_core_history_update();

CREATE TRIGGER trg_audit_records_prevent_delete
BEFORE DELETE ON audit_records
FOR EACH ROW
EXECUTE FUNCTION prevent_history_delete();

-- ============================================================================
-- BACKGROUND JOBS AND ATTEMPTS
-- ============================================================================

CREATE TABLE background_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID,
    session_id UUID,
    analysis_request_id UUID,

    job_type job_type_enum NOT NULL,
    job_status job_status_enum NOT NULL DEFAULT 'CREATED',
    progress_stage job_progress_stage_enum,

    idempotency_key VARCHAR(255) NOT NULL,
    priority SMALLINT NOT NULL DEFAULT 100,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,

    requested_by UUID,
    payload_reference JSONB,
    result_reference JSONB,

    error_code VARCHAR(100),
    error_message TEXT,
    retryable BOOLEAN NOT NULL DEFAULT TRUE,

    queued_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    heartbeat_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_background_jobs_owner
        FOREIGN KEY (owner_id)
        REFERENCES users (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_background_jobs_session
        FOREIGN KEY (session_id)
        REFERENCES trade_sessions (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_background_jobs_request
        FOREIGN KEY (analysis_request_id)
        REFERENCES analysis_requests (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_background_jobs_requested_by
        FOREIGN KEY (requested_by)
        REFERENCES users (id)
        ON DELETE RESTRICT,

    CONSTRAINT uq_background_jobs_idempotency
        UNIQUE (idempotency_key),

    CONSTRAINT ck_background_jobs_attempts
        CHECK (
            attempt_count >= 0
            AND max_attempts >= 1
            AND attempt_count <= max_attempts
        ),

    CONSTRAINT ck_background_jobs_priority
        CHECK (priority >= 0),

    CONSTRAINT ck_background_jobs_status_timestamps
        CHECK (
            (job_status <> 'QUEUED' OR queued_at IS NOT NULL)
            AND (
                job_status NOT IN ('PROCESSING', 'RETRYING')
                OR started_at IS NOT NULL
            )
            AND (job_status <> 'COMPLETED' OR completed_at IS NOT NULL)
            AND (job_status <> 'FAILED' OR failed_at IS NOT NULL)
            AND (job_status <> 'CANCELLED' OR cancelled_at IS NOT NULL)
        )
);

CREATE INDEX ix_background_jobs_queue
    ON background_jobs (
        job_status,
        priority,
        created_at
    );

CREATE INDEX ix_background_jobs_session
    ON background_jobs (session_id, created_at DESC);

CREATE INDEX ix_background_jobs_request
    ON background_jobs (analysis_request_id);

CREATE INDEX ix_background_jobs_heartbeat
    ON background_jobs (heartbeat_at)
    WHERE job_status IN ('PROCESSING', 'RETRYING');

CREATE TRIGGER trg_background_jobs_set_updated_at
BEFORE UPDATE ON background_jobs
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();


CREATE TABLE job_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL,
    attempt_number INTEGER NOT NULL,
    provider provider_enum,
    model VARCHAR(255),

    attempt_status job_attempt_status_enum NOT NULL,
    provider_request_id TEXT,

    error_code VARCHAR(100),
    error_message TEXT,

    latency_ms BIGINT,
    input_tokens BIGINT,
    output_tokens BIGINT,
    image_count INTEGER,
    estimated_cost NUMERIC(20,8),

    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_job_attempts_job
        FOREIGN KEY (job_id)
        REFERENCES background_jobs (id)
        ON DELETE RESTRICT,

    CONSTRAINT uq_job_attempts_number
        UNIQUE (job_id, attempt_number),

    CONSTRAINT ck_job_attempts_number
        CHECK (attempt_number >= 1),

    CONSTRAINT ck_job_attempts_metrics
        CHECK (
            (latency_ms IS NULL OR latency_ms >= 0)
            AND (input_tokens IS NULL OR input_tokens >= 0)
            AND (output_tokens IS NULL OR output_tokens >= 0)
            AND (image_count IS NULL OR image_count >= 0)
            AND (estimated_cost IS NULL OR estimated_cost >= 0)
        ),

    CONSTRAINT ck_job_attempts_completed
        CHECK (
            attempt_status = 'PROCESSING'
            OR completed_at IS NOT NULL
        )
);

CREATE INDEX ix_job_attempts_job
    ON job_attempts (job_id, attempt_number DESC);

-- ============================================================================
-- TRANSACTIONAL OUTBOX
-- ============================================================================

CREATE TABLE outbox_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_type VARCHAR(100) NOT NULL,
    aggregate_id UUID NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,

    status outbox_status_enum NOT NULL DEFAULT 'PENDING',
    attempt_count INTEGER NOT NULL DEFAULT 0,
    available_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at TIMESTAMPTZ,
    last_error TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT ck_outbox_aggregate_type
        CHECK (BTRIM(aggregate_type) <> ''),

    CONSTRAINT ck_outbox_event_type
        CHECK (BTRIM(event_type) <> ''),

    CONSTRAINT ck_outbox_payload
        CHECK (jsonb_typeof(payload) = 'object'),

    CONSTRAINT ck_outbox_attempts
        CHECK (attempt_count >= 0),

    CONSTRAINT ck_outbox_published
        CHECK (
            status <> 'PUBLISHED'
            OR published_at IS NOT NULL
        )
);

CREATE INDEX ix_outbox_dispatch
    ON outbox_events (status, available_at, created_at);

CREATE INDEX ix_outbox_aggregate
    ON outbox_events (aggregate_type, aggregate_id);

CREATE TRIGGER trg_outbox_events_set_updated_at
BEFORE UPDATE ON outbox_events
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

-- ============================================================================
-- AI PROVIDER CONFIGURATION AND SETTINGS
-- ============================================================================

CREATE TABLE ai_provider_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL,
    provider provider_enum NOT NULL,
    model VARCHAR(255) NOT NULL,

    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    is_fallback BOOLEAN NOT NULL DEFAULT FALSE,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,

    supports_vision BOOLEAN NOT NULL DEFAULT FALSE,
    supports_structured_output BOOLEAN NOT NULL DEFAULT FALSE,
    supports_long_context BOOLEAN NOT NULL DEFAULT FALSE,

    encrypted_secret_reference TEXT NOT NULL,

    timeout_seconds INTEGER NOT NULL DEFAULT 120,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    temperature NUMERIC(5,4) NOT NULL DEFAULT 0.2,
    max_output_tokens INTEGER NOT NULL DEFAULT 8192,

    last_validation_status VARCHAR(32),
    last_validated_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_ai_provider_configurations_owner
        FOREIGN KEY (owner_id)
        REFERENCES users (id)
        ON DELETE RESTRICT,

    CONSTRAINT ck_ai_provider_configuration_model
        CHECK (BTRIM(model) <> ''),

    CONSTRAINT ck_ai_provider_configuration_secret
        CHECK (BTRIM(encrypted_secret_reference) <> ''),

    CONSTRAINT ck_ai_provider_configuration_roles
        CHECK (
            NOT (is_primary = TRUE AND is_fallback = TRUE)
        ),

    CONSTRAINT ck_ai_provider_configuration_timeout
        CHECK (timeout_seconds > 0),

    CONSTRAINT ck_ai_provider_configuration_attempts
        CHECK (max_attempts >= 1),

    CONSTRAINT ck_ai_provider_configuration_temperature
        CHECK (temperature >= 0 AND temperature <= 2),

    CONSTRAINT ck_ai_provider_configuration_tokens
        CHECK (max_output_tokens > 0)
);

CREATE UNIQUE INDEX uq_ai_provider_primary
    ON ai_provider_configurations (owner_id)
    WHERE is_primary = TRUE
      AND enabled = TRUE;

CREATE UNIQUE INDEX uq_ai_provider_fallback
    ON ai_provider_configurations (owner_id)
    WHERE is_fallback = TRUE
      AND enabled = TRUE;

CREATE INDEX ix_ai_provider_owner
    ON ai_provider_configurations (owner_id, enabled);

CREATE TRIGGER trg_ai_provider_configurations_set_updated_at
BEFORE UPDATE ON ai_provider_configurations
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();


CREATE TABLE application_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL,
    setting_key VARCHAR(100) NOT NULL,
    setting_value JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_application_settings_owner
        FOREIGN KEY (owner_id)
        REFERENCES users (id)
        ON DELETE RESTRICT,

    CONSTRAINT uq_application_settings_key
        UNIQUE (owner_id, setting_key),

    CONSTRAINT ck_application_settings_key
        CHECK (BTRIM(setting_key) <> '')
);

CREATE TRIGGER trg_application_settings_set_updated_at
BEFORE UPDATE ON application_settings
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

-- ============================================================================
-- AI USAGE
-- ============================================================================

CREATE TABLE ai_usage_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL,
    session_id UUID,
    job_id UUID,
    job_attempt_id UUID,
    analysis_version_id UUID,

    provider provider_enum NOT NULL,
    model VARCHAR(255) NOT NULL,
    request_type analysis_type_enum,

    input_tokens BIGINT,
    output_tokens BIGINT,
    image_count INTEGER NOT NULL DEFAULT 0,
    latency_ms BIGINT,

    estimated_cost NUMERIC(20,8),
    cost_currency currency_enum,
    pricing_version VARCHAR(64),
    request_status VARCHAR(32) NOT NULL,

    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_ai_usage_owner
        FOREIGN KEY (owner_id)
        REFERENCES users (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_ai_usage_session
        FOREIGN KEY (session_id)
        REFERENCES trade_sessions (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_ai_usage_job
        FOREIGN KEY (job_id)
        REFERENCES background_jobs (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_ai_usage_attempt
        FOREIGN KEY (job_attempt_id)
        REFERENCES job_attempts (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_ai_usage_analysis
        FOREIGN KEY (analysis_version_id)
        REFERENCES analysis_versions (id)
        ON DELETE RESTRICT,

    CONSTRAINT ck_ai_usage_model
        CHECK (BTRIM(model) <> ''),

    CONSTRAINT ck_ai_usage_metrics
        CHECK (
            (input_tokens IS NULL OR input_tokens >= 0)
            AND (output_tokens IS NULL OR output_tokens >= 0)
            AND image_count >= 0
            AND (latency_ms IS NULL OR latency_ms >= 0)
            AND (estimated_cost IS NULL OR estimated_cost >= 0)
        )
);

CREATE INDEX ix_ai_usage_owner_time
    ON ai_usage_records (owner_id, recorded_at DESC);

CREATE INDEX ix_ai_usage_session_time
    ON ai_usage_records (session_id, recorded_at DESC);

CREATE INDEX ix_ai_usage_provider_model
    ON ai_usage_records (provider, model, recorded_at DESC);

CREATE INDEX ix_ai_usage_job
    ON ai_usage_records (job_id);

CREATE TRIGGER trg_ai_usage_prevent_update
BEFORE UPDATE ON ai_usage_records
FOR EACH ROW
EXECUTE FUNCTION prevent_core_history_update();

CREATE TRIGGER trg_ai_usage_prevent_delete
BEFORE DELETE ON ai_usage_records
FOR EACH ROW
EXECUTE FUNCTION prevent_history_delete();

-- ============================================================================
-- NOTIFICATIONS
-- ============================================================================

CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL,
    session_id UUID,

    notification_type notification_type_enum NOT NULL,
    priority notification_priority_enum NOT NULL,

    title TEXT NOT NULL,
    message TEXT NOT NULL,

    related_entity_type VARCHAR(100),
    related_entity_id UUID,
    deduplication_key VARCHAR(255),

    read_at TIMESTAMPTZ,
    dismissed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_notifications_owner
        FOREIGN KEY (owner_id)
        REFERENCES users (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_notifications_session
        FOREIGN KEY (session_id)
        REFERENCES trade_sessions (id)
        ON DELETE RESTRICT,

    CONSTRAINT ck_notifications_title
        CHECK (BTRIM(title) <> ''),

    CONSTRAINT ck_notifications_message
        CHECK (BTRIM(message) <> '')
);

CREATE UNIQUE INDEX uq_notifications_active_deduplication
    ON notifications (owner_id, deduplication_key)
    WHERE deduplication_key IS NOT NULL
      AND dismissed_at IS NULL;

CREATE INDEX ix_notifications_owner_unread
    ON notifications (owner_id, created_at DESC)
    WHERE read_at IS NULL
      AND dismissed_at IS NULL;

CREATE INDEX ix_notifications_session
    ON notifications (session_id, created_at DESC);

-- ============================================================================
-- CANONICAL REFERENCE FOREIGN KEYS
-- Added after all referenced tables exist.
-- ============================================================================

ALTER TABLE trade_sessions
    ADD CONSTRAINT fk_trade_sessions_active_thesis
    FOREIGN KEY (active_thesis_id)
    REFERENCES trading_theses (id)
    DEFERRABLE INITIALLY DEFERRED
    ON DELETE RESTRICT;

ALTER TABLE trade_sessions
    ADD CONSTRAINT fk_trade_sessions_active_position
    FOREIGN KEY (active_position_id)
    REFERENCES positions (id)
    DEFERRABLE INITIALLY DEFERRED
    ON DELETE RESTRICT;

ALTER TABLE trade_sessions
    ADD CONSTRAINT fk_trade_sessions_latest_analysis
    FOREIGN KEY (latest_canonical_analysis_id)
    REFERENCES analysis_versions (id)
    DEFERRABLE INITIALLY DEFERRED
    ON DELETE RESTRICT;

ALTER TABLE trade_sessions
    ADD CONSTRAINT fk_trade_sessions_context_summary
    FOREIGN KEY (canonical_context_summary_id)
    REFERENCES context_summaries (id)
    DEFERRABLE INITIALLY DEFERRED
    ON DELETE RESTRICT;

ALTER TABLE trade_sessions
    ADD CONSTRAINT fk_trade_sessions_latest_update
    FOREIGN KEY (latest_update_id)
    REFERENCES session_updates (id)
    DEFERRABLE INITIALLY DEFERRED
    ON DELETE RESTRICT;

-- ============================================================================
-- CROSS-TABLE VALIDATION FUNCTIONS
-- ============================================================================

CREATE OR REPLACE FUNCTION validate_session_update_evidence_parent()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    update_session_id UUID;
    evidence_session_id UUID;
BEGIN
    SELECT session_id
    INTO update_session_id
    FROM session_updates
    WHERE id = NEW.session_update_id;

    SELECT session_id
    INTO evidence_session_id
    FROM evidence
    WHERE id = NEW.evidence_id;

    IF update_session_id IS NULL OR evidence_session_id IS NULL THEN
        RAISE EXCEPTION 'Session update or evidence does not exist';
    END IF;

    IF update_session_id <> evidence_session_id THEN
        RAISE EXCEPTION
            'Session update and evidence must belong to the same Trade Session'
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_session_update_evidence_same_session
BEFORE INSERT OR UPDATE ON session_update_evidence
FOR EACH ROW
EXECUTE FUNCTION validate_session_update_evidence_parent();


CREATE OR REPLACE FUNCTION validate_analysis_evidence_parent()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    analysis_session_id UUID;
    evidence_session_id UUID;
BEGIN
    SELECT session_id
    INTO analysis_session_id
    FROM analysis_versions
    WHERE id = NEW.analysis_version_id;

    SELECT session_id
    INTO evidence_session_id
    FROM evidence
    WHERE id = NEW.evidence_id;

    IF analysis_session_id IS NULL OR evidence_session_id IS NULL THEN
        RAISE EXCEPTION 'Analysis or evidence does not exist';
    END IF;

    IF analysis_session_id <> evidence_session_id THEN
        RAISE EXCEPTION
            'Analysis and evidence must belong to the same Trade Session'
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_analysis_evidence_same_session
BEFORE INSERT OR UPDATE ON analysis_evidence_links
FOR EACH ROW
EXECUTE FUNCTION validate_analysis_evidence_parent();


CREATE OR REPLACE FUNCTION validate_thesis_evidence_parent()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    thesis_session_id UUID;
    evidence_session_id UUID;
BEGIN
    SELECT session_id
    INTO thesis_session_id
    FROM trading_theses
    WHERE id = NEW.thesis_id;

    SELECT session_id
    INTO evidence_session_id
    FROM evidence
    WHERE id = NEW.evidence_id;

    IF thesis_session_id IS NULL OR evidence_session_id IS NULL THEN
        RAISE EXCEPTION 'Thesis or evidence does not exist';
    END IF;

    IF thesis_session_id <> evidence_session_id THEN
        RAISE EXCEPTION
            'Thesis and evidence must belong to the same Trade Session'
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_thesis_evidence_same_session
BEFORE INSERT OR UPDATE ON thesis_evidence_links
FOR EACH ROW
EXECUTE FUNCTION validate_thesis_evidence_parent();


CREATE OR REPLACE FUNCTION validate_trading_thesis_parent_relations()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    related_session_id UUID;
BEGIN
    IF NEW.previous_thesis_id IS NOT NULL THEN
        SELECT session_id
        INTO related_session_id
        FROM trading_theses
        WHERE id = NEW.previous_thesis_id;

        IF related_session_id <> NEW.session_id THEN
            RAISE EXCEPTION
                'Previous thesis must belong to the same Trade Session'
                USING ERRCODE = '23514';
        END IF;
    END IF;

    SELECT session_id
    INTO related_session_id
    FROM analysis_versions
    WHERE id = NEW.source_analysis_version_id;

    IF related_session_id <> NEW.session_id THEN
        RAISE EXCEPTION
            'Source analysis must belong to the same Trade Session'
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_trading_thesis_same_session
BEFORE INSERT ON trading_theses
FOR EACH ROW
EXECUTE FUNCTION validate_trading_thesis_parent_relations();


CREATE OR REPLACE FUNCTION validate_price_level_parent_relations()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    related_session_id UUID;
BEGIN
    IF NEW.analysis_version_id IS NOT NULL THEN
        SELECT session_id
        INTO related_session_id
        FROM analysis_versions
        WHERE id = NEW.analysis_version_id;

        IF related_session_id <> NEW.session_id THEN
            RAISE EXCEPTION
                'Price level analysis must belong to the same Trade Session'
                USING ERRCODE = '23514';
        END IF;
    END IF;

    IF NEW.thesis_id IS NOT NULL THEN
        SELECT session_id
        INTO related_session_id
        FROM trading_theses
        WHERE id = NEW.thesis_id;

        IF related_session_id <> NEW.session_id THEN
            RAISE EXCEPTION
                'Price level thesis must belong to the same Trade Session'
                USING ERRCODE = '23514';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

CREATE CONSTRAINT TRIGGER trg_price_level_same_session
AFTER INSERT OR UPDATE ON price_levels
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION validate_price_level_parent_relations();


CREATE OR REPLACE FUNCTION validate_trade_session_canonical_references()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    related_session_id UUID;
    related_status analysis_canonical_status_enum;
    related_validation analysis_validation_status_enum;
    related_contradiction contradiction_status_enum;
    related_position_status position_status_enum;
BEGIN
    IF NEW.active_thesis_id IS NOT NULL THEN
        SELECT session_id
        INTO related_session_id
        FROM trading_theses
        WHERE id = NEW.active_thesis_id;

        IF related_session_id IS DISTINCT FROM NEW.id THEN
            RAISE EXCEPTION
                'Active thesis must belong to the same Trade Session'
                USING ERRCODE = '23514';
        END IF;
    END IF;

    IF NEW.active_position_id IS NOT NULL THEN
        SELECT session_id, position_status
        INTO related_session_id, related_position_status
        FROM positions
        WHERE id = NEW.active_position_id;

        IF related_session_id IS DISTINCT FROM NEW.id THEN
            RAISE EXCEPTION
                'Position must belong to the same Trade Session'
                USING ERRCODE = '23514';
        END IF;
    END IF;

    IF NEW.latest_canonical_analysis_id IS NOT NULL THEN
        SELECT
            session_id,
            canonical_status,
            validation_status,
            contradiction_status
        INTO
            related_session_id,
            related_status,
            related_validation,
            related_contradiction
        FROM analysis_versions
        WHERE id = NEW.latest_canonical_analysis_id;

        IF related_session_id IS DISTINCT FROM NEW.id THEN
            RAISE EXCEPTION
                'Latest analysis must belong to the same Trade Session'
                USING ERRCODE = '23514';
        END IF;

        IF related_status <> 'ACCEPTED'
           OR related_validation NOT IN ('VALID', 'VALID_WITH_WARNINGS')
           OR related_contradiction NOT IN ('PASS', 'PASS_WITH_EXPLANATION')
        THEN
            RAISE EXCEPTION
                'Latest canonical analysis must be accepted and valid'
                USING ERRCODE = '23514';
        END IF;
    END IF;

    IF NEW.canonical_context_summary_id IS NOT NULL THEN
        SELECT session_id
        INTO related_session_id
        FROM context_summaries
        WHERE id = NEW.canonical_context_summary_id;

        IF related_session_id IS DISTINCT FROM NEW.id THEN
            RAISE EXCEPTION
                'Context summary must belong to the same Trade Session'
                USING ERRCODE = '23514';
        END IF;
    END IF;

    IF NEW.latest_update_id IS NOT NULL THEN
        SELECT session_id
        INTO related_session_id
        FROM session_updates
        WHERE id = NEW.latest_update_id;

        IF related_session_id IS DISTINCT FROM NEW.id THEN
            RAISE EXCEPTION
                'Latest update must belong to the same Trade Session'
                USING ERRCODE = '23514';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

CREATE CONSTRAINT TRIGGER trg_trade_session_canonical_references
AFTER INSERT OR UPDATE ON trade_sessions
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION validate_trade_session_canonical_references();


CREATE OR REPLACE FUNCTION validate_position_active_stop()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    stop_position_id UUID;
    stop_active BOOLEAN;
BEGIN
    IF NEW.active_stop_loss_id IS NULL THEN
        IF NEW.position_status IN ('OPEN', 'PARTIALLY_CLOSED') THEN
            RAISE EXCEPTION
                'An active Position requires an active stop loss'
                USING ERRCODE = '23514';
        END IF;

        RETURN NEW;
    END IF;

    SELECT position_id, is_active
    INTO stop_position_id, stop_active
    FROM stop_loss_versions
    WHERE id = NEW.active_stop_loss_id;

    IF stop_position_id IS DISTINCT FROM NEW.id THEN
        RAISE EXCEPTION
            'Active stop loss must belong to the same Position'
            USING ERRCODE = '23514';
    END IF;

    IF NEW.position_status IN ('OPEN', 'PARTIALLY_CLOSED')
       AND stop_active IS DISTINCT FROM TRUE
    THEN
        RAISE EXCEPTION
            'Open Position stop loss must be active'
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;

CREATE CONSTRAINT TRIGGER trg_position_active_stop
AFTER INSERT OR UPDATE ON positions
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION validate_position_active_stop();


CREATE OR REPLACE FUNCTION validate_active_position_targets()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    active_target_count INTEGER;
BEGIN
    IF NEW.position_status IN ('OPEN', 'PARTIALLY_CLOSED') THEN
        SELECT COUNT(*)
        INTO active_target_count
        FROM position_targets
        WHERE position_id = NEW.id
          AND is_active = TRUE
          AND target_status IN ('ACTIVE', 'PARTIALLY_ACHIEVED');

        IF active_target_count < 1 THEN
            RAISE EXCEPTION
                'An active Position requires at least one active target'
                USING ERRCODE = '23514';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

CREATE CONSTRAINT TRIGGER trg_position_active_targets
AFTER INSERT OR UPDATE ON positions
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION validate_active_position_targets();


CREATE OR REPLACE FUNCTION validate_trade_session_lifecycle_integrity()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    position_exists BOOLEAN;
    position_state position_status_enum;
    position_remaining NUMERIC(24,6);
    accepted_initial_analysis_exists BOOLEAN;
    active_thesis_exists BOOLEAN;
    final_exit_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1
        FROM positions
        WHERE session_id = NEW.id
    )
    INTO position_exists;

    IF position_exists THEN
        SELECT position_status, remaining_quantity
        INTO position_state, position_remaining
        FROM positions
        WHERE session_id = NEW.id;
    END IF;

    SELECT EXISTS (
        SELECT 1
        FROM analysis_versions
        WHERE session_id = NEW.id
          AND analysis_type = 'INITIAL_ANALYSIS'
          AND canonical_status = 'ACCEPTED'
          AND validation_status IN ('VALID', 'VALID_WITH_WARNINGS')
    )
    INTO accepted_initial_analysis_exists;

    SELECT EXISTS (
        SELECT 1
        FROM trading_theses
        WHERE id = NEW.active_thesis_id
          AND session_id = NEW.id
    )
    INTO active_thesis_exists;

    IF NEW.stable_status = 'WATCHING' THEN
        IF NOT accepted_initial_analysis_exists OR NOT active_thesis_exists THEN
            RAISE EXCEPTION
                'WATCHING session requires accepted initial analysis and active thesis'
                USING ERRCODE = '23514';
        END IF;

        IF position_exists THEN
            RAISE EXCEPTION
                'WATCHING session cannot contain a Position'
                USING ERRCODE = '23514';
        END IF;
    END IF;

    IF NEW.stable_status = 'OPEN_POSITION' THEN
        IF NOT position_exists OR position_state <> 'OPEN' THEN
            RAISE EXCEPTION
                'OPEN_POSITION session requires an OPEN Position'
                USING ERRCODE = '23514';
        END IF;
    END IF;

    IF NEW.stable_status = 'PARTIALLY_CLOSED' THEN
        IF NOT position_exists OR position_state <> 'PARTIALLY_CLOSED' THEN
            RAISE EXCEPTION
                'PARTIALLY_CLOSED session requires a PARTIALLY_CLOSED Position'
                USING ERRCODE = '23514';
        END IF;
    END IF;

    IF NEW.stable_status IN (
        'CLOSED_TAKE_PROFIT',
        'CLOSED_STOP_LOSS',
        'CLOSED_MANUAL'
    ) THEN
        IF NOT position_exists OR position_state <> 'CLOSED' THEN
            RAISE EXCEPTION
                'Closed Trade Session requires a CLOSED Position'
                USING ERRCODE = '23514';
        END IF;

        SELECT EXISTS (
            SELECT 1
            FROM position_exits pe
            JOIN positions p ON p.id = pe.position_id
            WHERE p.session_id = NEW.id
              AND pe.exit_type = 'FINAL'
              AND pe.corrects_exit_id IS NULL
        )
        INTO final_exit_exists;

        IF NOT final_exit_exists THEN
            RAISE EXCEPTION
                'Closed Trade Session requires a final exit'
                USING ERRCODE = '23514';
        END IF;
    END IF;

    IF NEW.stable_status = 'CANCELLED' AND position_exists THEN
        RAISE EXCEPTION
            'Cancelled Trade Session cannot contain a Position'
            USING ERRCODE = '23514';
    END IF;

    IF NEW.lifecycle_status = 'ARCHIVED'
       AND NEW.stable_status IN ('OPEN_POSITION', 'PARTIALLY_CLOSED')
    THEN
        RAISE EXCEPTION
            'An active Position cannot be archived in the MVP'
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;

CREATE CONSTRAINT TRIGGER trg_trade_session_lifecycle_integrity
AFTER INSERT OR UPDATE ON trade_sessions
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION validate_trade_session_lifecycle_integrity();


CREATE OR REPLACE FUNCTION validate_journal_eligibility()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    session_state session_status_enum;
    stable_state session_status_enum;
BEGIN
    SELECT lifecycle_status, stable_status
    INTO session_state, stable_state
    FROM trade_sessions
    WHERE id = NEW.session_id;

    IF stable_state NOT IN (
        'CLOSED_TAKE_PROFIT',
        'CLOSED_STOP_LOSS',
        'CLOSED_MANUAL'
    ) THEN
        RAISE EXCEPTION
            'Trading Journal requires a fully closed Trade Session'
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_trading_journal_eligibility
BEFORE INSERT ON trading_journals
FOR EACH ROW
EXECUTE FUNCTION validate_journal_eligibility();


CREATE OR REPLACE FUNCTION validate_position_entry_allowed()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    current_position_status position_status_enum;
    current_thesis_status thesis_status_enum;
BEGIN
    SELECT p.position_status, ts.latest_thesis_status
    INTO current_position_status, current_thesis_status
    FROM positions p
    JOIN trade_sessions ts ON ts.id = p.session_id
    WHERE p.id = NEW.position_id;

    IF current_position_status = 'CLOSED' THEN
        RAISE EXCEPTION
            'Cannot add an entry to a closed Position'
            USING ERRCODE = '23514';
    END IF;

    IF NEW.entry_type = 'ADDITIONAL'
       AND current_thesis_status = 'INVALIDATED'
    THEN
        RAISE EXCEPTION
            'Cannot add an entry while the thesis is invalidated'
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_position_entry_allowed
BEFORE INSERT ON position_entries
FOR EACH ROW
EXECUTE FUNCTION validate_position_entry_allowed();


CREATE OR REPLACE FUNCTION validate_exit_quantity()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    current_remaining NUMERIC(24,6);
    current_status position_status_enum;
BEGIN
    SELECT remaining_quantity, position_status
    INTO current_remaining, current_status
    FROM positions
    WHERE id = NEW.position_id
    FOR UPDATE;

    IF current_status = 'CLOSED' THEN
        RAISE EXCEPTION
            'Cannot add an exit to a closed Position'
            USING ERRCODE = '23514';
    END IF;

    IF NEW.quantity IS NOT NULL
       AND current_remaining IS NOT NULL
       AND NEW.quantity > current_remaining
    THEN
        RAISE EXCEPTION
            'Exit quantity exceeds remaining Position quantity'
            USING ERRCODE = '23514';
    END IF;

    IF NEW.exit_type = 'PARTIAL'
       AND NEW.quantity IS NOT NULL
       AND current_remaining IS NOT NULL
       AND NEW.quantity >= current_remaining
    THEN
        RAISE EXCEPTION
            'Partial exit quantity must be less than remaining quantity'
            USING ERRCODE = '23514';
    END IF;

    IF NEW.exit_type = 'FINAL'
       AND NEW.quantity IS NOT NULL
       AND current_remaining IS NOT NULL
       AND NEW.quantity <> current_remaining
    THEN
        RAISE EXCEPTION
            'Final exit quantity must equal remaining quantity'
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_exit_quantity
BEFORE INSERT ON position_exits
FOR EACH ROW
EXECUTE FUNCTION validate_exit_quantity();

-- ============================================================================
-- INITIAL EVIDENCE READINESS VIEW
-- ============================================================================

CREATE VIEW session_initial_evidence_readiness_view AS
SELECT
    ts.id AS session_id,
    COUNT(*) FILTER (
        WHERE e.evidence_type = 'ORDERBOOK_SCREENSHOT'
          AND e.evidence_status = 'AVAILABLE'
          AND e.deleted_at IS NULL
    ) AS orderbook_count,
    COUNT(*) FILTER (
        WHERE e.evidence_type = 'CHART_THREE_MONTH'
          AND e.evidence_status = 'AVAILABLE'
          AND e.deleted_at IS NULL
    ) AS chart_three_month_count,
    COUNT(*) FILTER (
        WHERE e.evidence_type = 'CHART_SIX_MONTH'
          AND e.evidence_status = 'AVAILABLE'
          AND e.deleted_at IS NULL
    ) AS chart_six_month_count,
    (
        COUNT(*) FILTER (
            WHERE e.evidence_type = 'ORDERBOOK_SCREENSHOT'
              AND e.evidence_status = 'AVAILABLE'
              AND e.deleted_at IS NULL
        ) >= 1
        AND
        COUNT(*) FILTER (
            WHERE e.evidence_type = 'CHART_THREE_MONTH'
              AND e.evidence_status = 'AVAILABLE'
              AND e.deleted_at IS NULL
        ) >= 1
        AND
        COUNT(*) FILTER (
            WHERE e.evidence_type = 'CHART_SIX_MONTH'
              AND e.evidence_status = 'AVAILABLE'
              AND e.deleted_at IS NULL
        ) >= 1
    ) AS is_ready
FROM trade_sessions ts
LEFT JOIN evidence e
    ON e.session_id = ts.id
GROUP BY ts.id;

-- ============================================================================
-- READ VIEWS
-- ============================================================================

CREATE VIEW active_trade_sessions_view AS
SELECT
    ts.id AS session_id,
    ts.owner_id,
    ts.ticker,
    ts.company_name,
    ts.market,
    ts.currency,
    ts.title,
    ts.lifecycle_status,
    ts.stable_status,
    ts.latest_thesis_status,
    ts.latest_confidence_score,
    ts.latest_target_probability,
    ts.latest_risk_level,
    ts.latest_recommended_action,
    ts.latest_market_price,
    ts.last_analysis_at,
    ts.updated_at,

    p.id AS position_id,
    p.position_status,
    p.weighted_average_entry,
    p.total_entry_quantity,
    p.remaining_quantity,
    p.realized_profit_loss,
    p.unrealized_profit_loss,
    p.total_profit_loss,
    p.return_percentage,

    sl.price AS active_stop_loss,

    (
        SELECT pt.price
        FROM position_targets pt
        WHERE pt.position_id = p.id
          AND pt.is_active = TRUE
          AND pt.target_status IN ('ACTIVE', 'PARTIALLY_ACHIEVED')
        ORDER BY pt.priority ASC, pt.price ASC
        LIMIT 1
    ) AS nearest_active_target

FROM trade_sessions ts
LEFT JOIN positions p
    ON p.id = ts.active_position_id
LEFT JOIN stop_loss_versions sl
    ON sl.id = p.active_stop_loss_id
WHERE ts.lifecycle_status <> 'ARCHIVED'
  AND ts.stable_status IN (
      'DRAFT',
      'READY_FOR_ANALYSIS',
      'WATCHING',
      'OPEN_POSITION',
      'PARTIALLY_CLOSED'
  );


CREATE VIEW session_analysis_history_view AS
SELECT
    av.id AS analysis_version_id,
    av.session_id,
    av.version_number,
    av.analysis_type,
    av.generated_at,
    av.canonical_status,
    av.validation_status,
    av.provider,
    av.model,
    av.prompt_version,
    av.schema_version,
    av.contradiction_status,

    tt.thesis_status,
    tt.directional_bias,
    tt.confidence_score,

    (
        SELECT apa.percentage
        FROM analysis_probability_assessments apa
        WHERE apa.analysis_version_id = av.id
          AND apa.probability_type = 'TARGET_ACHIEVEMENT'
        LIMIT 1
    ) AS target_probability

FROM analysis_versions av
LEFT JOIN trading_theses tt
    ON tt.source_analysis_version_id = av.id;


CREATE VIEW position_performance_view AS
SELECT
    p.id AS position_id,
    p.session_id,
    p.position_status,
    p.weighted_average_entry,
    p.total_entry_quantity,
    p.remaining_quantity,
    p.realized_proceeds,
    p.realized_profit_loss,
    p.unrealized_profit_loss,
    p.total_profit_loss,
    p.return_percentage,
    p.opened_at,
    p.closed_at,

    EXTRACT(
        EPOCH FROM (
            COALESCE(p.closed_at, NOW()) - p.opened_at
        )
    ) / 86400.0 AS holding_duration_days,

    (
        SELECT
            CASE
                WHEN SUM(pe.quantity) IS NULL
                     OR SUM(pe.quantity) = 0
                THEN NULL
                ELSE
                    SUM(pe.price * pe.quantity)
                    / SUM(pe.quantity)
            END
        FROM position_exits pe
        WHERE pe.position_id = p.id
          AND pe.exit_type <> 'CORRECTION'
    ) AS weighted_average_exit

FROM positions p;


CREATE VIEW ai_usage_monthly_view AS
SELECT
    owner_id,
    DATE_TRUNC('month', recorded_at) AS usage_month,
    provider,
    model,
    COUNT(*) AS request_count,
    COALESCE(SUM(input_tokens), 0) AS input_tokens,
    COALESCE(SUM(output_tokens), 0) AS output_tokens,
    COALESCE(SUM(image_count), 0) AS image_count,
    COALESCE(SUM(estimated_cost), 0) AS estimated_cost,
    cost_currency
FROM ai_usage_records
GROUP BY
    owner_id,
    DATE_TRUNC('month', recorded_at),
    provider,
    model,
    cost_currency;

-- ============================================================================
-- DATA-INTEGRITY INSPECTION VIEW
-- This view does not replace application/domain validation.
-- ============================================================================

CREATE VIEW database_integrity_issues_view AS

SELECT
    ts.id AS session_id,
    'ARCHIVED_WITHOUT_PREVIOUS_STATUS'::TEXT AS issue_code,
    'Archived Trade Session does not preserve a previous status'::TEXT
        AS issue_description
FROM trade_sessions ts
WHERE ts.lifecycle_status = 'ARCHIVED'
  AND ts.pre_archive_status IS NULL

UNION ALL

SELECT
    ts.id,
    'WATCHING_WITHOUT_CANONICAL_ANALYSIS',
    'Watching Trade Session does not have a canonical analysis'
FROM trade_sessions ts
WHERE ts.stable_status = 'WATCHING'
  AND ts.latest_canonical_analysis_id IS NULL

UNION ALL

SELECT
    ts.id,
    'WATCHING_WITHOUT_ACTIVE_THESIS',
    'Watching Trade Session does not have an active thesis'
FROM trade_sessions ts
WHERE ts.stable_status = 'WATCHING'
  AND ts.active_thesis_id IS NULL

UNION ALL

SELECT
    p.session_id,
    'ACTIVE_POSITION_WITHOUT_ACTIVE_STOP',
    'Active Position does not have an active stop loss'
FROM positions p
WHERE p.position_status IN ('OPEN', 'PARTIALLY_CLOSED')
  AND p.active_stop_loss_id IS NULL

UNION ALL

SELECT
    p.session_id,
    'ACTIVE_POSITION_WITHOUT_TARGET',
    'Active Position does not have an active target'
FROM positions p
WHERE p.position_status IN ('OPEN', 'PARTIALLY_CLOSED')
  AND NOT EXISTS (
      SELECT 1
      FROM position_targets pt
      WHERE pt.position_id = p.id
        AND pt.is_active = TRUE
        AND pt.target_status IN ('ACTIVE', 'PARTIALLY_ACHIEVED')
  )

UNION ALL

SELECT
    p.session_id,
    'CLOSED_POSITION_WITH_REMAINING_QUANTITY',
    'Closed Position still has remaining quantity'
FROM positions p
WHERE p.position_status = 'CLOSED'
  AND p.remaining_quantity IS NOT NULL
  AND p.remaining_quantity <> 0

UNION ALL

SELECT
    ts.id,
    'CANCELLED_SESSION_WITH_POSITION',
    'Cancelled Trade Session contains a Position'
FROM trade_sessions ts
WHERE ts.stable_status = 'CANCELLED'
  AND EXISTS (
      SELECT 1
      FROM positions p
      WHERE p.session_id = ts.id
  )

UNION ALL

SELECT
    ts.id,
    'STALE_PROCESSING_JOB',
    'Trade Session has a processing job without a recent heartbeat'
FROM trade_sessions ts
WHERE EXISTS (
    SELECT 1
    FROM background_jobs bj
    WHERE bj.session_id = ts.id
      AND bj.job_status IN ('PROCESSING', 'RETRYING')
      AND (
          bj.heartbeat_at IS NULL
          OR bj.heartbeat_at < NOW() - INTERVAL '10 minutes'
      )
);

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE trade_sessions IS
'Canonical identity and current state of one complete trade story.';

COMMENT ON TABLE evidence IS
'Metadata for uploaded screenshots, structured evidence, and user notes.';

COMMENT ON TABLE analysis_versions IS
'Immutable normalized AI analysis results.';

COMMENT ON COLUMN analysis_versions.structured_payload IS
'Schema-versioned structured AI output with English keys and Indonesian narrative values.';

COMMENT ON TABLE trading_theses IS
'Immutable versions of the session trading thesis.';

COMMENT ON TABLE positions IS
'Canonical user-executed position state for one Trade Session.';

COMMENT ON TABLE position_entries IS
'Append-only actual entry transactions.';

COMMENT ON TABLE position_exits IS
'Append-only partial, final, and correction exit transactions.';

COMMENT ON TABLE stop_loss_versions IS
'Versioned user-confirmed stop-loss records.';

COMMENT ON TABLE position_targets IS
'Versioned user-confirmed target records.';

COMMENT ON TABLE trading_journals IS
'Immutable AI Trading Journal versions generated after position closure.';

COMMENT ON TABLE timeline_events IS
'User-visible chronological events for one Trade Session.';

COMMENT ON TABLE audit_records IS
'Technical audit history for authoritative mutations.';

COMMENT ON TABLE background_jobs IS
'Authoritative PostgreSQL job state; Redis is only the execution queue.';

COMMENT ON TABLE outbox_events IS
'Transactional outbox used for reliable asynchronous dispatch.';

-- ============================================================================
-- END
-- ============================================================================

COMMIT;
```
