#!/usr/bin/env bash
# SAPÉ f-MCP — install-and-run test for one Linux package, meant to run as root inside a
# clean container (see test_linux_docker.ps1). Usage: test_packages_inside.sh deb|rpm|appimage
set -u
KIND="$1"
OUT=/src/_distro/Linux/output
DATA="$HOME/.local/share/sape/f-mcp"
fail=0
check() { if eval "$2"; then echo "PASS  $1"; else echo "FAIL  $1"; fail=1; fi; }

case "$KIND" in
  deb)
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq >/dev/null
    check "apt installs the .deb with its dependencies" "apt-get install -y -qq $OUT/sape-f-mcp_*_amd64.deb >/dev/null 2>&1"
    ;;
  rpm)
    check "dnf installs the .rpm with its dependencies" "dnf install -y -q $OUT/sape-f-mcp-*.x86_64.rpm >/dev/null 2>&1"
    ;;
  appimage)
    cp $OUT/sape-f-mcp-*-x86_64.AppImage /tmp/app.AppImage && chmod +x /tmp/app.AppImage
    check "AppImage --cli --version" "/tmp/app.AppImage --appimage-extract-and-run --cli --version"
    check "AppImage keeps permissions.db in $DATA" \
          "/tmp/app.AppImage --appimage-extract-and-run --cli --show-permissions >/dev/null 2>&1 && [ -f $DATA/permissions.db ]"
    exit $fail
    ;;
esac

check "sape-f-mcp on PATH reports the version" "sape-f-mcp --cli --version"
QXCB=/opt/sape-f-mcp/_internal/PyQt6/Qt6/plugins/platforms/libqxcb.so
check "Qt xcb plugin has no unresolved libraries" "! ldd $QXCB | grep -q 'not found'"
[ -f "$QXCB" ] && ldd $QXCB | grep 'not found' | sed 's/^/      /'

mkdir -p /tmp/work && cd /tmp/work
check "terminal launch keeps permissions.db in $DATA" \
      "sape-f-mcp --cli --show-permissions >/dev/null 2>&1 && [ -f $DATA/permissions.db ]"
check "nothing is written inside /opt/sape-f-mcp" "[ ! -e /opt/sape-f-mcp/_internal/permissions.db ]"
check "FILE_MCP_DB overrides the default" \
      "FILE_MCP_DB=/tmp/work/custom.db sape-f-mcp --cli --show-permissions >/dev/null 2>&1 && [ -f /tmp/work/custom.db ]"

cd /
rm -rf "$DATA"
QT_QPA_PLATFORM=offscreen timeout 20 sape-f-mcp-gui >/tmp/gui.log 2>&1; rc=$?
check "GUI starts via desktop launcher (still running after 20 s)" "[ $rc -eq 124 ]"
[ $rc -ne 124 ] && tail -20 /tmp/gui.log | sed 's/^/      /'
check "desktop launch keeps permissions.db in $DATA" "[ -f $DATA/permissions.db ]"
check ".desktop entry installed" "[ -f /usr/share/applications/sape-f-mcp.desktop ]"
exit $fail
