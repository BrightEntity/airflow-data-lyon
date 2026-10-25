$ErrorActionPreference = "Stop"

Get-Content .env | ForEach-Object {          
         if ($_ -match '^\s*([^#][^=]*)=(.*)$') {
         $name = $matches[1].Trim()
         $value = $matches[2].Trim()
         [Environment]::SetEnvironmentVariable(
             $name,
             $value,
             'Process'
         )
     }
 }

$projectName = "airflow-data-lyon"
$garageContainer = "garaged"

astro dev start --compose-file compose.yaml
if ($LASTEXITCODE -ne 0) {
    throw "astro dev start failed with exit code $LASTEXITCODE."
}

$garageStatus = docker inspect --format "{{.State.Running}}" $garageContainer 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "Docker container '$garageContainer' was not found."
}

if ($garageStatus -ne "true") {
    docker start $garageContainer
    if ($LASTEXITCODE -ne 0) {
        throw "Could not start Docker container '$garageContainer'."
    }
}

$candidateNetworks = docker network ls --filter "name=$projectName" --format "{{.Name}}" |
    Where-Object { $_ -match "^$([regex]::Escape($projectName))_.+_airflow$" }

$airflowNetwork = $null
foreach ($candidateNetwork in $candidateNetworks) {
    $networkInfo = docker network inspect $candidateNetwork | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) {
        continue
    }

    foreach ($endpoint in $networkInfo[0].Containers.PSObject.Properties) {
        $member = (docker inspect $endpoint.Name | ConvertFrom-Json)[0]
        if (
            $member.State.Running -and
            $member.Name -match "^/$([regex]::Escape($projectName))_"
        ) {
            $airflowNetwork = $candidateNetwork
            break
        }
    }

    if ($airflowNetwork) {
        break
    }
}

if (-not $airflowNetwork) {
    throw "Could not find the active Astro Docker network for project '$projectName'."
}

$networkInfo = (docker network inspect $airflowNetwork | ConvertFrom-Json)[0]
$garageEndpoint = $networkInfo.Containers.PSObject.Properties |
    Where-Object { $_.Value.Name -eq $garageContainer } |
    Select-Object -First 1

if ($garageEndpoint -and $garageEndpoint.Value.Aliases -contains "garaged") {
    Write-Host "Garage is already connected to '$airflowNetwork' as 'garaged'."
    exit 0
}

if ($garageEndpoint) {
    docker network disconnect $airflowNetwork $garageContainer
    if ($LASTEXITCODE -ne 0) {
        throw "Could not disconnect '$garageContainer' from '$airflowNetwork'."
    }
}

docker network connect --alias garaged $airflowNetwork $garageContainer
if ($LASTEXITCODE -ne 0) {
    throw "Could not connect '$garageContainer' to '$airflowNetwork'."
}

Write-Host "Garage connected to '$airflowNetwork' as 'garaged'."
