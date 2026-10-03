# SAPE f-MCP - build the Linux packages from Windows, inside a Docker container.
#
# Usage (Docker Desktop running, Linux engine):
#
#   powershell -ExecutionPolicy Bypass -File _distro\Linux\build_linux_docker.ps1 [appimage] [deb] [rpm]
#
# Runs build_linux.sh unchanged in a throwaway container, so the Windows machine needs no
# Linux toolchain and no sudo. The image decides which distributions can run the result:
# a PyInstaller bundle needs a glibc at least as new as the build system's. The default
# rockylinux:9 (glibc 2.34) produces packages for RHEL/Rocky/Alma 9+, Ubuntu 22.04+,
# Debian 12+ and Fedora 35+. An older base gains nothing today: the PyQt6 6.11 wheels
# themselves require glibc 2.34. Pass -Image for another base; Debian/Ubuntu (apt) and
# RHEL/Fedora (dnf) images are both supported.
#
# The project folder must be on a drive Docker can mount (a local disk, not a virtual
# cloud-sync drive). Output: _distro\Linux\output\
#
# This file is ASCII-only on purpose: Windows PowerShell 5.1 reads a BOM-less script as ANSI.

# PositionalBinding off: bare words are formats (appimage, deb, rpm), never the -Image value.
[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$Image = "rockylinux:9",
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$Formats = @()
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

$aptPackages = @(
    # libpython3-dev pulls in libpython3.X.so, which PyInstaller bundles; system Python on
    # Debian/Ubuntu does not ship it by default.
    "python3", "python3-venv", "python3-pip", "libpython3-dev", "ca-certificates", "curl", "file",
    "dpkg-dev", "rpm",
    # Imported by PyInstaller's Qt hooks while it analyses PyQt6.
    "libglib2.0-0", "libgl1", "libegl1", "libfontconfig1", "libxkbcommon0", "libdbus-1-3",
    # Needed by Qt's xcb platform plugin; present here so PyInstaller can resolve them.
    "libxcb-cursor0", "libxcb-icccm4", "libxcb-image0", "libxcb-keysyms1", "libxcb-randr0",
    "libxcb-render-util0", "libxcb-shape0", "libxcb-xinerama0", "libxcb-xkb1", "libxkbcommon-x11-0"
) -join " "

$dnfPackages = @(
    # python3.11-devel brings libpython3.11.so, which PyInstaller bundles. dpkg (for the .deb)
    # comes from EPEL, enabled below.
    "python3.11", "python3.11-pip", "python3.11-devel", "ca-certificates", "file", "findutils",
    "dpkg", "rpm-build",
    # Imported by PyInstaller's Qt hooks while it analyses PyQt6.
    "glib2", "mesa-libGL", "mesa-libEGL", "fontconfig", "libxkbcommon", "dbus-libs",
    # Needed by Qt's xcb platform plugin; present here so PyInstaller can resolve them.
    "xcb-util-cursor", "xcb-util-wm", "xcb-util-image", "xcb-util-keysyms", "xcb-util-renderutil",
    "libxkbcommon-x11", "libX11-xcb"
) -join " "

# curl-minimal ships in the RHEL-family images; installing full curl would conflict with it.
$inner = "set -e; " +
         "if command -v apt-get >/dev/null; then " +
         "export DEBIAN_FRONTEND=noninteractive; " +
         "apt-get update -qq && apt-get install -y -qq --no-install-recommends $aptPackages >/dev/null; " +
         "else " +
         "dnf install -y -q epel-release >/dev/null 2>&1 || true; " +
         "dnf install -y -q $dnfPackages >/dev/null; " +
         "export PYTHON=python3.11; " +
         "fi; " +
         "bash /src/_distro/Linux/build_linux.sh $($Formats -join ' ')"

Write-Host "==> Building Linux packages in $Image from $ProjectRoot"
$previous = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try {
    & docker run --rm -v "${ProjectRoot}:/src" -e BUILD_ROOT=/build $Image bash -c $inner
} finally { $ErrorActionPreference = $previous }
if ($LASTEXITCODE -ne 0) { throw "Container build failed with exit code $LASTEXITCODE" }
Write-Host "==> Artifacts in $(Join-Path $ProjectRoot '_distro\Linux\output')"
