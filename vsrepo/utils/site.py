import sys
from os import getenv
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple, Optional, Union

from .installations import detect_vapoursynth_installation, is_sitepackage_install, is_sitepackage_install_portable

if TYPE_CHECKING:
    from .types import VSRepoNamespace
else:
    from argparse import Namespace as VSRepoNamespace

try:
    import winreg
except ImportError:
    print('{} is only supported on Windows.'.format(__file__))
    sys.exit(1)


def is_venv() -> bool:
    return hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)


def get_vs_installation_site() -> Path:
    if is_venv():
        try:
            return detect_vapoursynth_installation().parent
        except ImportError:
            import setuptools
            return Path(setuptools.__file__).parent.parent

    import site
    return Path(site.getusersitepackages())


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


def get_installation_info(args: VSRepoNamespace) -> InstallationInfo:
    is_64bits = str(args.target) == 'win64'

    file_dirname = Path(__file__).parent.parent.absolute()

    # VSRepo is installed to the site-packages.
    if Path(sys.prefix) in file_dirname.parents:
        file_dirname = Path.cwd()

    if args.portable:
        plugin32_path = file_dirname / 'vapoursynth32' / 'plugins'
        plugin64_path = file_dirname / 'vapoursynth64' / 'plugins'
        package_json_path = file_dirname / 'vspackages3.json'
    elif is_sitepackage_install_portable(args.portable):
        base_path = detect_vapoursynth_installation().parent

        plugin32_path = base_path / 'vapoursynth32' / 'plugins'
        plugin64_path = base_path / 'vapoursynth64' / 'plugins'
        package_json_path = base_path / 'vspackages3.json'
    else:
        pluginparent = Path(str(getenv('APPDATA'))) / 'VapourSynth'

        plugin32_path = pluginparent / 'plugins32'
        plugin64_path = pluginparent / 'plugins64'
        package_json_path = pluginparent / 'vsrepo' / 'vspackages3.json'

    plugin_path = plugin64_path if is_64bits else plugin32_path

    if args.force_dist_info or is_sitepackage_install(args.portable):
        if is_venv():
            try:
                import setuptools
                site_package_dir: Optional[Path] = Path(setuptools.__file__).parent.parent
                del setuptools
            except ImportError:
                site_package_dir = None
        else:
            import site
            site_package_dir = Path(site.getusersitepackages())
    else:
        site_package_dir = None

    py_script_path = file_dirname if args.portable else (site_package_dir or get_vs_installation_site())

    if args.script_path is not None:
        py_script_path = Path(args.script_path)

    if args.binary_path is not None:
        plugin_path = Path(args.binary_path)

    py_script_path.mkdir(parents=True, exist_ok=True)
    plugin_path.mkdir(parents=True, exist_ok=True)
    package_json_path.parent.mkdir(parents=True, exist_ok=True)

    cmd7zip_path = file_dirname / '7z.exe'
    if not cmd7zip_path.is_file():
        try:
            with winreg.OpenKeyEx(
                winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\7-Zip', reserved=0, access=winreg.KEY_READ
            ) as regkey:
                cmd7zip_path = Path(winreg.QueryValueEx(regkey, 'Path')[0]) / '7z.exe'
        except BaseException:
            cmd7zip_path = Path('7z.exe')

    return InstallationInfo(
        is_64bits, file_dirname, package_json_path, plugin_path, site_package_dir, py_script_path, cmd7zip_path
    )
