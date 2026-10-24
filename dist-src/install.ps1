<#
    FamSwap installer for PUKEY GODDESS SHOT TRICK Demo
    - finds the game through Steam
    - checks for UE4SS (the mod loader) and offers to download it from its official GitHub release
    - copies the mods from the "Mods" folder next to this script (never overwrites your own images)
    - disables UE4SS example mods that crash this game

    Run via Install.bat, or:  powershell -ExecutionPolicy Bypass -File install.ps1 [-GameDir "<path>"]
#>
param(
    [string]$GameDir = "",
    [switch]$NoDownload,
    [switch]$SkipRunningCheck   # for testing against a copy of the game folder
)

$ErrorActionPreference = "Stop"
$AppId = "5253020"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$UE4SSRelease = "https://api.github.com/repos/UE4SS-RE/RE-UE4SS/releases/tags/experimental-latest"
$UE4SSPage = "https://github.com/UE4SS-RE/RE-UE4SS/releases/tag/experimental-latest"
$CrashProneMods = @("CheatManagerEnablerMod", "ConsoleEnablerMod", "ConsoleCommandsMod")
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Say($text, $color = "Gray") { Write-Host $text -ForegroundColor $color }

function Find-GameDir {
    $roots = @()
    foreach ($key in @("HKCU:\Software\Valve\Steam", "HKLM:\SOFTWARE\WOW6432Node\Valve\Steam")) {
        try {
            $p = Get-ItemProperty -Path $key -ErrorAction Stop
            if ($p.SteamPath) { $roots += $p.SteamPath }
            if ($p.InstallPath) { $roots += $p.InstallPath }
        } catch { }
    }
    $roots += "C:\Program Files (x86)\Steam"
    $libs = New-Object System.Collections.Generic.List[string]
    foreach ($r in $roots) {
        $r = [IO.Path]::GetFullPath($r)
        if ((Test-Path $r) -and -not $libs.Contains($r)) { $libs.Add($r) }
        $vdf = Join-Path $r "steamapps\libraryfolders.vdf"
        if (Test-Path $vdf) {
            foreach ($m in [regex]::Matches((Get-Content $vdf -Raw), '"path"\s+"([^"]+)"')) {
                $lib = [IO.Path]::GetFullPath(($m.Groups[1].Value -replace '\\\\', '\'))
                if (-not $libs.Contains($lib)) { $libs.Add($lib) }
            }
        }
    }
    foreach ($lib in $libs) {
        $acf = Join-Path $lib "steamapps\appmanifest_$AppId.acf"
        if (Test-Path $acf) {
            $m = [regex]::Match((Get-Content $acf -Raw), '"installdir"\s+"([^"]+)"')
            if ($m.Success) {
                $dir = Join-Path $lib ("steamapps\common\" + $m.Groups[1].Value)
                if (Test-Path $dir) { return $dir }
            }
        }
    }
    return $null
}

Say "======================================================================" Cyan
Say " FamSwap installer - PUKEY GODDESS SHOT TRICK Demo" Cyan
Say "======================================================================" Cyan

# 1. Game folder
if (-not $GameDir) { $GameDir = Find-GameDir }
while (-not $GameDir -or -not (Test-Path (Join-Path $GameDir "PUKEY_GODDESS_SHOT_TRICK\Binaries\Win64"))) {
    if ($GameDir) { Say "Not the game folder: $GameDir" Yellow } else { Say "Could not find the game automatically." Yellow }
    $GameDir = (Read-Host "Path to the game folder (the one containing PUKEY_GODDESS_SHOT_TRICK), or q to quit").Trim('"', ' ')
    if ($GameDir -eq "q") { exit 1 }
}
$Win64 = Join-Path $GameDir "PUKEY_GODDESS_SHOT_TRICK\Binaries\Win64"
Say "Game: $GameDir" Green

# 2. Game must not be running (files are in use otherwise)
while (-not $SkipRunningCheck -and (Get-Process -Name "PUKEY_GODDESS_SHOT_TRICK*" -ErrorAction SilentlyContinue)) {
    Read-Host "Please close the game first, then press Enter" | Out-Null
}

# 3. UE4SS
$ue4ssDir = Join-Path $Win64 "ue4ss"
$hasUE4SS = (Test-Path (Join-Path $Win64 "dwmapi.dll")) -and (Test-Path (Join-Path $ue4ssDir "UE4SS.dll"))
if ($hasUE4SS) {
    Say "UE4SS is already installed." Green
} else {
    Say "UE4SS (the mod loader) is not installed yet." Yellow
    $download = $false
    if (-not $NoDownload) {
        $a = Read-Host "Download it now from the official GitHub release ($UE4SSPage)? (Y/n)"
        $download = ($a -eq "" -or $a -match '^(y|yes|j|ja)$')
    }
    if (-not $download) {
        Say ""
        Say "Install UE4SS manually:" Yellow
        Say "  1. Open $UE4SSPage"
        Say "  2. Download UE4SS_v....zip (NOT the zDEV/zCustom files)"
        Say "  3. Extract it into: $Win64"
        Say "     (dwmapi.dll and the ue4ss folder must end up next to the game's .exe)"
        Say "  4. Run Install.bat again."
        exit 1
    }
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Say "Looking up the latest UE4SS build ..."
    $rel = Invoke-RestMethod -Uri $UE4SSRelease -Headers @{ "User-Agent" = "FamSwap-Installer" }
    $asset = $rel.assets | Where-Object { $_.name -match '^UE4SS_v.*\.zip$' } | Select-Object -First 1
    if (-not $asset) { throw "No UE4SS zip found in the release. Please install it manually ($UE4SSPage)." }
    $zip = Join-Path $env:TEMP $asset.name
    Say ("Downloading {0} ({1:N1} MB) ..." -f $asset.name, ($asset.size / 1MB))
    Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zip -UseBasicParsing
    Expand-Archive -Path $zip -DestinationPath $Win64 -Force
    Remove-Item $zip -Force
    if (-not (Test-Path (Join-Path $ue4ssDir "UE4SS.dll"))) { throw "UE4SS extraction failed." }
    Say "UE4SS installed." Green
}

# 4. Copy mods (keeps your own images in the mod folders)
$modsDst = Join-Path $ue4ssDir "Mods"
New-Item -ItemType Directory -Force -Path $modsDst | Out-Null
foreach ($mod in Get-ChildItem -Directory (Join-Path $Here "Mods")) {
    $dst = Join-Path $modsDst $mod.Name
    foreach ($f in Get-ChildItem -Recurse -File $mod.FullName) {
        $rel = $f.FullName.Substring($mod.FullName.Length + 1)
        $target = Join-Path $dst $rel
        $isUserImage = ($rel -notmatch '\\') -and ($f.Extension -in ".png", ".jpg")
        if ($isUserImage -and (Test-Path $target)) { continue }
        New-Item -ItemType Directory -Force -Path (Split-Path $target) | Out-Null
        Copy-Item -Path $f.FullName -Destination $target -Force
    }
    Say "Installed mod: $($mod.Name)" Green
}

# 5. Disable UE4SS example mods that crash this game (PlayerController:ClientRestart hook)
foreach ($modName in $CrashProneMods) {
    $marker = Join-Path $modsDst "$modName\enabled.txt"
    if (Test-Path -LiteralPath $marker) { Remove-Item -LiteralPath $marker -Force }
}
$modsTxt = Join-Path $modsDst "mods.txt"
if (Test-Path $modsTxt) {
    $lines = Get-Content $modsTxt
    $lines = $lines | ForEach-Object {
        $l = $_
        foreach ($m in $CrashProneMods) { if ($l -match "^\s*$m\s*:\s*1") { $l = "$m : 0" } }
        $l
    }
    [IO.File]::WriteAllText($modsTxt, (($lines -join "`r`n") + "`r`n"), $Utf8NoBom)
}
$modsJson = Join-Path $modsDst "mods.json"
if (Test-Path $modsJson) {
    $json = Get-Content $modsJson -Raw | ConvertFrom-Json
    foreach ($e in $json) { if ($CrashProneMods -contains $e.mod_name) { $e.mod_enabled = $false } }
    [IO.File]::WriteAllText($modsJson, (ConvertTo-Json -InputObject @($json) -Depth 5), $Utf8NoBom)
}
Say "Disabled crash-prone UE4SS example mods: $($CrashProneMods -join ', ')" Green

Say ""
Say "Done! Next step: run FamSwap-Wizard.bat to pick your image." Cyan
Say "In-game: F8 = toggle replacement, F9 = reload images." Cyan
