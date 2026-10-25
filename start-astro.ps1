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

astro dev start --compose-file compose.yaml
if ($LASTEXITCODE -ne 0) {
    throw "astro dev start failed with exit code $LASTEXITCODE."
}
