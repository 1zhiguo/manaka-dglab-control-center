[CmdletBinding()]
param(
    [string]$DistPath = ''
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $root 'python\.venv\Scripts\python.exe'
$entry = Join-Path $root 'python\qml_dashboard_prototype\main.py'
$qml = Join-Path $root 'python\qml_dashboard_prototype\ControlCenter.qml'
$qmlAssets = Join-Path $root 'python\qml_dashboard_prototype\assets'
$appVersionFile = Join-Path $root 'python\qml_dashboard_prototype\VERSION'
$appIconPng = Join-Path $root 'python\qml_dashboard_prototype\assets\app_icon.png'
$appIconIco = Join-Path $root 'python\qml_dashboard_prototype\assets\app_icon.ico'
$plugin = Join-Path $root 'manaka_telemetry\bin\ManakaDGLabTelemetry.dll'
$bepinexPayload = Join-Path $root 'installer_payload\bepinex_v113'
$guideAssets = Join-Path $root 'python\assets\dglab_guide'
$npcVoiceCore = Join-Path $root 'manaka_npc_voices\bin\ManakaNpcVoices.dll'
$npcVoiceBridge = Join-Path $root 'manaka_npc_voices\bin\ManakaNpcVoices.CustomMissions2.dll'
$npcVoicePacks = Join-Path $root 'manaka_npc_voices\VoicePacks'
$npcSubtitleLines = Join-Path $root 'manaka_npc_voices\SubtitleLines'
$npcSubtitleProfiles = Join-Path $root 'manaka_npc_voices\SubtitleProfiles'
$npcVoiceReadme = Join-Path $root 'manaka_npc_voices\VOICE_PACK_README.txt'
$npcVoicePayload = Join-Path $root 'build\npc_voice_payload'
$dropInTemplate = Join-Path $root 'dropin_mods'
if (-not $DistPath) {
    $buildVersion = (Get-Content -LiteralPath $appVersionFile -Raw).Trim()
    if (-not $buildVersion) { throw 'VERSION must not be empty.' }
    $DistPath = Join-Path $root "release\build-$buildVersion-qml"
}
elseif (-not [System.IO.Path]::IsPathRooted($DistPath)) {
    $DistPath = Join-Path $root $DistPath
}
$portable = Join-Path $DistPath 'ManakaQmlControlCenter'

foreach ($required in @($python, $entry, $qml, $qmlAssets, $appVersionFile, $appIconPng, $appIconIco, $plugin, $bepinexPayload, $guideAssets, $npcVoiceCore, $npcVoiceBridge, $npcVoicePacks, $npcSubtitleLines, $npcSubtitleProfiles, $npcVoiceReadme, $dropInTemplate)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Missing build input: $required"
    }
}

# Stage only Japanese runtime WAVs. Subtitle text is copied from the editable
# source files below; generation manifests and API tooling stay developer-only.
$buildRoot = [System.IO.Path]::GetFullPath((Join-Path $root 'build')).TrimEnd('\') + '\'
$payloadRoot = [System.IO.Path]::GetFullPath($npcVoicePayload)
if (-not ($payloadRoot + '\').StartsWith($buildRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to recreate NPC voice payload outside build directory: $payloadRoot"
}
if (Test-Path -LiteralPath $payloadRoot) {
    Remove-Item -LiteralPath $payloadRoot -Recurse -Force
}
New-Item -ItemType Directory -Force -Path (Join-Path $payloadRoot 'bin') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $payloadRoot 'VoicePacks') | Out-Null
Copy-Item -LiteralPath $npcVoiceCore -Destination (Join-Path $payloadRoot 'bin\ManakaNpcVoices.dll') -Force
Copy-Item -LiteralPath $npcVoiceBridge -Destination (Join-Path $payloadRoot 'bin\ManakaNpcVoices.CustomMissions2.dll') -Force
Copy-Item -LiteralPath $npcVoiceReadme -Destination (Join-Path $payloadRoot 'VOICE_PACK_README.txt') -Force
$japaneseVoiceRoot = Join-Path $npcVoicePacks 'ja'
$runtimeVoiceFiles = @(Get-ChildItem -LiteralPath $japaneseVoiceRoot -Recurse -File -Filter '*.wav')
if ($runtimeVoiceFiles.Count -ne 90) {
    throw "Expected 90 Japanese NPC voice WAVs, found $($runtimeVoiceFiles.Count): $japaneseVoiceRoot"
}
foreach ($source in $runtimeVoiceFiles) {
    $relative = $source.FullName.Substring($npcVoicePacks.Length).TrimStart('\')
    $destination = Join-Path (Join-Path $payloadRoot 'VoicePacks') $relative
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
    Copy-Item -LiteralPath $source.FullName -Destination $destination -Force
}
foreach ($language in @('zh', 'ja', 'en')) {
    foreach ($state in @('ambient', 'phone', 'watching', 'alert', 'found', 'failure', 'aftermath')) {
        $subtitleSource = Join-Path $npcSubtitleLines "$language\$state.txt"
        if (-not (Test-Path -LiteralPath $subtitleSource -PathType Leaf)) {
            throw "Missing bundled NPC subtitle file: $subtitleSource"
        }
        $subtitleDestination = Join-Path $payloadRoot "VoicePacks\$language\$state\lines.txt"
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $subtitleDestination) | Out-Null
        Copy-Item -LiteralPath $subtitleSource -Destination $subtitleDestination -Force
    }
    $profileSubtitleSource = Join-Path $npcSubtitleProfiles "$language.txt"
    if (-not (Test-Path -LiteralPath $profileSubtitleSource -PathType Leaf)) {
        throw "Missing bundled NPC profile subtitle file: $profileSubtitleSource"
    }
    Copy-Item -LiteralPath $profileSubtitleSource -Destination (Join-Path $payloadRoot "VoicePacks\$language\profiles.txt") -Force
}

& $python -c 'import PyInstaller, PySide6'
if ($LASTEXITCODE -ne 0) {
    throw 'PyInstaller or PySide6 is not installed in python\.venv.'
}

Push-Location $root
try {
    & $python -m PyInstaller `
        --noconfirm `
        --clean `
        --windowed `
        --onedir `
        --name 'ManakaQmlControlCenter' `
        --icon $appIconIco `
        --distpath $DistPath `
        --workpath (Join-Path $root 'build\qml') `
        --specpath (Join-Path $root 'build') `
        --paths (Join-Path $root 'python') `
        --add-data "$qml;qml" `
        --add-data "$appIconPng;assets" `
        --add-data "$appVersionFile;assets" `
        --add-data "$qmlAssets;qml\assets" `
        --add-data "$plugin;assets" `
        --add-data "$bepinexPayload;assets\bepinex_v113" `
        --add-data "$guideAssets;assets\dglab_guide" `
        --add-data "$npcVoicePayload;assets\ManakaNpcVoices" `
        $entry
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller QML build failed.' }

    # Qt's generic QML hook also bundles WebEngine/PDF modules even though this
    # controller never imports them. Remove only these explicitly named modules
    # from the newly generated portable directory to save roughly 200 MB.
    $portableRoot = [System.IO.Path]::GetFullPath($portable).TrimEnd('\') + '\'
    $unusedQtItems = @(
        '_internal\PySide6\Qt6WebEngineCore.dll',
        '_internal\PySide6\Qt6WebEngineQuick.dll',
        '_internal\PySide6\Qt6WebEngineQuickDelegatesQml.dll',
        '_internal\PySide6\Qt6WebView.dll',
        '_internal\PySide6\Qt6WebViewQuick.dll',
        '_internal\PySide6\Qt6Pdf.dll',
        '_internal\PySide6\Qt6PdfQuick.dll',
        '_internal\PySide6\qml\QtWebEngine',
        '_internal\PySide6\qml\QtWebView',
        '_internal\PySide6\qml\QtQuick\Pdf',
        # PyInstaller can pick these up from a Poppler directory on PATH.
        # QtCore on current Windows expects the OS ICU compatibility DLLs;
        # bundling Poppler's ICU 78 under these unversioned names breaks import.
        '_internal\icuuc.dll',
        '_internal\icudt78.dll'
    )
    foreach ($relativeItem in $unusedQtItems) {
        $candidate = [System.IO.Path]::GetFullPath((Join-Path $portable $relativeItem))
        if (-not ($candidate + '\').StartsWith($portableRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to prune path outside portable build: $candidate"
        }
        if (Test-Path -LiteralPath $candidate) {
            Remove-Item -LiteralPath $candidate -Recurse -Force
        }
    }

    # Python 3.11 may contribute an older VC++ runtime to `_internal` than the
    # one used to build the current PySide6 wheels. Because the bootloader loads
    # the root copy first, QtCore then fails with "specified procedure could not
    # be found". Keep one consistent, backward-compatible runtime version.
    $qtRuntimeDir = Join-Path $portable '_internal\PySide6'
    $runtimeTargetDir = Join-Path $portable '_internal'
    foreach ($runtimeName in @('VCRUNTIME140.dll', 'VCRUNTIME140_1.dll', 'MSVCP140.dll', 'MSVCP140_1.dll', 'MSVCP140_2.dll')) {
        $runtimeSource = Join-Path $qtRuntimeDir $runtimeName
        if (-not (Test-Path -LiteralPath $runtimeSource)) {
            throw "Missing PySide6 runtime dependency: $runtimeSource"
        }
        Copy-Item -LiteralPath $runtimeSource -Destination (Join-Path $runtimeTargetDir $runtimeName) -Force
    }

    Copy-Item -LiteralPath (Join-Path $root 'QUICKSTART_CN.md') -Destination (Join-Path $portable 'QUICKSTART_CN.md') -Force
    Copy-Item -LiteralPath (Join-Path $root 'QUICKSTART_EN.md') -Destination (Join-Path $portable 'QUICKSTART_EN.md') -Force
    Copy-Item -LiteralPath (Join-Path $root 'FAQ_CN.md') -Destination (Join-Path $portable 'FAQ_CN.md') -Force
    Copy-Item -LiteralPath (Join-Path $root 'FAQ_EN.md') -Destination (Join-Path $portable 'FAQ_EN.md') -Force
    Copy-Item -LiteralPath (Join-Path $root 'THIRD_PARTY_NOTICES.md') -Destination (Join-Path $portable 'THIRD_PARTY_NOTICES.md') -Force
    Copy-Item -LiteralPath (Join-Path $root 'USER_AGREEMENT_CN.md') -Destination (Join-Path $portable 'USER_AGREEMENT_CN.md') -Force
    Copy-Item -LiteralPath (Join-Path $root 'MOD_CONTENT_NOTICE_CN.md') -Destination (Join-Path $portable 'MOD_CONTENT_NOTICE_CN.md') -Force

    # Third-party plugins and missions are intentionally not redistributed.
    # Never copy the whole local Drop-in tree: ignored repository/archive files
    # may contain a maintainer's private test imports. Ship only the documented
    # empty inbox; the importer creates repository, archive, and staging folders
    # on first launch.
    $portableDropIn = Join-Path $portable 'dropin_mods'
    New-Item -ItemType Directory -Force -Path (Join-Path $portableDropIn 'incoming') | Out-Null
    Copy-Item -LiteralPath (Join-Path $dropInTemplate 'README.txt') -Destination (Join-Path $portableDropIn 'README.txt') -Force

    $smokeProcess = Start-Process -FilePath (Join-Path $portable 'ManakaQmlControlCenter.exe') `
        -ArgumentList '--demo', '--smoke-test' `
        -PassThru `
        -Wait `
        -WindowStyle Hidden
    if ($smokeProcess.ExitCode -ne 0) {
        throw "Packaged QML smoke test failed with exit code $($smokeProcess.ExitCode)."
    }
    Write-Host "Built QML portable app: $portable"
    Write-Host 'Share the entire folder as a ZIP; users run ManakaQmlControlCenter.exe.'
}
finally {
    Pop-Location
}
