[CmdletBinding()]
param(
    [switch]$Docker,
    [ValidateRange(1, 65535)][int]$Port = 8765
)
$ErrorActionPreference = 'Stop'
$selectedPython = $null
$selectedPrefix = @()
foreach ($candidate in @('py', 'python3', 'python')) {
    $command = Get-Command $candidate -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $command) { continue }
    $prefix = @()
    if ($candidate -eq 'py') { $prefix = @('-3') }
    try {
        & $command.Source @prefix -c 'import sys; raise SystemExit(sys.version_info < (3, 11))' 2>$null
        if ($LASTEXITCODE -eq 0) {
            $selectedPython = $command.Source
            $selectedPrefix = $prefix
            break
        }
    } catch { continue }
}
if ($null -eq $selectedPython) {
    Write-Error 'Python 3.11 ou superior nao encontrado.'
    exit 1
}
$arguments = @($selectedPrefix) + @((Join-Path $PSScriptRoot 'scripts/service.py'), 'start', '--port', [string]$Port)
if ($Docker) { $arguments += '--docker' }
& $selectedPython @arguments
exit $LASTEXITCODE
