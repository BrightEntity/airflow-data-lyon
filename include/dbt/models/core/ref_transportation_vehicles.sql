WITH ranked_vehicles AS (
    SELECT
        md5(dvm.vehicle_ref) AS vehicle_sk,
        dvm.vehicle_ref AS ak_vehicle_ref,
        CURRENT_TIMESTAMP AS load_dtm,
        CURRENT_TIMESTAMP AS update_dtm,
        ROW_NUMBER() OVER (
            PARTITION BY dvm.vehicle_ref
            ORDER BY dvm.recorded_at_time DESC
        ) AS rn
    FROM {{ source('std-data-grand-lyon', 'std_datagrandlyon_vehicle_monitoring') }} AS dvm
    where dvm.is_current = true
)
SELECT
    vehicle_sk,
    ak_vehicle_ref,
    load_dtm,
    update_dtm
FROM ranked_vehicles
WHERE rn = 1