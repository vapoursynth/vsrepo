import sys
from glob import glob
from importlib.util import find_spec
from pathlib import Path


def get_vapoursynth_version() -> int:
    try:
        import vapoursynth
    except ImportError:
        return 1

    if hasattr(vapoursynth, '__version__'):
        return vapoursynth.__version__[0]
    return vapoursynth.core.version_number()


def get_vapoursynth_api_version() -> int:
    try:
        import vapoursynth
    except ImportError:
        return 1

    if hasattr(vapoursynth, '__api_version__'):
        return vapoursynth.__api_version__[0]
    # assume lowest widespread api version, will probably error out somewhere else
    return 3


def detect_vapoursynth_installation() -> Path:
    try:
        spec = find_spec('vapoursynth')

        if spec is None:
            raise ModuleNotFoundError
    except (ValueError, ModuleNotFoundError):
        print('Could not detect vapoursynth.')
        sys.exit(1)

    if not spec.has_location:
        try:
            import vapoursynth
        except ImportError:
            print('The vapoursynth-module could not be found or imported.')
        else:
            return Path(vapoursynth.__file__)

    if spec.origin is None:
        print('VapourSynth\'s origin could not be determined.')
        sys.exit(1)

    return Path(spec.origin)


def is_sitepackage_install_portable(portable: bool) -> bool:
    if portable:
        return False

    vapoursynth_path = detect_vapoursynth_installation()
    return vapoursynth_path.with_name('portable.vs').exists()


def is_sitepackage_install(portable: bool) -> bool:
    from .site import is_venv

    if portable:
        return False

    base_path = detect_vapoursynth_installation().parent

    vs_path = 'VapourSynth' if is_venv() else 'VapourSynth_portable'

    if not glob(str(base_path / f'{vs_path}-*.dist-info')):
        return False

    return (base_path / 'portable.vs').exists()
