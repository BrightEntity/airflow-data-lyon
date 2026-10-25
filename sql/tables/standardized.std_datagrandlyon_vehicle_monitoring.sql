CREATE SCHEMA IF NOT EXISTS standardized;

CREATE TABLE IF NOT EXISTS standardized.std_datagrandlyon_vehicle_monitoring (
    vehicle_monitoring_sk BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- Clé métier
    vehicle_ref TEXT NOT NULL,

    -- Données de supervision du véhicule
    valid_until_time TIMESTAMPTZ,
    recorded_at_time TIMESTAMPTZ,
    line_ref TEXT,
    direction TEXT,
    vehicle_status TEXT,
    delay TEXT,
    longitude NUMERIC(12, 8),
    latitude NUMERIC(12, 8),
    stop_point_ref TEXT,

    -- Métadonnées SIRI
    response_timestamp TIMESTAMPTZ,
    producer_ref TEXT,
    response_message_identifier TEXT,
    more_data BOOLEAN,
    siri_version TEXT,

    -- SCD Type 2
    valid_from TIMESTAMPTZ NOT NULL,
    valid_to TIMESTAMPTZ,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,

    -- Contrôle technique
    attribute_hash TEXT NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),

    CONSTRAINT chk_vehicle_monitoring_validity
        CHECK (valid_to IS NULL OR valid_to >= valid_from)
);

-- Une seule version courante par véhicule.
CREATE UNIQUE INDEX IF NOT EXISTS
    uq_std_datagrandlyon_vehicle_monitoring_current
ON standardized.std_datagrandlyon_vehicle_monitoring (vehicle_ref)
WHERE is_current = TRUE;

CREATE INDEX IF NOT EXISTS
    ix_std_datagrandlyon_vehicle_monitoring_history
ON standardized.std_datagrandlyon_vehicle_monitoring
    (vehicle_ref, valid_from DESC);

