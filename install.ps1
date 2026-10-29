# zhanggong skill installer (Windows PowerShell 5.1 / 7+ compatible)
#
# Usage:
#   irm https://raw.githubusercontent.com/Yym11345/zhanggong-yanyu-skill/main/install.ps1 | iex
#   powershell -ExecutionPolicy Bypass -File install.ps1
#   Options: -Project  -> install into ./.workbuddy/skills/zhanggong
#             -Target D -> custom destination directory
#
# NOTE: This file is deliberately ASCII-only (no Chinese / no non-ASCII arrows).
# PowerShell 5.1 reads .ps1 files as ANSI unless a UTF-8 BOM is present, so
# non-ASCII characters can be mangled and break parsing on older systems.
# All user-facing text is emitted in English to stay encoding-safe.
#
# Works in two modes:
#   1) Piped execution (irm | iex): script comes from stdin, $PSScriptRoot is
#      empty -> auto-download the repo tarball as the install source.
#   2) Local execution (-File install.ps1): use the script's own directory.

param(
  [switch]$Project,
  [string]$Target = ""
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$SkillName = "zhanggong"
$Repo = "Yym11345/zhanggong-yanyu-skill"
$Tarball = "https://github.com/$Repo/archive/refs/heads/main.tar.gz"

function Write-Step($msg) { Write-Host "-> $msg" }

# ---------- locate source ----------
$SrcDir = ""
$TmpDir = ""

try {
  if ($PSScriptRoot -and (Test-Path (Join-Path $PSScriptRoot "SKILL.md"))) {
    # Local execution
    $SrcDir = $PSScriptRoot
  }
  else {
    # Piped execution: download the repo tarball
    Write-Step "Piped mode: downloading package from GitHub..."
    $TmpDir = Join-Path ([System.IO.Path]::GetTempPath()) ("zg_install_" + [System.Guid]::NewGuid().ToString("N").Substring(0,8))
    New-Item -ItemType Directory -Path $TmpDir -Force | Out-Null

    $extract = Join-Path $TmpDir "x"
    New-Item -ItemType Directory -Path $extract -Force | Out-Null

    # NOTE: GNU tar on Windows may treat "C:" in an absolute path as a remote host
    # ("Cannot connect to C:"). Download into the extract dir and use a relative
    # name so tar never sees a drive letter.
    $tgz = Join-Path $extract "pkg.tar.gz"
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $Tarball -OutFile $tgz -UseBasicParsing

    Push-Location $extract
    try {
      & tar -xzf "pkg.tar.gz"
      if ($LASTEXITCODE -ne 0) { throw "tar extraction failed" }
    } finally {
      Pop-Location
    }

    $dirs = Get-ChildItem -Path $extract -Directory
    if (-not $dirs) { throw "unexpected archive layout" }
    $SrcDir = $dirs[0].FullName
    if (-not (Test-Path (Join-Path $SrcDir "SKILL.md"))) { throw "SKILL.md not found in archive" }
    Write-Step "Downloaded: $SrcDir"
  }

  # ---------- decide destination ----------
  if ($Target) {
    $Dest = $Target
  } elseif ($Project) {
    $Dest = Join-Path (Get-Location).Path ".workbuddy\skills\$SkillName"
  } else {
    $wb = Join-Path $HOME ".workbuddy\skills"
    $cl = Join-Path $HOME ".claude\skills"
    if (Test-Path $wb) { $Dest = Join-Path $wb $SkillName }
    elseif (Test-Path $cl) { $Dest = Join-Path $cl $SkillName }
    else { $Dest = Join-Path $wb $SkillName }
  }

  Write-Step "Source     : $SrcDir"
  Write-Step "Destination: $Dest"

  # ---------- back up existing install ----------
  if (Test-Path $Dest) {
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backup = "$Dest.bak.$stamp"
    Write-Step "Existing install found, backing up to: $backup"
    Move-Item $Dest $backup
  }

  New-Item -ItemType Directory -Path $Dest -Force | Out-Null

  # ---------- copy core files ----------
  foreach ($f in @("SKILL.md", "README.md", "INSTALL.md", "LICENSE")) {
    $p = Join-Path $SrcDir $f
    if (Test-Path $p) { Copy-Item $p $Dest -Force }
  }

  foreach ($d in @("references", "scripts", "assets")) {
    $p = Join-Path $SrcDir $d
    if (Test-Path $p) {
      $dd = Join-Path $Dest $d
      New-Item -ItemType Directory -Path $dd -Force | Out-Null
      Copy-Item (Join-Path $p "*") $dd -Recurse -Force
      Write-Host "   + $d/"
    }
  }

  # ---------- clean caches ----------
  # NOTE: Get-ChildItem returns $null when nothing matches; piping $null into
  # Remove-Item raises "missing path operand". Guard with an explicit count.
  $pycache = @(Get-ChildItem $Dest -Recurse -Filter "__pycache__" -Directory -ErrorAction SilentlyContinue)
  if ($pycache.Count -gt 0) {
    $pycache | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
  }
  $pyc = @(Get-ChildItem $Dest -Recurse -Filter "*.pyc" -ErrorAction SilentlyContinue)
  if ($pyc.Count -gt 0) {
    $pyc | Remove-Item -Force -ErrorAction SilentlyContinue
  }

  # ---------- verify ----------
  $skillMd = Join-Path $Dest "SKILL.md"
  if (-not (Test-Path $skillMd)) {
    throw "Verification failed: SKILL.md missing"
  }
  $head = (Get-Content $skillMd -TotalCount 6) -join "`n"
  if ($head -notmatch '(?m)^name:\s*(\S+)') {
    throw "Verification failed: SKILL.md frontmatter malformed"
  }
  $name = $Matches[1]
  $refCount = 0
  if (Test-Path (Join-Path $Dest "references")) {
    $refCount = (Get-ChildItem (Join-Path $Dest "references") -File).Count
  }

  Write-Host ""
  Write-Host "Installation complete."
  Write-Host "  skill name : $name"
  Write-Host "  references : $refCount"
  Write-Host "  path       : $Dest"
  Write-Host ""
  Write-Host "Usage: paste a verbal-reasoning question, or say 'analyze this question using the flashcard method'."
}
finally {
  if ($TmpDir -and (Test-Path $TmpDir)) {
    try {
      [System.IO.Directory]::Delete($TmpDir, $true)
    } catch {
      # cleanup failure must not break the install result
    }
  }
}
