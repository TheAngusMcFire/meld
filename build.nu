#!/usr/bin/env nu

# build.nu — install everything needed to build a release version of Meld,
# then build it.
#
# Meld uses the Meson build system. This script installs the build and runtime
# dependencies via pacman, configures a non-Devel (release) Meson build, and
# compiles it.
#
# Usage:
#   nu build.nu               # install deps + build release into ./_build
#   nu build.nu --install     # ...and then install system-wide (uses sudo)
#   nu build.nu --builddir b  # use a different Meson build directory

def main [
    --install                       # run `meson install` after building
    --builddir: string = "_build"   # Meson build directory to use
] {
    let repo = $env.FILE_PWD
    cd $repo

    if not ("meld.doap" | path exists) {
        error make {msg: $"($repo) does not look like the Meld source tree"}
    }

    print $"Meld release build — source: ($repo)"

    # 1. Dependencies.
    #    Build tools: meson, ninja, gettext (msgfmt + gnome.yelp), glib2
    #    (glib-compile-schemas/resources), itstool (help), pkgconf.
    #    pkg-config deps: gtk3, gtksourceview4, python-gobject (pygobject-3.0),
    #    python-cairo (py3cairo), gsettings-desktop-schemas.
    #    Optional post-install/validation: desktop-file-utils, appstream,
    #    adwaita-icon-theme.
    let pkgs = [
        base-devel
        pkgconf
        meson
        ninja
        gettext
        glib2
        itstool
        python
        python-gobject
        python-cairo
        gtk3
        gtksourceview4
        gsettings-desktop-schemas
        adwaita-icon-theme
        desktop-file-utils
        appstream
    ]

    print "==> Installing build dependencies (sudo pacman -Syu --needed)..."
    # -Syu refreshes the package DB first, avoiding stale-mirror 404s on a
    # partial install.
    sudo pacman -Syu --needed ...$pkgs

    if (which meson | is-empty) {
        error make {msg: "meson not found after install; aborting"}
    }

    # 2. Configure a release build (default profile == non-Devel release).
    if ($builddir | path exists) {
        print $"==> Reconfiguring existing Meson build dir '($builddir)'..."
        meson setup --reconfigure --buildtype=release $builddir
    } else {
        print $"==> Configuring release build in '($builddir)'..."
        meson setup --buildtype=release $builddir
    }

    # 3. Compile.
    print "==> Building..."
    meson compile -C $builddir

    # 4. Optionally install system-wide.
    if $install {
        print "==> Installing system-wide (sudo meson install)..."
        sudo meson install -C $builddir
        print "Installed. Run it with: meld"
    } else {
        print $"==> Done. Release build produced in '($repo)/($builddir)'."
        print "    Install it with:  nu build.nu --install"
        print "    Or run uninstalled from the source tree:  bin/meld"
    }
}
