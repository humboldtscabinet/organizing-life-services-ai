-- Add image analysis records used by the vision workflow.
-- Existing volumes do not re-run init.sql, so keep this migration idempotent.

CREATE TABLE IF NOT EXISTS image_analysis (
    id              SERIAL PRIMARY KEY,
    image_url       VARCHAR(1000) NOT NULL,
    filename        VARCHAR(500),
    gallery_name    VARCHAR(300),
    alt_text        TEXT,
    title           VARCHAR(500),
    item_tags       JSONB,
    description     TEXT,
    confidence      DOUBLE PRECISION,
    status          VARCHAR(50) DEFAULT 'pending',
    data            JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_image_analysis_status
    ON image_analysis (status);
CREATE INDEX IF NOT EXISTS ix_image_analysis_gallery_name
    ON image_analysis (gallery_name);
CREATE INDEX IF NOT EXISTS ix_image_analysis_image_url
    ON image_analysis (image_url);
CREATE INDEX IF NOT EXISTS ix_image_analysis_status_gallery
    ON image_analysis (status, gallery_name);
