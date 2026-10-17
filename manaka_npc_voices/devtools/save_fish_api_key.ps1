[CmdletBinding()]
param(
    [string]$CredentialPath = ''
)

$ErrorActionPreference = 'Stop'
if (-not $CredentialPath) {
    $CredentialPath = Join-Path $env:LOCALAPPDATA 'ManakaDGLab\fish_audio_api_key.clixml'
}

$secureKey = Read-Host 'Paste Fish Audio API Key (stored encrypted for this Windows user)' -AsSecureString
$keyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
try {
    $plainKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPointer)
    if ([string]::IsNullOrWhiteSpace($plainKey) -or $plainKey.Length -lt 8) {
        throw 'The API Key is empty or too short.'
    }
}
finally {
    if ($keyPointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPointer)
    }
    $plainKey = $null
}

$parent = Split-Path -Parent $CredentialPath
New-Item -ItemType Directory -Path $parent -Force | Out-Null
$credential = [System.Management.Automation.PSCredential]::new('FishAudio', $secureKey)
$credential | Export-Clixml -LiteralPath $CredentialPath -Force
Write-Host "Fish Audio API Key saved for the current Windows user: $CredentialPath"
