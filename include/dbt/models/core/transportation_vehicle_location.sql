select md5(concat_ws('|', rv.vehicle_sk, dvm.latitude, dvm.longitude, dvm.recorded_at_time)) as vehicle_location_sk, 
    rv.vehicle_sk as fk_vehicle_sk, 
    rl.line_sk as fk_line_sk, 
    dvm.latitude, 
    dvm.longitude, 
    dvm.recorded_at_time as vehicle_location_dtm, 
    dvm.valid_until_time,
    dvm.line_ref,
    dvm.direction,
    dvm.vehicle_status,
    dvm.delay,
    dvm.stop_point_ref,

    -- Métadonnées SIRI
    dvm.response_timestamp,
    dvm.producer_ref,
    dvm.response_message_identifier,
    dvm.more_data,
    dvm.siri_version,
    current_timestamp as load_dtm,
    current_timestamp as update_dtm
from {{ source( 'std-data-grand-lyon', 'std_datagrandlyon_vehicle_monitoring') }} as dvm
left join {{ ref('ref_transportation_vehicles') }} as rv on dvm.vehicle_ref = rv.ak_vehicle_ref
left join {{ ref('ref_transportation_line') }} as rl on dvm.line_ref = rl.ak_line_id