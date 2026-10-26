[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$GameDir,
    [string]$OutputDir = ''
)

$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $scriptDir
$version = '0.6.1'
if (-not $OutputDir) {
    $OutputDir = Join-Path $root 'release'
} elseif (-not [System.IO.Path]::IsPathRooted($OutputDir)) {
    $OutputDir = Join-Path $root $OutputDir
}
$buildRoot = [System.IO.Path]::GetFullPath((Join-Path $root 'build')).TrimEnd('\') + '\'
$stage = [System.IO.Path]::GetFullPath((Join-Path $root 'build\manaka-npc-voices-manual'))
if (-not ($stage + '\').StartsWith($buildRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to recreate staging path outside build directory: $stage"
}

& (Join-Path $scriptDir 'build_plugin.ps1') -GameDir $GameDir
if ($LASTEXITCODE -ne 0) { throw "NPC voice plugin build failed: $LASTEXITCODE" }

if (Test-Path -LiteralPath $stage) {
    Remove-Item -LiteralPath $stage -Recurse -Force
}
$pluginStage = Join-Path $stage 'BepInEx\plugins\ManakaNpcVoices'
$voiceStage = Join-Path $pluginStage 'VoicePacks'
New-Item -ItemType Directory -Force -Path $voiceStage | Out-Null

Copy-Item -LiteralPath (Join-Path $scriptDir 'bin\ManakaNpcVoices.dll') -Destination $pluginStage -Force
Copy-Item -LiteralPath (Join-Path $scriptDir 'VOICE_PACK_README.txt') -Destination (Join-Path $voiceStage 'README.txt') -Force
Copy-Item -LiteralPath (Join-Path $scriptDir 'MANUAL_INSTALL_CN.txt') -Destination (Join-Path $stage 'README_FIRST_CN.txt') -Force
Copy-Item -LiteralPath (Join-Path $scriptDir 'MANUAL_INSTALL_EN.txt') -Destination (Join-Path $stage 'README_FIRST_EN.txt') -Force

$sourceVoiceRoot = Join-Path $scriptDir 'VoicePacks'
$japaneseWavs = @(Get-ChildItem -LiteralPath (Join-Path $sourceVoiceRoot 'ja') -Recurse -File -Filter '*.wav')
if ($japaneseWavs.Count -ne 90) { throw "Expected 90 Japanese runtime WAVs, found $($japaneseWavs.Count)." }
foreach ($source in $japaneseWavs) {
    $relative = $source.FullName.Substring($sourceVoiceRoot.Length).TrimStart('\')
    $destination = Join-Path $voiceStage $relative
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
    Copy-Item -LiteralPath $source.FullName -Destination $destination -Force
}

foreach ($language in @('zh', 'ja', 'en')) {
    foreach ($state in @('ambient', 'phone', 'watching', 'alert', 'found', 'failure', 'aftermath')) {
        $source = Join-Path $scriptDir "SubtitleLines\$language\$state.txt"
        $destination = Join-Path $voiceStage "$language\$state\lines.txt"
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
        Copy-Item -LiteralPath $source -Destination $destination -Force
    }
    Copy-Item -LiteralPath (Join-Path $scriptDir "SubtitleProfiles\$language.txt") -Destination (Join-Path $voiceStage "$language\profiles.txt") -Force
}

$bridge = Join-Path $scriptDir 'bin\ManakaNpcVoices.CustomMissions2.dll'
if (Test-Path -LiteralPath $bridge -PathType Leaf) {
    # Keep the optional bridge as one loose DLL. A second nested BepInEx tree
    # looked like an alternative installer and made it easy to install only
    # the bridge while omitting the required core plugin and voice pack.
    $optionalPluginDir = Join-Path $stage '_OPTIONAL_CM2_PHONE_PAGE'
    New-Item -ItemType Directory -Force -Path $optionalPluginDir | Out-Null
    Copy-Item -LiteralPath $bridge -Destination $optionalPluginDir -Force
    Copy-Item -LiteralPath (Join-Path $scriptDir 'OPTIONAL_CM2_README.txt') -Destination (Join-Path $optionalPluginDir 'README.txt') -Force
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$zip = Join-Path $OutputDir "ManakaNpcVoices-v$version-manual.zip"
if (Test-Path -LiteralPath $zip) { Remove-Item -LiteralPath $zip -Force }
Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $zip -CompressionLevel Optimal
$hash = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -LiteralPath ($zip + '.sha256') -Value "$hash  $([System.IO.Path]::GetFileName($zip))" -Encoding ASCII
Write-Host "Manual package: $zip"
Write-Host "Japanese reaction WAVs: $($japaneseWavs.Count)"
