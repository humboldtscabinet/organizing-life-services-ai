-- Add performance indexes to existing tables
-- Run inside ols-postgres container:
-- docker exec -i ols-postgres psql -U ols_user -d ols_db < data/add_indexes.sql

-- GSC Data indexes (critical for content gap analysis)
CREATE INDEX IF NOT EXISTS ix_gsc_data_date ON gsc_data (date);
CREATE INDEX IF NOT EXISTS ix_gsc_data_query ON gsc_data (query);
CREATE INDEX IF NOT EXISTS ix_gsc_data_query_date ON gsc_data (query, date);
CREATE INDEX IF NOT EXISTS ix_gsc_data_query_page_date ON gsc_data (query, page, date);

-- GA4 Data indexes
CREATE INDEX IF NOT EXISTS ix_ga4_data_date ON ga4_data (date);
CREATE INDEX IF NOT EXISTS ix_ga4_data_metric_date ON ga4_data (metric_name, date);
CREATE INDEX IF NOT EXISTS ix_ga4_data_metric_dim_date ON ga4_data (metric_name, dimension_value, date);

-- Google Ads Data indexes
CREATE INDEX IF NOT EXISTS ix_google_ads_data_date ON google_ads_data (date);
CREATE INDEX IF NOT EXISTS ix_google_ads_data_campaign_date ON google_ads_data (campaign_name, date);

-- Dashboard Tasks indexes
CREATE INDEX IF NOT EXISTS ix_dashboard_tasks_status ON dashboard_tasks (status);
CREATE INDEX IF NOT EXISTS ix_dashboard_tasks_type_status ON dashboard_tasks (task_type, status);
