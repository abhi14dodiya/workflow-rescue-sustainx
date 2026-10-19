param([ValidateRange(1, 65535)][int]$Port = 8080)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the virtual environment.' }
    & '.\.venv\Scripts\python.exe' -m pip install -r requirements-dev.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
}
# Build an isolated child environment; preserve the caller's console and
# machine/user credential settings for unrelated projects.
$RescueStartInfo = New-Object System.Diagnostics.ProcessStartInfo
$RescueStartInfo.FileName = (Resolve-Path -LiteralPath '.venv\Scripts\python.exe').Path
$RescueStartInfo.Arguments = "-m uvicorn app.main:app --host 127.0.0.1 --port $Port"
$RescueStartInfo.WorkingDirectory = $ProjectRoot
$RescueStartInfo.UseShellExecute = $false
$RescueStartInfo.CreateNoWindow = $true
$RescueSettings = @('GEMINI_API_KEY', 'GEMINI_MODEL', 'DEFAULT_PROVIDER', 'FIRESTORE_PROJECT_ID',
    'DEMO_ACCESS_TOKEN', 'MAX_MODEL_CALLS_PER_HOUR', 'MAX_ACTIVE_RUNS', 'PORT')
foreach ($RescueName in @($RescueStartInfo.EnvironmentVariables.Keys)) {
    if ($RescueName -notin $RescueSettings -and
        ($RescueName -match 'API_?KEY|ACCESS_?TOKEN|AUTH_?TOKEN|PASSWORD|SECRET|PRIVATE_KEY' -or
         $RescueName -match '_(BASE_URL|DEPLOYMENT|MODEL|API_VERSION|ENDPOINT)$')) {
        $RescueStartInfo.EnvironmentVariables.Remove($RescueName)
    }
}
$RescueStartInfo.EnvironmentVariables['DEFAULT_PROVIDER'] = 'gemini'
$RescueProcess = New-Object System.Diagnostics.Process
$RescueProcess.StartInfo = $RescueStartInfo
$RescueStarted = $false
try {
    $RescueStarted = $RescueProcess.Start()
    if (-not $RescueStarted) { throw 'Could not start the local Gemini application.' }
    while (-not $RescueProcess.WaitForExit(500)) { }
    $RescueExitCode = $RescueProcess.ExitCode
} finally {
    if ($RescueStarted -and -not $RescueProcess.HasExited) { $RescueProcess.Kill() }
    $RescueProcess.Dispose()
}
exit $RescueExitCode

