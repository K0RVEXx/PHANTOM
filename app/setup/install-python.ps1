# First-time setup: installs Python for the current user if it is missing.
# Started by the .bat launcher only when no working Python is found.
# Downloads the official installer from python.org, checks its digital signature,
# and installs it for this user only (no administrator rights needed).
param(
    [string]$App = "PHANTOM",
    [ValidateSet("green", "cyan")][string]$Accent = "green",
    [switch]$Preview,           # show the screens without downloading or installing
    [switch]$PreviewDecline,    # show the "not installed" screen without waiting for input
    [int]$PreviewStopAt = 0,    # preview only: freeze the download bar at this percent (for screenshots)
    [switch]$Fast               # preview only: no animation delays
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

# ---------------------------------------------------------------- progress
$BarWidth = 30
function DrawBar([double]$done, [double]$total, [double]$secs) {
    $pct = if ($total -gt 0) { [Math]::Min([double]1.0, [double]($done / $total)) } else { 0.0 }   # keep it a fraction
    $fill = [int][Math]::Floor($pct * $BarWidth)
    $bar = $A + ("█" * $fill) + $GR + ("░" * ($BarWidth - $fill)) + $X
    $secs = [Math]::Max(0.001, $secs)
    $nums = "{0,3}%   {1,4:N1} / {2:N1} MB   {3,4:N1} MB/s" -f [int]($pct * 100), ($done / 1MB), ($total / 1MB), ($done / $secs / 1MB)
    Write-Host ("`r" + (Pad "        $bar $W$nums$X  ")) -NoNewline
}

function Download([string]$url, [string]$out) {
    # Streams the file in chunks so a live progress bar can be shown.
    $watch = [Diagnostics.Stopwatch]::StartNew()
    if ($Preview) {
        $total = 29991280.0; $done = 0.0
        while ($done -lt $total) {
            $done = [Math]::Min($total, $done + 786432)
            DrawBar $done $total ($done / 4.3MB)          # preview: show a realistic speed
            if ($PreviewStopAt -gt 0 -and $done -ge $total * $PreviewStopAt / 100) { Write-Host ""; return $done }
            if (-not $Fast) { Start-Sleep -Milliseconds 45 }
        }
        Write-Host ""; return $done
    }
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    $req = [Net.HttpWebRequest]::Create($url)
    $req.UserAgent = "KORVEX-setup"
    $resp = $req.GetResponse()
    $total = [double]$resp.ContentLength
    $in = $resp.GetResponseStream()
    $fs = [IO.File]::Create($out)
    try {
        $buf = New-Object byte[] 131072
        $done = 0.0; $last = -1000
        while (($n = $in.Read($buf, 0, $buf.Length)) -gt 0) {
            $fs.Write($buf, 0, $n)
            $done += $n
            if ($watch.ElapsedMilliseconds - $last -ge 100) { DrawBar $done $total $watch.Elapsed.TotalSeconds; $last = $watch.ElapsedMilliseconds }
        }
        DrawBar $done $total $watch.Elapsed.TotalSeconds
        Write-Host ""
    } finally { $fs.Close(); $in.Close(); $resp.Close() }
    return $done
}

function Spin($proc, [string]$label) {
    # Animated indicator while a process runs (the Python installer gives no percentage).
    $frames = @("▖", "▘", "▝", "▗")
    $watch = [Diagnostics.Stopwatch]::StartNew(); $i = 0
    while (-not $proc.HasExited) {
        Write-Host ("`r" + (Pad "        $A$($frames[$i % 4])$X $W$label$X $GR$([int]$watch.Elapsed.TotalSeconds)s$X   ")) -NoNewline
        Start-Sleep -Milliseconds 120; $i++
    }
    Write-Host ("`r" + (Pad (" " * 50)) + "`r") -NoNewline
}

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
    try { $got = Download $Url $tmp } catch { Write-Host ""; Fail "Download failed: $($_.Exception.Message)"; return $false }
    if ($PreviewStopAt -gt 0) { return $true }
    Ok ("{0:N1} MB downloaded" -f ($got / 1MB))

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
    if ($Preview) {
        if (-not $Fast) { $fake = Start-Process -FilePath "powershell" -ArgumentList "-NoProfile -Command Start-Sleep 3" -WindowStyle Hidden -PassThru; Spin $fake "Installing Python $PyVersion…" }
        Ok "Python $PyVersion installed"
    }
    else {
        $installArgs = "/quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_launcher=1 InstallLauncherAllUsers=0"
        $p = Start-Process -FilePath $tmp -ArgumentList $installArgs -PassThru
        Spin $p "Installing Python $PyVersion…"
        $p.WaitForExit()
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
