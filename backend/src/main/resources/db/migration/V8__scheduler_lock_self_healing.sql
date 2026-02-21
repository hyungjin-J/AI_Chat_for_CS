ALTER TABLE tb_scheduler_lock
    ADD COLUMN IF NOT EXISTS last_heartbeat_utc TIMESTAMP NULL;

ALTER TABLE tb_scheduler_lock
    ADD COLUMN IF NOT EXISTS last_recovered_at TIMESTAMP NULL;

ALTER TABLE tb_scheduler_lock
    ADD COLUMN IF NOT EXISTS recovery_count BIGINT NOT NULL DEFAULT 0;

UPDATE tb_scheduler_lock
SET last_heartbeat_utc = COALESCE(last_heartbeat_utc, updated_at)
WHERE last_heartbeat_utc IS NULL;

CREATE INDEX IF NOT EXISTS idx_tb_scheduler_lock_lease_heartbeat
    ON tb_scheduler_lock (lease_until_utc, last_heartbeat_utc);
