create or replace table stg_feature_exposures as
select
    cast(exposure_id as integer) as exposure_id,
    lower(trim(experiment_name)) as experiment_name,
    cast(user_id as integer) as user_id,
    lower(trim(variant)) as variant,
    lower(trim(surface)) as surface,
    cast(exposed_at as timestamp) as exposed_at
from raw_feature_exposures;
