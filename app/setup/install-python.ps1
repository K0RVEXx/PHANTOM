# First-time setup: installs Python for the current user if it is missing.
# Started by the .bat launcher only when no working Python is found.
# Downloads the official installer from python.org, checks its digital signature,
# and installs it for this user only (no administrator rights needed).
param(
    [string]$App = "PHANTOM",
    [ValidateSet("green", "cyan")][string]$Accent = "green",
    [switch]$Preview,           # show the screens without downloading or installing
    [switch]$PreviewDecline     # show the "not installed" screen without waiting for input
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
[Console]::OutputEncoding = [Text.Encoding]::UTF8

$PyVersion = "3.13.17"
$Arch = if ($env:PROCESSOR_ARCHITECTURE -eq "ARM64") { "arm64" } else { "amd64" }
$Url = "https://www.python.org/ftp/python/$PyVersion/python-$PyVersion-$Arch.exe"
$Target = Join-Path $env:LOCALAPPDATA "Programs\Python\Python313\python.exe"

# ---------------------------------------------------------------- look
$E = [char]27
$G = "$E[92m"; $C = "$E[96m"; $GR = "$E[90m"; $R = "$E[91m"; $Y = "$E[93m"; $W = "$E[97m"; $B = "$E[1m"; $X = "$E[0m"
$A = if ($Accent -eq "cyan") { $C } else { $G }
$Width = 58

function Pad([string]$text) {
    try { $cols = [Console]::WindowWidth } catch { $cols = 100 }   # no console window (e.g. redirected)
    $margin = [Math]::Max(0, [int](($cols - $Width - 4) / 2))
    return (" " * $margin) + $text
}
function Line([string]$text = "") { Write-Host (Pad $text) }
function BoxTop { Line "$GR╔$("═" * $Width)╗$X" }
function BoxMid { Line "$GR╠$("═" * $Width)╣$X" }
function BoxBot { Line "$GR╚$("═" * $Width)╝$X" }
function BoxRow([string]$text = "", [switch]$Center) {
    $plain = $text -replace "$E\[[0-9;]*m", ""
    $space = [Math]::Max(0, $Width - $plain.Length)
    $left = if ($Center) { [int]($space / 2) } else { 0 }
    Line "$GR║$X$(" " * $left)$text$(" " * ($space - $left))$GR║$X"
}
function Header {
    Clear-Host
    Write-Host ""
    BoxTop
    BoxRow "$A$B$App$X" -Center
    BoxRow "${GR}First-time setup$X" -Center
    BoxMid
}
function Step([int]$n, [string]$text) { Line "  $GR[$n/3]$X $W$text$X" }
function Ok([string]$text) { Line "        $G[OK]$X $text" }
function Fail([string]$text) { Line "        $R[ERROR]$X $text" }

# ---------------------------------------------------------------- screens
function Ask {
    Header
    BoxRow ""
    BoxRow "  ${W}Python was not found on this computer.$X"
    BoxRow "  $App needs Python to run."
    BoxRow ""
    BoxRow "  ${A}$App can install it for you:$X"
    BoxRow "    $GR-$X Python $PyVersion from ${W}python.org$X (official)"
    BoxRow "    $GR-$X the download's signature is checked first"
    BoxRow "    $GR-$X installed only for you, no administrator needed"
    BoxRow "    $GR-$X about 30 MB"
    BoxRow ""
    BoxBot
    Write-Host ""
    if ($Preview) { Line "  $C›$X Install Python now? (Y/N): ${G}Y$X"; return "y" }
    if ($PreviewDecline) { Line "  $C›$X Install Python now? (Y/N): ${G}N$X"; return "n" }
    Write-Host (Pad "  $C›$X Install Python now? (Y/N): ") -NoNewline
    $answer = Read-Host
    return $answer.Trim().ToLower()
}

function Declined {
    Header
    BoxRow ""
    BoxRow "  ${Y}Python was not installed.$X"
    BoxRow ""
    BoxRow "  To install it yourself:"
    BoxRow "    1. Open ${W}python.org/downloads$X"
    BoxRow "    2. Download Python 3 for Windows and run it"
    BoxRow "    3. Tick ${W}Add python.exe to PATH$X, then Install"
    BoxRow "    4. Start $App again"
    BoxRow ""
    BoxBot
    Write-Host ""
    if ($PreviewDecline) { Line "  $C›$X Press O to open the download page, or Enter to exit:"; return }
    Write-Host (Pad "  $C›$X Press O to open the download page, or Enter to exit: ") -NoNewline
    $k = Read-Host
    if ($k.Trim().ToLower() -eq "o") { Start-Process "https://www.python.org/downloads/windows/" }
}

function Install {
    Header
    BoxRow ""
    BoxRow "  ${W}Installing Python $PyVersion$X"
    BoxRow ""
    BoxBot
    Write-Host ""
    $tmp = Join-Path $env:TEMP "python-$PyVersion-$Arch.exe"

    Step 1 "Downloading from python.org…"
    if ($Preview) { Ok "28.6 MB downloaded" }
    else {
        try { Invoke-WebRequest -Uri $Url -OutFile $tmp -UseBasicParsing; Ok ("{0:N1} MB downloaded" -f ((Get-Item $tmp).Length / 1MB)) }
        catch { Fail "Download failed: $($_.Exception.Message)"; return $false }
    }

    Step 2 "Checking the digital signature…"
    if ($Preview) { Ok "Signed by Python Software Foundation" }
    else {
        $sig = Get-AuthenticodeSignature -FilePath $tmp
        $signer = if ($sig.SignerCertificate) { $sig.SignerCertificate.Subject } else { "" }
        if ($sig.Status -ne "Valid" -or $signer -notmatch "Python Software Foundation") {
            Fail "The file is not signed by the Python Software Foundation. Not installing."
            Remove-Item $tmp -ErrorAction SilentlyContinue
            return $false
        }
        Ok "Signed by Python Software Foundation"
    }

    Step 3 "Installing for this user (this can take a minute)…"
    if ($Preview) { Ok "Python $PyVersion installed" }
    else {
        $installArgs = "/quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_launcher=1 InstallLauncherAllUsers=0"
        $p = Start-Process -FilePath $tmp -ArgumentList $installArgs -Wait -PassThru
        Remove-Item $tmp -ErrorAction SilentlyContinue
        if ($p.ExitCode -ne 0 -or -not (Test-Path $Target)) {
            Fail "The installer stopped with code $($p.ExitCode)."
            return $false
        }
        Ok "Python $PyVersion installed"
    }
    Write-Host ""
    Line "  ${G}Python is ready. Starting $App…$X"
    Start-Sleep -Seconds 2
    return $true
}

# ---------------------------------------------------------------- main
$answer = Ask
if ($answer -in @("y", "yes", "i", "igen")) {
    if (Install) { exit 0 } else {
        Write-Host ""
        Line "  ${GR}Install Python yourself from python.org/downloads, then start $App again.$X"
        Write-Host ""
        if (-not $Preview) { Write-Host (Pad "  Press Enter to exit…") -NoNewline; [void](Read-Host) }
        exit 2
    }
}
if (-not $Preview) { Declined }
exit 1
