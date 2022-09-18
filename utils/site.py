import sys
from os.path import dirname


def is_venv() -> bool:
    return hasattr(sys, "real_prefix") or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)


def get_vs_installation_site() -> str:
    if is_venv():
        try:
            from .installations import detect_vapoursynth_installation
            return dirname(detect_vapoursynth_installation())
        except ImportError:
            import setuptools
            return dirname(dirname(setuptools.__file__))

    import site
    return site.getusersitepackages()
