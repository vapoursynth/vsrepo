import base64
import binascii
import csv
import hashlib
import io
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from argparse import Namespace
from email.utils import formatdate, mktime_tz, parsedate_tz
from pathlib import Path
from typing import Iterator, List, Optional, Tuple
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .utils import (
    InstallationInfo, InstalledPackages, InstallFileResult, InstallPackageResult, VSPackage,
    VSPackagePlatformReleaseWheel, VSPackageRel, VSPackages, VSPackageType, fetch_url_cached,
    get_vapoursynth_api_version
)

args: Namespace = None  # type: ignore
info: InstallationInfo = None  # type: ignore
package_list: VSPackages = None  # type: ignore
installed_packages: InstalledPackages = None  # type: ignore


def set_variables(
    _args: Namespace, _info: InstallationInfo, _package_list: VSPackages, _installed_packages: InstalledPackages
) -> None:
    global args, info, package_list, installed_packages
    args = _args
    info = _info
    package_list = _package_list
    installed_packages = _installed_packages


package_print_string = '{:25s} {:15s} {:11s} {:11s} {:s}'

bundled_api3_plugins = {
    'com.vapoursynth.avisource', 'com.vapoursynth.eedi3', 'com.vapoursynth.imwri',
    'com.vapoursynth.misc', 'com.vapoursynth.morpho', 'com.vapoursynth.removegrainvs',
    'com.vapoursynth.subtext', 'com.vapoursynth.vinverse', 'org.ivtc.v', 'com.nodame.histogram'
}

MISSING = object()


def check_hash(data: bytes, ref_hash: str) -> Tuple[bool, str, str]:
    data_hash = hashlib.sha256(data).hexdigest()
    return (data_hash == ref_hash, data_hash, ref_hash)


def find_dist_version(pkg: VSPackage, path: Optional[Path]) -> Optional[str]:
    if path is None:
        return None

    name = pkg.get_python_name()
    versions = [
        targetname.name[len(name) + 1:-10]
        for targetname in path.iterdir() if (
            # only bother with dist-info dirs that actually have a usable
            # record in case a package uninstall failed to delete the dir
            targetname.name.startswith(f'{name}-') and targetname.name.endswith('.dist-info')
            and (targetname / 'RECORD').is_file()
        )
    ]

    return max(versions, default=None)


def detect_installed_packages() -> None:
    for p in package_list:
        dest_path = p.get_install_path(info)

        if p.pkg_type is VSPackageType.WHEEL:
            if (version := find_dist_version(p, dest_path)) is not None:
                installed_packages[p.identifier] = version

            continue

        for v in p.releases:
            matched = True
            exists = True

            if (release := v.get_release(p.pkg_type)) and release.files:
                for f, rel_file in release.files.items():
                    try:
                        if not check_hash((dest_path / f).read_bytes(), rel_file.filename)[0]:
                            matched = False
                    except FileNotFoundError:
                        exists = False
                        matched = False

                if matched:
                    installed_packages[p.identifier] = v.version
                    break

                if exists:
                    installed_packages[p.identifier] = 'Unknown'


def print_package_status(p: VSPackage) -> None:
    lastest_installable = p.get_latest_installable_release()
    name = p.name
    if installed_packages.is_package_upgradable(p.identifier, False):
        name = f'*{name}'
    elif installed_packages.is_package_upgradable(p.identifier, True):
        name = f'+{name}'
    print(
        package_print_string.format(
            name, p.namespace if p.pkg_type is VSPackageType.PLUGIN else p.modulename,
            installed_packages.get(p.identifier, ''),
            lastest_installable.version if lastest_installable is not None else '',
            p.identifier
        )
    )


def list_installed_packages() -> None:
    print(package_print_string.format('Name', 'Namespace', 'Installed', 'Latest', 'Identifier'))
    for id in installed_packages:
        pkg = installed_packages.get_package_from_id(id, True)
        if pkg is not None:
            print_package_status(pkg)


def list_available_packages() -> None:
    print(package_print_string.format('Name', 'Namespace', 'Installed', 'Latest', 'Identifier'))

    for p in package_list:
        print_package_status(p)


def can_install(p: VSPackage) -> bool:
    return p.get_latest_installable_release() is not None


def make_pyversion(version: str, index: int) -> str:
    PEP440REGEX = re.compile(r'(\d+!)?\d+(\.\d+)*((?:a|b|rc)\d+)?(\.post\d+)?(\.dev\d+)?(\+[a-zA-Z0-9]+)?')

    version = version.lower().replace('-', '.')

    if version.startswith('rev'):
        return make_pyversion(version[3:], index)

    elif version.startswith('release_'):
        return make_pyversion(version[8:], index)

    elif version.startswith('r') or version.startswith('v'):
        return make_pyversion(version[1:], index)

    elif version.startswith('test'):
        return make_pyversion(version[4:], index)

    elif version.startswith('git:'):
        version = version[4:]
        return f'{index}+{version}'

    elif PEP440REGEX.match(version):
        return version

    else:
        return str(index)


def rmdir(path: Path) -> None:
    for file in path.iterdir():
        if file.is_dir():
            return rmdir(file)

        file.unlink(True)

    path.rmdir()


def find_dist_dirs(name: str, path: Optional[Path] = MISSING) -> Iterator[Path]:  # type: ignore[assignment]
    if path is MISSING:
        path = info.site_package_dir

    if path is None:
        return

    for targetname in path.iterdir():
        if not (targetname.name.startswith(f'{name}-') and targetname.name.endswith('.dist-info')):
            continue
        yield targetname


def remove_package_meta(pkg: VSPackage) -> None:
    if info.site_package_dir is None:
        return

    name = pkg.get_python_name()

    for dist_dir in find_dist_dirs(name):
        rmdir(dist_dir)


def install_package_meta(files: List[Tuple[Path, str, str]], pkg: VSPackage, rel: VSPackageRel, index: int) -> None:
    if info.site_package_dir is None:
        return

    name = pkg.get_python_name()

    version = make_pyversion(rel.version, index)
    dist_dir = info.site_package_dir / f'{name}-{version}.dist-info'

    remove_package_meta(pkg)

    dist_dir.mkdir(parents=True, exist_ok=True)

    inst_path, meta_path, recd_path = [dist_dir / name for name in ('INSTALLER', 'METADATA', 'RECORD')]

    files.extend([(path, '', '') for path in (inst_path, meta_path, recd_path)])

    inst_path.write_text('vsrepo')
    meta_path.write_text(
        f'Metadata-Version: 2.1\nName: {name}\nVersion: {version}\nSummary: {pkg.description or name}\nPlatform: All'
    )

    with open(recd_path, 'w', newline='') as f:
        w = csv.writer(f)
        for filename, sha256hex, length in files:
            if sha256hex:
                sha256hex = 'sha256=' + base64.urlsafe_b64encode(binascii.unhexlify(
                    sha256hex.encode('ascii'))).rstrip(b'=').decode('ascii')
            try:
                filename = filename.relative_to(info.site_package_dir)
            except ValueError:
                ...

            w.writerow([filename, sha256hex, length])


def install_files(p: VSPackage) -> InstallFileResult:
    err = InstallFileResult(0, 1)
    dest_path = p.get_install_path(info)

    idx, install_rel = p.get_latest_installable_release_with_index()

    if install_rel is None:
        return err

    release = install_rel.get_release(p.pkg_type)
    assert release

    data: Optional[bytearray] = None

    try:
        data = fetch_url_cached(release.url, f'{p.name} {install_rel.version}')
    except BaseException:
        print(
            f'Failed to download {p.name} {install_rel.version}, skipping installation and moving on'
        )

        return err

    files: List[Tuple[Path, str, str]] = []

    if p.pkg_type is VSPackageType.WHEEL:
        assert isinstance(release, VSPackagePlatformReleaseWheel)

        try:
            hash_result = check_hash(data, release.hash)

            if not hash_result[0]:
                raise ValueError(f'Hash mismatch for {release.url} got {hash_result[1]} but expected {hash_result[2]}')

            with zipfile.ZipFile(io.BytesIO(data), 'r') as zf:
                basename: Optional[str] = None

                for fn in zf.namelist():
                    if fn.endswith('.dist-info/WHEEL'):
                        basename = fn[:-len('.dist-info/WHEEL')]
                        break

                if basename is None:
                    raise Exception('Wheel: failed to determine package base name')

                for fn in zf.namelist():
                    if fn.startswith(f'{basename}.data'):
                        raise Exception('Wheel: .data dir mapping not supported')

                wheelfile = zf.read(f'{basename}.dist-info/WHEEL').decode().splitlines()
                wheeldict = {}

                for line in wheelfile:
                    tmp = line.split(': ', 2)
                    if len(tmp) == 2:
                        wheeldict[tmp[0]] = tmp[1]

                if wheeldict['Wheel-Version'] != '1.0':
                    raise Exception('Wheel: only version 1.0 supported')

                if wheeldict['Root-Is-Purelib'] != 'true':
                    raise Exception('Wheel: only purelib root supported')

                zf.extractall(path=dest_path)

                recd_path = dest_path / f'{basename}.dist-info' / 'RECORD'

                recd_path.write_text('vsrepo')

                newline_end = recd_path.read_text().endswith('\n')

                with open(recd_path, mode='a') as f:
                    if not newline_end:
                        f.write('\n')
                    f.write(f'{basename}.dist-info/INSTALLER,,\n')
        except BaseException as e:
            print(
                f'Failed to decompress {p.name} {install_rel.version} with error: {e},'
                ' skipping installation and moving on'
            )

            return err
    else:
        single_file: Optional[Tuple[Path, str, str]] = None

        if len(release.files) == 1:
            key, file = next(iter(release.files.items()))
            single_file = (key, file[0], file[1])

        if (single_file is not None) and (single_file[1] == release.url.rsplit('/', 2)[-1]):
            install_fn = single_file[0]
            hash_result = check_hash(data, single_file[2])

            if not hash_result[0]:
                raise Exception(
                    f'Hash mismatch for {install_fn} got {hash_result[1]} but expected {hash_result[2]}'
                )

            uninstall_files(p)

            (dest_path / install_fn.parent).mkdir(parents=True, exist_ok=True)

            out_file = dest_path / install_fn

            files.append((out_file, single_file[2], str(len(data))))
            out_file.write_bytes(data)
        else:
            tffd, _tfpath = tempfile.mkstemp(prefix='vsm')
            tfpath = Path(_tfpath)

            with open(tffd, mode='wb') as tf:
                tf.write(data)

            result_cache = {}

            for install_fn in release.files:
                fn_props = release.files[install_fn]
                result = subprocess.run(
                    [info.cmd7zip_path, 'e', '-so', tfpath, fn_props[0]],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                result.check_returncode()
                hash_result = check_hash(result.stdout, fn_props[1])

                if not hash_result[0]:
                    raise Exception(
                        f'Hash mismatch for {install_fn} got {hash_result[1]} but expected {hash_result[2]}'
                    )

                result_cache[install_fn] = (result.stdout, fn_props[1])

            uninstall_files(p)

            for install_fn in release.files:
                (dest_path / install_fn.parent).mkdir(parents=True, exist_ok=True)
                files.append((
                    dest_path / install_fn,
                    str(result_cache[install_fn][1]),
                    str(len(result_cache[install_fn][0]))
                ))
                (dest_path / install_fn).write_bytes(result_cache[install_fn][0])
            tfpath.unlink()

        install_package_meta(files, p, install_rel, idx)

    installed_packages[p.identifier] = install_rel.version

    print(f'Successfully installed {p.name} {install_rel.version}')

    return InstallFileResult(1, 0)


def install_package(name: str) -> InstallPackageResult:
    p = installed_packages.get_package_from_name(name)

    if get_vapoursynth_api_version() <= 3:
        if p.identifier in bundled_api3_plugins:
            print(f'Binaries are already bundled for {p.name}, skipping installation')
            return InstallPackageResult()

    if can_install(p):
        inst = InstallPackageResult()

        if not args.skip_deps:
            for dep in p.dependencies:
                inst += install_package(dep)

        if not installed_packages.is_package_installed(p.identifier):
            inst += install_files(p)

        return inst

    print(f'No binaries available for {args.target} in package {p.name}, skipping installation')

    return InstallPackageResult(error=1)


def upgrade_files(p: VSPackage) -> InstallPackageResult:
    if can_install(p):
        inst = InstallPackageResult()

        for dep in p.dependencies:
            if not installed_packages.is_package_installed(dep):
                inst += install_package(dep)

        return inst + install_files(p)

    print(f'No binaries available for {args.target} in package {p.name}, skipping installation')

    return InstallPackageResult(error=1)


def upgrade_package(name: str, force: bool) -> InstallPackageResult:
    p = installed_packages.get_package_from_name(name)

    if not installed_packages.is_package_installed(p.identifier):
        print(f'Package {p.name} not installed, can\'t upgrade')
    elif installed_packages.is_package_upgradable(p.identifier, force):
        return upgrade_files(p)
    elif not installed_packages.is_package_upgradable(p.identifier, True):
        print(f'Package {p.name} not upgraded, latest version installed')
    else:
        print(f'Package {p.name} not upgraded, unknown version must use -f to force replacement')

    return InstallPackageResult()


def uninstall_files(p: VSPackage) -> None:
    dest_path = p.get_install_path(info)

    if p.pkg_type is VSPackageType.WHEEL:
        files: List[Path] = []
        pyname = p.get_python_name()

        for dist_dir in find_dist_dirs(pyname, dest_path):
            lines = (dest_path / dist_dir / 'RECORD').read_text().splitlines()
            for line in lines:
                tmp = line.split(',')
                if tmp and len(tmp[0]) > 0:
                    files.append(Path(tmp[0]))

        print(files)

        for f in files:
            try:
                (dest_path / f).unlink(True)
            except BaseException as e:
                print(f'File removal error: {e}')

        for dist_dir in find_dist_dirs(pyname, dest_path):
            rmdir(dist_dir)
    else:
        installed_rel: Optional[VSPackageRel] = None
        if p.identifier in installed_packages:
            for rel in p.releases:
                if rel.version == installed_packages[p.identifier]:
                    installed_rel = rel
                    break
        if installed_rel is not None:
            prel = installed_rel.get_release(p.pkg_type)
            assert prel
            for f in prel.files:
                (dest_path / f).unlink(True)

        remove_package_meta(p)


def uninstall_package(name: str) -> InstallPackageResult:
    p = installed_packages.get_package_from_name(name)
    if installed_packages.is_package_installed(p.identifier):
        if installed_packages[p.identifier] == 'Unknown':
            print(f'Can\'t uninstall unknown version of package: {p.name}')
            return InstallPackageResult()

        uninstall_files(p)

        print(f'Uninstalled package: {p.name} {installed_packages[p.identifier]}')
        return InstallPackageResult(1)

    print(f'No files installed for {p.name}, skipping uninstall')

    return InstallPackageResult()


def update_package_definition(url: str) -> None:
    localmtimeval = 0.0

    try:
        localmtimeval = os.path.getmtime(info.package_json_path)
    except OSError:
        pass

    localmtime = formatdate(localmtimeval + 10, usegmt=True)
    req_obj = Request(url, headers={'If-Modified-Since': localmtime, 'User-Agent': 'VSRepo'})

    try:
        with urlopen(req_obj) as urlreq:
            remote_modtime = mktime_tz(parsedate_tz(urlreq.info()['Last-Modified']))

            data = urlreq.read()

            with zipfile.ZipFile(io.BytesIO(data), 'r') as zf:
                with zf.open('vspackages3.json') as pkgfile:
                    with open(info.package_json_path, 'wb') as dstfile:
                        dstfile.write(pkgfile.read())

                    os.utime(info.package_json_path, times=(remote_modtime, remote_modtime))
    except HTTPError as httperr:
        if httperr.code == 304:
            print(f'Local definitions already up to date: {formatdate(localmtimeval, usegmt=True)}')
        else:
            raise
    else:
        print(f'Local definitions updated to: {formatdate(remote_modtime, usegmt=True)}')


def update_genstubs() -> None:
    print('Updating VapourSynth stubs')

    version = str(api_ver) if (api_ver := get_vapoursynth_api_version()) > 3 else ''

    genstubs = info.file_dirname / f'vsgenstubs{version}' / '__init__.py'

    contents = subprocess.getoutput([sys.executable, genstubs, '-o', '-'])  # type: ignore

    site_package = False
    stubpath = Path(args.stub_output_file) if args.stub_output_file else None
    if stubpath == '-':
        stubpath = None
        fp = sys.stdout
    elif stubpath == '--':
        stubpath = None
        fp = sys.stderr
    else:
        if not stubpath:
            if info.site_package_dir:
                stubpath = info.site_package_dir
                site_package = True
            else:
                stubpath = Path('.')

        if stubpath.is_dir():
            stubpath = stubpath / 'vapoursynth.pyi'

        fp = open(stubpath, 'w')

    with fp:
        fp.write(contents)

    if site_package:
        if info.site_package_dir is None:
            return

        vs_stub_pkg = info.site_package_dir / 'vapoursynth-stubs'

        if vs_stub_pkg.exists():
            rmdir(vs_stub_pkg)

        vs_stub_pkg.mkdir(parents=True, exist_ok=True)

        if stubpath is None:
            return

        (vs_stub_pkg / '__init__.pyi').write_bytes(stubpath.read_bytes())

        stubpath.unlink()
        stubpath = vs_stub_pkg / '__init__.pyi'

        for dist_dir in find_dist_dirs('VapourSynth'):
            with open(dist_dir / 'RECORD') as f:
                contents = f.read()

            try:
                filename = stubpath.relative_to(info.site_package_dir)
            except ValueError:
                filename = stubpath

            if '__init__.pyi' not in contents or 'vapoursynth.pyi' not in contents:
                with open(dist_dir / 'RECORD', 'a') as f:
                    if not contents.endswith('\n'):
                        f.write('\n')
                    f.write(f'{filename},,\n')
            break


def rebuild_distinfo() -> None:
    print('Rebuilding dist-info dirs for other python package installers')

    for pkg_id, pkg_ver in installed_packages.items():
        pkg = installed_packages.get_package_from_id(pkg_id)

        if pkg is None:
            continue

        if pkg.pkg_type is VSPackageType.WHEEL:
            continue

        for idx, rel in enumerate(pkg.releases):
            if rel.version == pkg_ver:
                break
        else:
            remove_package_meta(pkg)
            continue

        dest_path = pkg.get_install_path(info)

        prel = rel.get_release(pkg.pkg_type)
        assert prel

        files = [
            ((path := (dest_path / fn)), fd[1], str(path.stat().st_size))
            for fn, fd in prel.files.items()
        ]

        install_package_meta(files, pkg, rel, idx)
