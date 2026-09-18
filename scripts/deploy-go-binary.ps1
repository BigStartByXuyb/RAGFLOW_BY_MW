<#
.SYNOPSIS
  Build RAGFlow's Go server in WSL and deploy the resulting binary.

.EXAMPLES
  .\scripts\deploy-go-binary.ps1 -Sync              # sync source, build, deploy into the local WSL container
  .\scripts\deploy-go-binary.ps1 -Target server     # build, then deploy to the remote dev server
  .\scripts\deploy-go-binary.ps1 -SkipBuild         # deploy the binary that was built last time
#>
param(
    [ValidateSet('local', 'server')]
    [string]$Target = 'local',
    [string]$WslDistro = 'ragflow',
    [string]$Container = 'ragflow-dev-ragflow-cpu-1',
    [string]$Server = 'ctyun@10.101.0.62',
    [switch]$Sync,
    [switch]$SkipBuild
)

$ErrorActionPreference = 'Stop'
$binary = '/root/build/ragflow/bin/ragflow_server'

if (-not $SkipBuild) {
    Write-Host '>>> building the Linux binary in WSL ...' -ForegroundColor Cyan
    if ($Sync) {
        wsl -d $WslDistro -u root -e bash /root/build/ragflow-build.sh --sync
    } else {
        wsl -d $WslDistro -u root -e bash /root/build/ragflow-build.sh
    }
    if ($LASTEXITCODE -ne 0) { throw "build failed (exit $LASTEXITCODE)" }
}

if ($Target -eq 'local') {
    Write-Host ">>> installing into the WSL container '$Container'" -ForegroundColor Cyan
    wsl -d $WslDistro -u root -e bash -lc "docker cp $binary ${Container}:/ragflow/bin/ragflow_server && docker restart $Container"
    if ($LASTEXITCODE -ne 0) { throw "local deploy failed (exit $LASTEXITCODE)" }
    Write-Host '>>> done: the WSL RAGFlow container is running the new binary' -ForegroundColor Green
}
else {
    Write-Host ">>> uploading $binary to $Server (password prompt expected)" -ForegroundColor Cyan
    wsl -d $WslDistro -u root -e bash -lc "scp -O $binary ${Server}:/tmp/ragflow_server"
    if ($LASTEXITCODE -ne 0) { throw "upload failed (exit $LASTEXITCODE)" }

    Write-Host ">>> installing into '$Container' on $Server" -ForegroundColor Cyan
    ssh $Server "docker cp /tmp/ragflow_server $Container:/ragflow/bin/ragflow_server && docker restart $Container"
    if ($LASTEXITCODE -ne 0) { throw "remote deploy failed (exit $LASTEXITCODE)" }
    Write-Host '>>> done: the remote container is running the new binary' -ForegroundColor Green
}
