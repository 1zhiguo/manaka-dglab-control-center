[CmdletBinding()]
param(
    [ValidateSet('', 'zh', 'ja', 'en')]
    [string]$Language = '',

    [ValidateSet('', 'phone', 'watching', 'alert', 'found', 'failure')]
    [string]$State = '',

    [switch]$Force,
    [switch]$DryRun,
    [switch]$ResetApiKey,
    [string]$Manifest = '',
    [string]$Output = '',
    [string]$CredentialPath = ''
)

$ErrorActionPreference = 'Stop'
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repositoryRoot = Split-Path -Parent (Split-Path -Parent $scriptRoot)
$venvPython = Join-Path $repositoryRoot 'python\.venv\Scripts\python.exe'
$python = if (Test-Path -LiteralPath $venvPython) { $venvPython } else { 'python' }
$generator = Join-Path $scriptRoot 'generate_voice_pack.py'
$keySetupScript = Join-Path $scriptRoot 'save_fish_api_key.ps1'
if (-not $CredentialPath) {
    $CredentialPath = Join-Path $env:LOCALAPPDATA 'ManakaDGLab\fish_audio_api_key.clixml'
}

if ($ResetApiKey -and (Test-Path -LiteralPath $CredentialPath)) {
    Remove-Item -LiteralPath $CredentialPath -Force
}

$temporaryApiKey = $false
$keyPointer = [IntPtr]::Zero
if (-not $DryRun -and ($ResetApiKey -or [string]::IsNullOrWhiteSpace($env:FISH_API_KEY))) {
    if (-not (Test-Path -LiteralPath $CredentialPath)) {
        & $keySetupScript -CredentialPath $CredentialPath
    }
    try {
        $credential = Import-Clixml -LiteralPath $CredentialPath
        if ($credential -isnot [System.Management.Automation.PSCredential]) {
            throw 'The saved credential has an unexpected format.'
        }
        $keyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($credential.Password)
        $env:FISH_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPointer)
    }
    catch {
        throw "Unable to read the saved Fish Audio API Key. Run again with -ResetApiKey. $($_.Exception.Message)"
    }
    $temporaryApiKey = $true
}

$arguments = @($generator)
if ($Manifest) { $arguments += @('--manifest', $Manifest) }
if ($Language) { $arguments += @('--language', $Language) }
if ($State) { $arguments += @('--state', $State) }
if ($Output) { $arguments += @('--output', $Output) }
if ($Force) { $arguments += '--force' }
if ($DryRun) { $arguments += '--dry-run' }

try {
    & $python @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Fish Audio batch generation failed with exit code: $LASTEXITCODE"
    }
}
finally {
    if ($keyPointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPointer)
    }
    if ($temporaryApiKey) {
        Remove-Item Env:FISH_API_KEY -ErrorAction SilentlyContinue
    }
}
