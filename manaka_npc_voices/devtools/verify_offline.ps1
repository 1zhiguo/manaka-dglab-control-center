$ErrorActionPreference = "Stop"
$pluginRoot = Split-Path -Parent $PSScriptRoot
$sourcePaths = @(
    (Join-Path $pluginRoot "Plugin.cs"),
    (Join-Path $pluginRoot "CustomMissions2PhoneBridge.cs")
)
$binaryPaths = @(
    (Join-Path $pluginRoot "bin\ManakaNpcVoices.dll"),
    (Join-Path $pluginRoot "bin\ManakaNpcVoices.CustomMissions2.dll")
)

$forbidden = @(
    "System.Net",
    "HttpClient",
    "WebRequest",
    "WebSocket",
    "TcpClient",
    "UdpClient",
    "Socket",
    "api_key",
    "apikey",
    "access_token"
)

foreach ($sourcePath in $sourcePaths) {
    if (-not (Test-Path -LiteralPath $sourcePath)) { continue }
    $source = Get-Content -LiteralPath $sourcePath -Raw
    foreach ($token in $forbidden) {
        if ($source.IndexOf($token, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) {
            throw "Offline policy violation in source $sourcePath`: $token"
        }
    }
}

foreach ($binaryPath in $binaryPaths) {
    if (-not (Test-Path -LiteralPath $binaryPath)) { continue }
    $bytes = [System.IO.File]::ReadAllBytes($binaryPath)
    $ascii = [System.Text.Encoding]::ASCII.GetString($bytes)
    foreach ($token in $forbidden) {
        if ($ascii.IndexOf($token, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) {
            throw "Offline policy violation in binary $binaryPath`: $token"
        }
    }
}

Write-Host "Offline policy verified: no network/API symbols found in runtime source or DLL."
