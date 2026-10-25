docker compose -f compose.streamlit.yaml up -d --build
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$containerId = docker compose -f compose.streamlit.yaml ps -q streamlit
if ($LASTEXITCODE -ne 0 -or -not $containerId) {
    throw "Impossible de trouver le conteneur Streamlit."
}

$networkName = "airflow-data-lyon_12d0e0_airflow"
$networks = docker inspect --format '{{json .NetworkSettings.Networks}}' $containerId | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if ($networks.PSObject.Properties.Name -notcontains $networkName) {
    docker network connect $networkName $containerId
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
