-- 04_audit_tables.sql
-- Audit layer - quality checks, failures, and bad records

CREATE TABLE IF NOT EXISTS audit.pipeline_runs (
    run_id BIGSERIAL PRIMARY KEY,
    run_date DATE NOT NULL,
    dag_id VARCHAR(256),
    task_id VARCHAR(256),
    execution_date TIMESTAMP NOT NULL,
    status VARCHAR(50) NOT NULL,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    duration_seconds INTEGER,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pipeline_runs_run_date ON audit.pipeline_runs(run_date);
CREATE INDEX idx_pipeline_runs_status ON audit.pipeline_runs(status);
CREATE INDEX idx_pipeline_runs_execution_date ON audit.pipeline_runs(execution_date);

COMMENT ON TABLE audit.pipeline_runs IS 'Track all DAG and task executions with status and timing';


CREATE TABLE IF NOT EXISTS audit.dq_failures (
    dq_failure_id BIGSERIAL PRIMARY KEY,
    run_date DATE NOT NULL,
    check_name VARCHAR(256) NOT NULL,
    check_type VARCHAR(100) NOT NULL,
    failed_count INTEGER,
    failure_message TEXT,
    details JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_dq_failures_run_date ON audit.dq_failures(run_date);
CREATE INDEX idx_dq_failures_check_name ON audit.dq_failures(check_name);

COMMENT ON TABLE audit.dq_failures IS 'Log all data quality check failures with details';


CREATE TABLE IF NOT EXISTS audit.bad_records (
    bad_record_id BIGSERIAL PRIMARY KEY,
    run_date DATE NOT NULL,
    source_table VARCHAR(256),
    record_id VARCHAR(256),
    failure_reason TEXT,
    failed_value TEXT,
    raw_data JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_bad_records_run_date ON audit.bad_records(run_date);
CREATE INDEX idx_bad_records_source_table ON audit.bad_records(source_table);

COMMENT ON TABLE audit.bad_records IS 'Store individual bad records that fail quality checks';
