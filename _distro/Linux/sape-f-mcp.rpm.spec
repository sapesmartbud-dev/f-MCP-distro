# SAPÉ f-MCP — RPM spec for repackaging the prebuilt PyInstaller bundle.
#
# Not meant to be run by hand: build_linux.sh stages the files and calls rpmbuild with
# --define for app_version and staging_dir.

# The payload is an already-frozen PyInstaller bundle: no compilation, no stripping (it
# would corrupt the bundled archive), no Python byte-compiling, no debuginfo.
%global debug_package %{nil}
%global __strip /bin/true
%global __os_install_post %{nil}
%global _build_id_links none
# Automatic dependency scanning would demand every library bundled inside the package
# (Qt, OpenSSL, ...) from the system. Real system dependencies are listed by hand below.
AutoReqProv: no

Name:           sape-f-mcp
Version:        %{app_version}
Release:        1
Summary:        Controlled file system access with granular permissions for LLMs
License:        GPL-3.0-only
URL:            https://sapebud.com
ExclusiveArch:  x86_64 aarch64

# Qt 6's xcb platform plugin needs these from the system.
Requires:       xcb-util-cursor
Requires:       xcb-util-image
Requires:       xcb-util-keysyms
Requires:       xcb-util-renderutil
Requires:       xcb-util-wm
Requires:       libxkbcommon-x11
Requires:       libX11-xcb
Requires:       mesa-libGL
Requires:       mesa-libEGL
Requires:       glib2
Requires:       fontconfig
Requires:       dbus-libs
Requires:       hicolor-icon-theme

%description
SAPÉ f-MCP is an MCP server with a desktop GUI that gives LLMs controlled access to the
local file system under granular, default-deny, per-folder permissions, with a log of
every tool call.

%install
cp -a %{staging_dir}/. %{buildroot}/

%files
# /opt/sape-f-mcp/LICENSE ships inside the directory below.
/opt/sape-f-mcp
/usr/bin/sape-f-mcp
/usr/bin/sape-f-mcp-gui
/usr/share/applications/sape-f-mcp.desktop
/usr/share/icons/hicolor/*/apps/sape-f-mcp.png
