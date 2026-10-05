# =========================================================================
# Copyright (C) 2026 Ezequiel M Rezende
# License: GPL-3.0-or-later (same as IngeTrazo)
# =========================================================================
# Build the distributable igz_modify3d.zip for the IngeTrazo extension
# catalog (https://github.com/ingelibre/ingetrazo-extensions).
#
# Windows / PowerShell builder — no Python needed. It produces the SAME
# archive layout as packaging/build_extension.py: one top-level folder,
# igz_modify3d/, holding __init__.py + igz_tb_modify3d.py + modify3d/
# (tools and icons) + docs.
#
# The catalog installs ONE file per entry: a .py file, or a .zip holding a
# single folder with an __init__.py (see TEMPLATE.toml in that repository).
#
# Fixed entry timestamps keep the archive stable: rebuilding it prints the
# same SHA-256 as long as the content is unchanged. That SHA-256 is the value
# pasted into extensions/igz_modify3d.toml, and must match the file uploaded
# as the GitHub Release asset of the tag named in `download`.
#
# Usage:
#     powershell -ExecutionPolicy Bypass -File packaging\build_extension.ps1
#
# Output:
#     dist/igz_modify3d.zip
#     dist/igz_modify3d.zip.sha256
# =========================================================================
[CmdletBinding()]
param(
    [string]$Output
)

$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$scriptDir = $PSScriptRoot
if (-not $scriptDir) { $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path }
if (-not $Output) { $Output = Join-Path $scriptDir '..\dist' }

$root = (Resolve-Path (Join-Path $scriptDir '..')).Path
$package = 'igz_modify3d'
$zipName = "$package.zip"

# Fixed timestamp -> reproducible archive.
$fixed = [System.DateTimeOffset]::new(2026, 1, 1, 0, 0, 0, [System.TimeSpan]::Zero)

$outDir = [System.IO.Path]::GetFullPath($Output)
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$zipPath = Join-Path $outDir $zipName
if (Test-Path -LiteralPath $zipPath) { Remove-Item -LiteralPath $zipPath -Force }

# --- Collect the files, then sort by archive path --------------------------
$entries = New-Object System.Collections.Generic.List[object]

function Add-Entry([string]$arc, [string]$src) {
    if (-not (Test-Path -LiteralPath $src -PathType Leaf)) { return }
    $entries.Add([pscustomobject]@{ Arc = $arc; Src = $src })
}

# Package root files.
Add-Entry "$package/__init__.py" (Join-Path $root '__init__.py')
Add-Entry "$package/igz_tb_modify3d.py" (Join-Path $root 'igz_tb_modify3d.py')
foreach ($f in @('LICENSE', 'README.md')) {
    Add-Entry "$package/$f" (Join-Path $root $f)
}

# The modify3d/ tools subpackage (modules + icons), recursively.
$sub = Join-Path $root 'modify3d'
if (Test-Path -LiteralPath $sub) {
    Get-ChildItem -LiteralPath $sub -Recurse -File | ForEach-Object {
        $rel = $_.FullName.Substring($sub.Length + 1) -replace '\\', '/'
        Add-Entry "$package/modify3d/$rel" $_.FullName
    }
}

$sorted = $entries | Sort-Object Arc

# --- Write the zip ---------------------------------------------------------
$stream = [System.IO.File]::Open($zipPath, [System.IO.FileMode]::CreateNew)
try {
    $archive = New-Object System.IO.Compression.ZipArchive(
        $stream, [System.IO.Compression.ZipArchiveMode]::Create)
    try {
        foreach ($e in $sorted) {
            $entry = $archive.CreateEntry(
                $e.Arc, [System.IO.Compression.CompressionLevel]::Optimal)
            $entry.LastWriteTime = $fixed
            $dest = $entry.Open()
            try {
                $bytes = [System.IO.File]::ReadAllBytes($e.Src)
                $dest.Write($bytes, 0, $bytes.Length)
            } finally {
                $dest.Dispose()
            }
        }
    } finally {
        $archive.Dispose()
    }
} finally {
    $stream.Dispose()
}

# --- SHA-256 ---------------------------------------------------------------
$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $zipPath).Hash.ToLower()
Set-Content -LiteralPath "$zipPath.sha256" -Value "$hash  $zipName" -Encoding ascii

$version = '0.0.0'
foreach ($line in Get-Content -LiteralPath (Join-Path $root 'igz_tb_modify3d.py')) {
    if ($line -match '^#\s*Version:\s*(\S+)') { $version = $Matches[1]; break }
}

Write-Host "igz_modify3d $version"
Write-Host "  $zipPath"
Write-Host ("  sha256 = ""{0}""" -f $hash)
Write-Host ''
Write-Host '  Paste that sha256 into extensions/igz_modify3d.toml and upload'
Write-Host "  $zipName to the GitHub Release of the tag in ``download``."
