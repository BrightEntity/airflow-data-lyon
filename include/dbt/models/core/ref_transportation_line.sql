with core as (
    select
        md5(dvm.line_ref) as line_sk,
        dvm.line_ref as ak_line_id,
        current_timestamp as load_dtm,
        current_timestamp as update_dtm,
        row_number() over (partition by dvm.line_ref order by dvm.recorded_at_time desc) as rn
    from {{ source('std-data-grand-lyon', 'std_datagrandlyon_vehicle_monitoring') }} as dvm
    where dvm.is_current = true
)
select
    line_sk,
    ak_line_id,
    load_dtm,
    update_dtm
from core
where rn = 1