param(
    [Parameter(Mandatory = $true)]
    [string]$GameDir,
    [switch]$Deploy,
    [switch]$SkipBridge
)

$ErrorActionPreference = "Stop"
$compiler = "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe"
if (-not (Test-Path -LiteralPath $compiler)) { throw "C# compiler not found: $compiler" }

$gameDir = (Resolve-Path -LiteralPath $GameDir).Path
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$outputDir = Join-Path $scriptDir "bin"
$outputDll = Join-Path $outputDir "ManakaNpcVoices.dll"
$bridgeDll = Join-Path $outputDir "ManakaNpcVoices.CustomMissions2.dll"
$responseFile = Join-Path $outputDir "compiler.rsp"
$bridgeResponseFile = Join-Path $outputDir "compiler_cm2_bridge.rsp"
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

$references = @(
    "dotnet\System.Private.CoreLib.dll",
    "dotnet\mscorlib.dll",
    "dotnet\System.Runtime.dll",
    "dotnet\netstandard.dll",
    "dotnet\System.Console.dll",
    "dotnet\System.Collections.dll",
    "dotnet\System.IO.dll",
    "dotnet\System.IO.FileSystem.dll",
    "dotnet\System.IO.FileSystem.Primitives.dll",
    "BepInEx\core\BepInEx.Core.dll",
    "BepInEx\core\BepInEx.Unity.Common.dll",
    "BepInEx\core\BepInEx.Unity.IL2CPP.dll",
    "BepInEx\core\Il2CppInterop.Runtime.dll",
    "BepInEx\core\0Harmony.dll",
    "BepInEx\interop\Assembly-CSharp.dll",
    "BepInEx\interop\Il2Cppmscorlib.dll",
    "BepInEx\interop\UnityEngine.dll",
    "BepInEx\interop\UnityEngine.CoreModule.dll",
    "BepInEx\interop\UnityEngine.AudioModule.dll",
    "BepInEx\interop\UnityEngine.TextRenderingModule.dll",
    "BepInEx\interop\UnityEngine.UIModule.dll",
    "BepInEx\interop\UnityEngine.UI.dll"
) | ForEach-Object { Join-Path $gameDir $_ }

foreach ($reference in $references) {
    if (-not (Test-Path -LiteralPath $reference)) { throw "Required reference not found: $reference" }
}

$response = @(
    "/nostdlib+",
    "/target:library",
    "/optimize+",
    "/debug-",
    "/langversion:latest",
    "/out:`"$outputDll`""
)
$response += $references | ForEach-Object { "/reference:`"$_`"" }
$response += "`"$(Join-Path $scriptDir 'Plugin.cs')`""
Set-Content -LiteralPath $responseFile -Value $response -Encoding UTF8

& $compiler "/noconfig" "@$responseFile"
if ($LASTEXITCODE -ne 0) { throw "Plugin compilation failed with exit code $LASTEXITCODE" }
Write-Host "Built: $outputDll"

$cm2Dll = Join-Path $gameDir "BepInEx\plugins\SFM_custom_mission_v2.dll"
if (-not $SkipBridge -and (Test-Path -LiteralPath $cm2Dll)) {
    $bridgeReferences = $references + @(
        (Join-Path $gameDir "BepInEx\interop\Unity.TextMeshPro.dll"),
        $cm2Dll,
        $outputDll
    )
    foreach ($reference in $bridgeReferences) {
        if (-not (Test-Path -LiteralPath $reference)) { throw "Bridge reference not found: $reference" }
    }
    $bridgeResponse = @(
        "/nostdlib+",
        "/target:library",
        "/optimize+",
        "/debug-",
        "/langversion:latest",
        "/out:`"$bridgeDll`""
    )
    $bridgeResponse += $bridgeReferences | ForEach-Object { "/reference:`"$_`"" }
    $bridgeResponse += "`"$(Join-Path $scriptDir 'CustomMissions2PhoneBridge.cs')`""
    Set-Content -LiteralPath $bridgeResponseFile -Value $bridgeResponse -Encoding UTF8

    & $compiler "/noconfig" "@$bridgeResponseFile"
    if ($LASTEXITCODE -ne 0) { throw "CM2 phone bridge compilation failed with exit code $LASTEXITCODE" }
    Write-Host "Built: $bridgeDll"
} else {
    if (Test-Path -LiteralPath $bridgeDll -PathType Leaf) {
        Remove-Item -LiteralPath $bridgeDll -Force
    }
    Write-Warning "Custom Missions 2 phone bridge was skipped."
}

if ($Deploy) {
    $pluginDir = Join-Path $gameDir "BepInEx\plugins\ManakaNpcVoices"
    $voiceDir = Join-Path $pluginDir "VoicePacks"
    New-Item -ItemType Directory -Force -Path $pluginDir | Out-Null
    Copy-Item -LiteralPath $outputDll -Destination (Join-Path $pluginDir "ManakaNpcVoices.dll") -Force
    if (-not $SkipBridge -and (Test-Path -LiteralPath $bridgeDll)) {
        Copy-Item -LiteralPath $bridgeDll -Destination (Join-Path $pluginDir "ManakaNpcVoices.CustomMissions2.dll") -Force
    } else {
        $staleBridge = Join-Path $pluginDir "ManakaNpcVoices.CustomMissions2.dll"
        if (Test-Path -LiteralPath $staleBridge -PathType Leaf) {
            Remove-Item -LiteralPath $staleBridge -Force
        }
    }
    foreach ($language in @("zh", "ja", "en")) {
        foreach ($state in @("ambient", "phone", "watching", "alert", "found", "failure", "aftermath")) {
            New-Item -ItemType Directory -Force -Path (Join-Path $voiceDir "$language\$state") | Out-Null
        }
    }
    $bundledVoiceDir = Join-Path $scriptDir "VoicePacks"
    $subtitleDir = Join-Path $scriptDir "SubtitleLines"
    $profileSubtitleDir = Join-Path $scriptDir "SubtitleProfiles"
    if (-not (Test-Path -LiteralPath $bundledVoiceDir)) {
        throw "Missing bundled voice directory: $bundledVoiceDir"
    }
    # Clean only obsolete assets previously owned by this installer. Never touch
    # lines.txt, profiles.txt, or arbitrary custom WAV names.
    if (Test-Path -LiteralPath $voiceDir) {
        Get-ChildItem -LiteralPath $voiceDir -Recurse -File | Where-Object {
            ($_.FullName -match '[\\/](zh|en)[\\/].*\\voice_[ab]_\d{2}\.wav$') -or
            ($_.Name -match '^voice_[ab]_\d{2}\.txt$') -or
            ($_.Name -eq '.fish_voice_ids.local.json')
        } | Remove-Item -Force
    }
    $japaneseVoiceDir = Join-Path $bundledVoiceDir 'ja'
    $japaneseWavs = @(Get-ChildItem -LiteralPath $japaneseVoiceDir -Recurse -File -Filter '*.wav')
    if ($japaneseWavs.Count -ne 90) {
        throw "Expected 90 Japanese voice WAVs, found $($japaneseWavs.Count): $japaneseVoiceDir"
    }
    foreach ($source in $japaneseWavs) {
        $relative = $source.FullName.Substring($bundledVoiceDir.Length).TrimStart('\')
        $destination = Join-Path $voiceDir $relative
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
        Copy-Item -LiteralPath $source.FullName -Destination $destination -Force
    }
    foreach ($language in @("zh", "ja", "en")) {
        foreach ($state in @("ambient", "phone", "watching", "alert", "found", "failure", "aftermath")) {
            $subtitleSource = Join-Path $subtitleDir "$language\$state.txt"
            if (-not (Test-Path -LiteralPath $subtitleSource -PathType Leaf)) {
                throw "Missing bundled subtitle file: $subtitleSource"
            }
            Copy-Item -LiteralPath $subtitleSource -Destination (Join-Path $voiceDir "$language\$state\lines.txt") -Force
        }
        $profileSubtitleSource = Join-Path $profileSubtitleDir "$language.txt"
        if (-not (Test-Path -LiteralPath $profileSubtitleSource -PathType Leaf)) {
            throw "Missing bundled profile subtitle file: $profileSubtitleSource"
        }
        Copy-Item -LiteralPath $profileSubtitleSource -Destination (Join-Path $voiceDir "$language\profiles.txt") -Force
    }
    Copy-Item -LiteralPath (Join-Path $scriptDir "VOICE_PACK_README.txt") -Destination (Join-Path $voiceDir "README.txt") -Force
    Write-Host "Deployed: $pluginDir"
    Write-Host "Restart the game so BepInEx can load the plugin."
}

foreach ($generatedResponse in @($responseFile, $bridgeResponseFile)) {
    if (Test-Path -LiteralPath $generatedResponse -PathType Leaf) {
        Remove-Item -LiteralPath $generatedResponse -Force
    }
}
