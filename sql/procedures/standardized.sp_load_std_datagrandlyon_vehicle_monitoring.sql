CREATE OR REPLACE PROCEDURE
    standardized.sp_load_std_datagrandlyon_vehicle_monitoring()
LANGUAGE plpgsql
AS $procedure$
DECLARE
    v_load_time TIMESTAMPTZ := clock_timestamp();
BEGIN
    -- Évite deux chargements concurrents de cette même cible.
    PERFORM pg_advisory_xact_lock(
        hashtext('standardized.std_datagrandlyon_vehicle_monitoring')
    );

    DROP TABLE IF EXISTS pg_temp.tmp_vehicle_monitoring;

    CREATE TEMP TABLE pg_temp.tmp_vehicle_monitoring
    ON COMMIT DROP
    AS
    WITH extracted AS (
        SELECT
            vehicle ->> 'ValidUntilTime'
                AS valid_until_time_text,

            vehicle ->> 'RecordedAtTime'
                AS recorded_at_time_text,

            journey #>> '{VehicleRef,value}'
                AS vehicle_ref,

            journey #>> '{LineRef,value}'
                AS line_ref,

            journey #>> '{DirectionRef,value}'
                AS direction,

            journey ->> 'VehicleStatus'
                AS vehicle_status,

            journey ->> 'Delay'
                AS delay,

            NULLIF(
                journey #>> '{VehicleLocation,Longitude}', ''
            )::NUMERIC(12, 8)
                AS longitude,

            NULLIF(
                journey #>> '{VehicleLocation,Latitude}', ''
            )::NUMERIC(12, 8)
                AS latitude,

            journey #>> '{MonitoredCall,StopPointRef,value}'
                AS stop_point_ref,

            nullif(svm."Siri.ServiceDelivery.ResponseTimestamp", '')::timestamptz
                AS response_timestamp,

            svm."Siri.ServiceDelivery.ProducerRef.value"
                AS producer_ref,

            svm."Siri.ServiceDelivery.ResponseMessageIdentifier.value"
                AS response_message_identifier,

            NULLIF(
                svm."Siri.ServiceDelivery.MoreData"::TEXT, ''
            )::BOOLEAN
                AS more_data,

            svm."Siri.version"::TEXT
                AS siri_version

        FROM staging.stg_vehicle_monitoring AS svm

        CROSS JOIN LATERAL jsonb_array_elements(
            svm."Siri.ServiceDelivery.VehicleMonitoringDelivery"::JSONB
        ) AS delivery(item)

        CROSS JOIN LATERAL jsonb_array_elements(
            COALESCE(
                delivery.item -> 'VehicleActivity',
                '[]'::JSONB
            )
        ) AS activity(vehicle)

        CROSS JOIN LATERAL (
            SELECT
                activity.vehicle -> 'MonitoredVehicleJourney'
                    AS journey
        ) AS j

        WHERE activity.vehicle ? 'MonitoredVehicleJourney'
          AND j.journey #>> '{VehicleRef,value}' IS NOT NULL
    ),

    typed AS (
        SELECT
            NULLIF(valid_until_time_text, '')::TIMESTAMPTZ
                AS valid_until_time,

            NULLIF(recorded_at_time_text, '')::TIMESTAMPTZ
                AS recorded_at_time,

            vehicle_ref,
            line_ref,
            direction,
            vehicle_status,
            delay,
            longitude,
            latitude,
            stop_point_ref,
            response_timestamp,
            producer_ref,
            response_message_identifier,
            more_data,
            siri_version

        FROM extracted
    ),

    deduplicated AS (
        SELECT DISTINCT ON (vehicle_ref)
            *
        FROM typed
        ORDER BY
            vehicle_ref,
            recorded_at_time DESC NULLS LAST,
            response_timestamp DESC NULLS LAST
    )

    SELECT
        d.*,

        -- Seuls les attributs métier suivis déclenchent
        -- une nouvelle version SCD2.
        md5(
            jsonb_build_object(
                'line_ref',       d.line_ref,
                'direction',      d.direction,
                'vehicle_status', d.vehicle_status,
                'delay',          d.delay,
                'longitude',      d.longitude,
                'latitude',       d.latitude,
                'stop_point_ref', d.stop_point_ref
            )::TEXT
        ) AS attribute_hash

    FROM deduplicated AS d;

    -- 1. Clôturer les versions courantes dont les attributs
    -- métier ont changé.
    UPDATE standardized.std_datagrandlyon_vehicle_monitoring AS target
    SET
        valid_to = v_load_time,
        is_current = FALSE
    FROM tmp_vehicle_monitoring AS source
    WHERE target.vehicle_ref = source.vehicle_ref
      AND target.is_current = TRUE
      AND target.attribute_hash <> source.attribute_hash;

    -- 2. Insérer les véhicules nouveaux et les nouvelles versions.
    INSERT INTO standardized.std_datagrandlyon_vehicle_monitoring (
        vehicle_ref,
        valid_until_time,
        recorded_at_time,
        line_ref,
        direction,
        vehicle_status,
        delay,
        longitude,
        latitude,
        stop_point_ref,
        response_timestamp,
        producer_ref,
        response_message_identifier,
        more_data,
        siri_version,
        valid_from,
        valid_to,
        is_current,
        attribute_hash,
        loaded_at
    )
    SELECT
        source.vehicle_ref,
        source.valid_until_time,
        source.recorded_at_time,
        source.line_ref,
        source.direction,
        source.vehicle_status,
        source.delay,
        source.longitude,
        source.latitude,
        source.stop_point_ref,
        source.response_timestamp,
        source.producer_ref,
        source.response_message_identifier,
        source.more_data,
        source.siri_version,
        v_load_time,
        NULL,
        TRUE,
        source.attribute_hash,
        v_load_time
    FROM tmp_vehicle_monitoring AS source
    WHERE NOT EXISTS (
        SELECT 1
        FROM standardized.std_datagrandlyon_vehicle_monitoring AS target
        WHERE target.vehicle_ref = source.vehicle_ref
          AND target.is_current = TRUE
          AND target.attribute_hash = source.attribute_hash
    );

    DROP TABLE IF EXISTS pg_temp.tmp_vehicle_monitoring;

END;
$procedure$;