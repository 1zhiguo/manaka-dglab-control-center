[CmdletBinding()]
param(
    [string]$DistPath = ''
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $root 'python\.venv\Scripts\python.exe'
$entry = Join-Path $root 'python\qml_dashboard_prototype\main.py'
$qml = Join-Path $root 'python\qml_dashboard_prototype\ControlCenter.qml'
$appIconPng = Join-Path $root 'python\qml_dashboard_prototype\assets\app_icon.png'
$appIconIco = Join-Path $root 'python\qml_dashboard_prototype\assets\app_icon.ico'
$plugin = Join-Path $root 'manaka_telemetry\bin\ManakaDGLabTelemetry.dll'
$bepinexPayload = Join-Path $root 'installer_payload\bepinex_v113'
$guideAssets = Join-Path $root 'python\assets\dglab_guide'
$modRepositories = Join-Path $root 'mod_repositories'
$dropInTemplate = Join-Path $root 'dropin_mods'
if (-not $DistPath) {
    $DistPath = Join-Path $root 'release\build-v0.24.4-qml'
}
elseif (-not [System.IO.Path]::IsPathRooted($DistPath)) {
    $DistPath = Join-Path $root $DistPath
}
$portable = Join-Path $DistPath 'ManakaQmlControlCenter'

foreach ($required in @($python, $entry, $qml, $appIconPng, $appIconIco, $plugin, $bepinexPayload, $guideAssets, $modRepositories, $dropInTemplate)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Missing build input: $required"
    }
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
        --add-data "$appIconPng;qml\assets" `
        --add-data "$plugin;assets" `
        --add-data "$bepinexPayload;assets\bepinex_v113" `
        --add-data "$guideAssets;assets\dglab_guide" `
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
    Copy-Item -LiteralPath (Join-Path $root 'THIRD_PARTY_NOTICES.md') -Destination (Join-Path $portable 'THIRD_PARTY_NOTICES.md') -Force
    Copy-Item -LiteralPath (Join-Path $root 'USER_AGREEMENT_CN.md') -Destination (Join-Path $portable 'USER_AGREEMENT_CN.md') -Force
    Copy-Item -LiteralPath (Join-Path $root 'MOD_CONTENT_NOTICE_CN.md') -Destination (Join-Path $portable 'MOD_CONTENT_NOTICE_CN.md') -Force

    # Ship the three repository worktrees beside the EXE, without local Git
    # history. Keeping them visible makes ownership and later replacement clear.
    $portableModHub = Join-Path $portable 'mod_repositories'
    New-Item -ItemType Directory -Force -Path $portableModHub | Out-Null
    Copy-Item -LiteralPath (Join-Path $modRepositories 'README.md') -Destination $portableModHub -Force
    Copy-Item -LiteralPath (Join-Path $modRepositories '原始整合包说明.txt') -Destination $portableModHub -Force
    foreach ($repoName in @('custommissions1', 'custommissions2', 'plugins')) {
        $sourceRepo = Join-Path $modRepositories $repoName
        $targetRepo = Join-Path $portableModHub $repoName
        New-Item -ItemType Directory -Force -Path $targetRepo | Out-Null
        Get-ChildItem -LiteralPath $sourceRepo -Force |
            Where-Object { $_.Name -ne '.git' } |
            Copy-Item -Destination $targetRepo -Recurse -Force
    }
    Copy-Item -LiteralPath $dropInTemplate -Destination $portable -Recurse -Force

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
