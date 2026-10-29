# zhanggong skill installer (Windows PowerShell 5.1 / 7+ compatible)
#
# Usage:
#   irm https://raw.githubusercontent.com/<YOUR_GITHUB_USERNAME>/zhanggong-yanyu-skill/main/install.ps1 | iex
#   powershell -ExecutionPolicy Bypass -File install.ps1
#   Options: -Project  -> install into ./.workbuddy/skills/zhanggong
#             -Target D -> custom destination directory
#
# NOTE: This file is deliberately ASCII-only (no Chinese / no non-ASCII arrows).
# PowerShell 5.1 reads .ps1 files as ANSI unless a UTF-8 BOM is present, so
# non-ASCII characters can be mangled and break parsing on older systems.
# All user-facing text is emitted in English to stay encoding-safe.

param(
  [switch]$Project,
  [string]$Target = ""
)

$ErrorActionPreference = "Stop"
$SkillName = "zhanggong"

# ---------- locate source ----------
$SrcDir = $PSScriptRoot
if (-not $SrcDir) { $SrcDir = (Get-Location).Path }
if (-not (Test-Path (Join-Path $SrcDir "SKILL.md"))) {
  Write-Error "SKILL.md not found. Run this script from inside the skill repository."
  exit 1
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

Write-Host "-> Source     : $SrcDir"
Write-Host "-> Destination: $Dest"

# ---------- back up existing install ----------
if (Test-Path $Dest) {
  $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
  $backup = "$Dest.bak.$stamp"
  Write-Host "-> Existing install found, backing up to: $backup"
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
Get-ChildItem $Dest -Recurse -Filter "__pycache__" -Directory -ErrorAction SilentlyContinue |
  Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem $Dest -Recurse -Filter "*.pyc" -ErrorAction SilentlyContinue |
  Remove-Item -Force -ErrorAction SilentlyContinue

# ---------- verify ----------
$skillMd = Join-Path $Dest "SKILL.md"
if (-not (Test-Path $skillMd)) {
  Write-Error "Verification failed: SKILL.md missing"
  exit 1
}
$head = (Get-Content $skillMd -TotalCount 6) -join "`n"
if ($head -notmatch '(?m)^name:\s*(\S+)') {
  Write-Error "Verification failed: SKILL.md frontmatter malformed"
  exit 1
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
