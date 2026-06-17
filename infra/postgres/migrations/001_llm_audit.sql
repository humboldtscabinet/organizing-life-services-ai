-- Add durable audit records for model routing and high-stakes review.
-- Run against existing Mac mini/laptop volumes; init.sql only applies to
-- brand-new Postgres volumes.

CREATE TABLE IF NOT EXISTS llm_audit (
    id                  SERIAL PRIMARY KEY,
    task_type           VARCHAR(100) NOT NULL,
    risk_level          VARCHAR(30) NOT NULL,
    model_role          VARCHAR(50) NOT NULL,
    provider            VARCHAR(50) NOT NULL,
    model               VARCHAR(200) NOT NULL,
    status              VARCHAR(50) NOT NULL,
    verdict             VARCHAR(30),
    prompt_tokens       INTEGER,
    completion_tokens   INTEGER,
    total_tokens        INTEGER,
    estimated_cost_usd  DOUBLE PRECISION,
    input_refs          JSONB,
    request             JSONB,
    response            JSONB,
    error               TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_llm_audit_task_created
    ON llm_audit (task_type, created_at);
CREATE INDEX IF NOT EXISTS ix_llm_audit_risk_status
    ON llm_audit (risk_level, status);
