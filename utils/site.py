from pathlib import Path
import sys
from argparse import Namespace
from os import getcwd, getenv, makedirs
from os.path import abspath, dirname, isfile
from os.path import join as join_path
from os.path import pardir
from typing import NamedTuple, Optional, Union

from .installations import detect_vapoursynth_installation, is_sitepackage_install, is_sitepackage_install_portable

try:
    import winreg
except ImportError:
    print('{} is only supported on Windows.'.format(__file__))
    sys.exit(1)


def is_venv() -> bool:
    return hasattr(sys, "real_prefix") or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)


def get_vs_installation_site() -> str:
    if is_venv():
        try:
            return dirname(detect_vapoursynth_installation())
        except ImportError:
            import setuptools
            return dirname(dirname(setuptools.__file__))

    import site
    return site.getusersitepackages()


class InstallationInfo(NamedTuple):
    is_64bits: bool
    file_dirname: Path
    package_json_path: Path
    plugin_path: Path
    site_package_dir: Union[Path, None]
    py_script_path: Path
    cmd7zip_path: Path

    def print_info(self) -> None:
        print('Paths:')
        print(f'Definitions: {self.package_json_path}')
        print(f'Binaries: {self.plugin_path}')
        print(f'Scripts: {self.py_script_path}')

        if self.site_package_dir is not None:
            print(f'Dist-Infos: {self.site_package_dir}')
        else:
            print('Dist-Infos: <Will not be installed>')


def get_installation_info(args: Namespace) -> InstallationInfo:
    is_64bits = args.target == 'win64'

    file_dirname = dirname(join_path(pardir, pardir, abspath(__file__)))

    # VSRepo is installed to the site-packages.
    if abspath(file_dirname).startswith(abspath(sys.prefix)):
        file_dirname = getcwd()

    if args.portable:
        plugin32_path = join_path(file_dirname, 'vapoursynth32', 'plugins')
        plugin64_path = join_path(file_dirname, 'vapoursynth64', 'plugins')
        package_json_path = join_path(file_dirname, 'vspackages3.json')
    elif is_sitepackage_install_portable(args.portable):
        vapoursynth_path = detect_vapoursynth_installation()
        base_path = dirname(vapoursynth_path)
        plugin32_path = join_path(base_path, 'vapoursynth32', 'plugins')
        plugin64_path = join_path(base_path, 'vapoursynth64', 'plugins')
        package_json_path = join_path(base_path, 'vspackages3.json')
        del vapoursynth_path
    else:
        pluginparent = [str(getenv('APPDATA')), 'VapourSynth']
        plugin32_path = join_path(*pluginparent, 'plugins32')
        plugin64_path = join_path(*pluginparent, 'plugins64')
        package_json_path = join_path(*pluginparent, 'vsrepo', 'vspackages3.json')

    plugin_path: str = plugin64_path if is_64bits else plugin32_path

    if args.force_dist_info or is_sitepackage_install(args.portable):
        if is_venv():
            try:
                import setuptools
                site_package_dir: Optional[str] = dirname(dirname(setuptools.__file__))
                del setuptools
            except ImportError:
                site_package_dir = None
        else:
            import site
            site_package_dir = site.getusersitepackages()
    else:
        site_package_dir = None

    py_script_path: str = file_dirname if args.portable else (
        site_package_dir if site_package_dir is not None else get_vs_installation_site()
    )
    if args.script_path is not None:
        py_script_path = args.script_path

    if args.binary_path is not None:
        plugin_path = args.binary_path

    makedirs(py_script_path, exist_ok=True)
    makedirs(plugin_path, exist_ok=True)
    makedirs(dirname(package_json_path), exist_ok=True)

    cmd7zip_path: str = join_path(file_dirname, '7z.exe')
    if not isfile(cmd7zip_path):
        try:
            with winreg.OpenKeyEx(
                winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\7-Zip', reserved=0, access=winreg.KEY_READ
            ) as regkey:
                cmd7zip_path = join_path(winreg.QueryValueEx(regkey, 'Path')[0], '7z.exe')
        except BaseException:
            cmd7zip_path = '7z.exe'

    return InstallationInfo(
        is_64bits, Path(file_dirname), Path(package_json_path), Path(plugin_path),
        site_package_dir and Path(site_package_dir) or None,
        Path(py_script_path), Path(cmd7zip_path)
    )
