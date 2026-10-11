param(
    [Parameter(Mandatory = $true)]
    [string]$GameDir,
    [switch]$Deploy
)

$ErrorActionPreference = "Stop"

$compiler = "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe"
if (-not (Test-Path -LiteralPath $compiler)) {
    throw "C# compiler not found: $compiler"
}

$gameDir = (Resolve-Path -LiteralPath $GameDir).Path
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$outputDir = Join-Path $scriptDir "bin"
$outputDll = Join-Path $outputDir "ManakaDGLabTelemetry.dll"
$responseFile = Join-Path $outputDir "compiler.rsp"

New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

$references = @(
    "dotnet\System.Private.CoreLib.dll",
    "dotnet\mscorlib.dll",
    "dotnet\System.Runtime.dll",
    "dotnet\netstandard.dll",
    "dotnet\System.Console.dll",
    "dotnet\System.Collections.dll",
    "dotnet\System.Net.Primitives.dll",
    "dotnet\System.Net.Sockets.dll",
    "dotnet\System.Text.Encoding.Extensions.dll",
    "dotnet\System.Runtime.InteropServices.dll",
    "dotnet\Microsoft.Win32.Primitives.dll",
    "BepInEx\core\BepInEx.Core.dll",
    "BepInEx\core\BepInEx.Unity.Common.dll",
    "BepInEx\core\BepInEx.Unity.IL2CPP.dll",
    "BepInEx\core\Il2CppInterop.Runtime.dll",
    "BepInEx\core\0Harmony.dll",
    "BepInEx\interop\Assembly-CSharp.dll",
    "BepInEx\interop\Il2Cppmscorlib.dll",
    "BepInEx\interop\UnityEngine.dll",
    "BepInEx\interop\UnityEngine.CoreModule.dll"
) | ForEach-Object { Join-Path $gameDir $_ }

foreach ($reference in $references) {
    if (-not (Test-Path -LiteralPath $reference)) {
        throw "Required reference not found: $reference"
    }
}

$response = @(
    "/nostdlib+",
    "/target:library",
    "/optimize+",
    "/debug:portable",
    "/langversion:latest",
    "/out:`"$outputDll`""
)
$response += $references | ForEach-Object { "/reference:`"$_`"" }
$response += "`"$(Join-Path $scriptDir 'Plugin.cs')`""

Set-Content -LiteralPath $responseFile -Value $response -Encoding UTF8
& $compiler "/noconfig" "@$responseFile"
if ($LASTEXITCODE -ne 0) {
    throw "Plugin compilation failed with exit code $LASTEXITCODE"
}

Write-Host "Built: $outputDll"

if ($Deploy) {
    $pluginDir = Join-Path $gameDir "BepInEx\plugins\ManakaDGLabTelemetry"
    New-Item -ItemType Directory -Force -Path $pluginDir | Out-Null
    Copy-Item -LiteralPath $outputDll -Destination (Join-Path $pluginDir "ManakaDGLabTelemetry.dll") -Force
    Write-Host "Deployed: $pluginDir"
    Write-Host "Restart the game so BepInEx can load the plugin."
}
