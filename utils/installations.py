import sys
from glob import glob
from importlib.util import find_spec
from os.path import dirname
from os.path import exists as path_exists
from os.path import join as join_path

from .site import is_venv


def detect_vapoursynth_installation() -> str:
    try:
        spec = find_spec("vapoursynth")

        if spec is None:
            raise ModuleNotFoundError
    except (ValueError, ModuleNotFoundError):
        print("Could not detect vapoursynth.")
        sys.exit(1)

    if not spec.has_location:
        try:
            import vapoursynth
        except ImportError:
            print("The vapoursynth-module could not be found or imported.")
        else:
            return vapoursynth.__file__

    if spec.origin is None:
        print("VapourSynth's origin could not be determined.")
        sys.exit(1)

    return spec.origin


def is_sitepackage_install_portable(portable: bool) -> bool:
    if portable:
        return False

    vapoursynth_path = detect_vapoursynth_installation()
    return path_exists(join_path(dirname(vapoursynth_path), 'portable.vs'))


def is_sitepackage_install(portable: bool) -> bool:
    if portable:
        return False

    vapoursynth_path = detect_vapoursynth_installation()
    base_path = dirname(vapoursynth_path)

    # We reside in a venv.
    if is_venv():
        # VapourSynth has not been installed as a package.
        # Assume no site-package install
        if len(glob.glob(join_path(base_path, 'VapourSynth-*.dist-info'))) == 0:
            return False

        if path_exists(join_path(base_path, "portable.vs")):
            return True

        # Assume this is not a global install.
        return False

    # We do not reside in a venv.
    else:
        # pip install vapoursynth-portable
        # Install all packages to site-packages and treat them as packages.
        if len(glob.glob(join_path(base_path, 'VapourSynth_portable-*.dist-info'))) > 0:
            return True

        # This is a portable installation, this cannot be a site-package install.
        if path_exists(join_path(base_path, "portable.vs")):
            return False

        # This is a global install. Install dist-info files.
        return True
