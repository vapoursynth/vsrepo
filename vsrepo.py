##    MIT License
##
##    Copyright (c) 2018-2020 Fredrik Mellbin
##
##    Permission is hereby granted, free of charge, to any person obtaining a copy
##    of this software and associated documentation files (the "Software"), to deal
##    in the Software without restriction, including without limitation the rights
##    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
##    copies of the Software, and to permit persons to whom the Software is
##    furnished to do so, subject to the following conditions:
##
##    The above copyright notice and this permission notice shall be included in all
##    copies or substantial portions of the Software.
##
##    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
##    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
##    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
##    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
##    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
##    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
##    SOFTWARE.

import argparse
import base64
import binascii
import csv
import email.utils
import glob
import hashlib
import importlib.util as imputil
import io
import json
import os
import os.path
import re
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from typing import Iterator, List, MutableMapping, Optional, Tuple

try:
    import winreg
except ImportError:
    print('{} is only supported on Windows.'.format(__file__))
    sys.exit(1)

try:
    import tqdm  # type: ignore
except ImportError:
    pass

bundled_api3_plugins = ['com.vapoursynth.avisource', 'com.vapoursynth.eedi3', 'com.vapoursynth.imwri', 'com.vapoursynth.misc', 'com.vapoursynth.morpho', 'com.vapoursynth.removegrainvs', 'com.vapoursynth.subtext', 'com.vapoursynth.vinverse', 'org.ivtc.v', 'com.nodame.histogram']


def is_venv() -> bool:
    return hasattr(sys, "real_prefix") or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)


def detect_vapoursynth_installation() -> str:
    try:
        spec = imputil.find_spec("vapoursynth")
        if spec is None:
            raise ModuleNotFoundError()
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


def is_sitepackage_install_portable() -> bool:
    if args.portable:
        return False

    vapoursynth_path = detect_vapoursynth_installation()
    return os.path.exists(os.path.join(os.path.dirname(vapoursynth_path), 'portable.vs'))

def is_sitepackage_install() -> bool:
    if args.portable:
        return False

    vapoursynth_path = detect_vapoursynth_installation()
    base_path = os.path.dirname(vapoursynth_path)

    # We reside in a venv.
    if is_venv():
        # VapourSynth has not been installed as a package.
        # Assume no site-package install
        if len(glob.glob(os.path.join(base_path, 'VapourSynth-*.dist-info'))) == 0:
            return False

        if os.path.exists(os.path.join(base_path, "portable.vs")):
            return True

        # Assume this is not a global install.
        return False

    # We do not reside in a venv.
    else:
        # pip install vapoursynth-portable
        # Install all packages to site-packages and treat them as packages.
        if len(glob.glob(os.path.join(base_path, 'VapourSynth_portable-*.dist-info'))) > 0:
            return True

        # This is a portable installation, this cannot be a site-package install.
        if os.path.exists(os.path.join(base_path, "portable.vs")):
            return False

        # This is a global install. Install dist-info files.
        return True

def get_vs_installation_site() -> str:
    if is_venv():
        try:
            return os.path.dirname(detect_vapoursynth_installation())
        except ImportError:
            import setuptools
            return os.path.dirname(os.path.dirname(setuptools.__file__))

    import site
    return site.getusersitepackages()


is_64bits: bool = sys.maxsize > 2**32

parser = argparse.ArgumentParser(description='A simple VapourSynth package manager')
parser.add_argument('operation', choices=['install', 'update', 'upgrade', 'upgrade-all', 'uninstall', 'installed', 'available', 'paths', "genstubs", "gendistinfo"])
parser.add_argument('package', nargs='*', help='identifier, namespace or module to install, upgrade or uninstall')
parser.add_argument('-f', action='store_true', dest='force', help='force upgrade for packages where the current version is unknown')
parser.add_argument('-p', action='store_true', dest='portable', help='use paths suitable for portable installs')
parser.add_argument('-d', action='store_true', dest='skip_deps', help='skip installing dependencies')
parser.add_argument('-t', choices=['win32', 'win64'], default='win64' if is_64bits else 'win32', dest='target', help='binaries to install, defaults to python\'s architecture')
parser.add_argument('-b', dest='binary_path', help='custom binary install path')
parser.add_argument('-s', dest='script_path', help='custom script install path')
parser.add_argument("--stub-output-file", default="", help="Don't update the typestubs generated by vsrepo.")
parser.add_argument("--force-dist-info", action="store_true", default=False, help="")
args = parser.parse_args()

is_64bits = args.target == 'win64'

file_dirname: str = os.path.dirname(os.path.abspath(__file__))

# VSRepo is installed to the site-packages.
if os.path.abspath(file_dirname).startswith(os.path.abspath(sys.prefix)):
    file_dirname = os.getcwd()

if args.portable:
    plugin32_path = os.path.join(file_dirname, 'vapoursynth32', 'plugins')
    plugin64_path = os.path.join(file_dirname, 'vapoursynth64', 'plugins')
elif is_sitepackage_install_portable():
    vapoursynth_path = detect_vapoursynth_installation()
    base_path = os.path.dirname(vapoursynth_path)
    plugin32_path = os.path.join(base_path, 'vapoursynth32', 'plugins')
    plugin64_path = os.path.join(base_path, 'vapoursynth64', 'plugins')
    del vapoursynth_path
else:
    pluginparent = [str(os.getenv("APPDATA")), 'VapourSynth']
    plugin32_path = os.path.join(*pluginparent, 'plugins32')
    plugin64_path = os.path.join(*pluginparent, 'plugins64')

if (args.operation in ['install', 'upgrade', 'uninstall']) and ((args.package is None) or len(args.package) == 0):
    print('Package argument required for install, upgrade and uninstall operations')
    sys.exit(1)

package_json_path = os.path.join(file_dirname, 'vspackages3.json') if args.portable else os.path.join(*pluginparent, 'vsrepo', 'vspackages3.json')

if args.force_dist_info or is_sitepackage_install():
    if is_venv():
        try:
            import setuptools
            site_package_dir: Optional[str] = os.path.dirname(os.path.dirname(setuptools.__file__))
            del setuptools
        except ImportError:
            site_package_dir = None
    else:
        import site
        site_package_dir = site.getusersitepackages()
else:
    site_package_dir = None

py_script_path: str = file_dirname if args.portable else (site_package_dir if site_package_dir is not None else get_vs_installation_site())
if args.script_path is not None:
    py_script_path = args.script_path


plugin_path: str = plugin64_path if is_64bits else plugin32_path
if args.binary_path is not None:
    plugin_path = args.binary_path

os.makedirs(py_script_path, exist_ok=True)
os.makedirs(plugin_path, exist_ok=True)
os.makedirs(os.path.dirname(package_json_path), exist_ok=True)


cmd7zip_path: str = os.path.join(file_dirname, '7z.exe')
if not os.path.isfile(cmd7zip_path):
    try:
        with winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\7-Zip', reserved=0, access=winreg.KEY_READ) as regkey:
            cmd7zip_path = os.path.join(winreg.QueryValueEx(regkey, 'Path')[0], '7z.exe')
    except:
        cmd7zip_path = '7z.exe'

installed_packages: MutableMapping = {}
download_cache: MutableMapping = {}

def fetch_ur1(url: str, desc: Optional[str] = None) -> bytearray:
    with urllib.request.urlopen(url) as urlreq:
        if ('tqdm' in sys.modules) and (urlreq.headers['content-length'] is not None):
            size = int(urlreq.headers['content-length'])
            remaining = size
            data = bytearray()
            with tqdm.tqdm(total=size, unit='B', unit_scale=True, unit_divisor=1024, desc=desc) as t:
                while remaining > 0:
                    blocksize = min(remaining, 1024*128)
                    data.extend(urlreq.read(blocksize))
                    remaining = remaining - blocksize
                    t.update(blocksize)
            return data
        else:
            print('Fetching: ' + url)
            return urlreq.read()

def fetch_url_cached(url: str, desc: str = "") -> bytearray:
    data = download_cache.get(url, None)
    if data is None:
        data = fetch_ur1(url, desc)
        download_cache[url] = data
    return data

package_print_string = "{:25s} {:15s} {:11s} {:11s} {:s}"

package_list: Optional[MutableMapping] = None
try:
    with open(package_json_path, 'r', encoding='utf-8') as pl:
        package_list = json.load(pl)
    if package_list is None:
        raise ValueError()
    if package_list['file-format'] != 3:
        print('Package definition format is {} but only version 3 is supported'.format(package_list['file-format']))
        raise ValueError()
    package_list = package_list.get('packages')
except (OSError, FileExistsError, ValueError):
    pass

def check_hash(data: bytes, ref_hash: str) -> Tuple[bool, str, str]:
    data_hash = hashlib.sha256(data).hexdigest()
    return (data_hash == ref_hash, data_hash, ref_hash)

def get_bin_name(p: MutableMapping):
    if p['type'] == 'PyScript':
        return 'script'
    if p['type'] == 'PyWheel':
        return 'wheel'
    elif p['type'] == 'VSPlugin':
        if is_64bits:
            return 'win64'
        else:
            return 'win32'
    else:
        raise ValueError('Unknown install type')

def get_install_path(p: MutableMapping) -> str:
    if p['type'] == 'PyScript' or p['type'] == 'PyWheel':
        return py_script_path
    elif p['type'] == 'VSPlugin':
        return plugin_path
    else:
        raise ValueError('Unknown install type')

def get_package_from_id(id: str, required: bool = False) -> Optional[MutableMapping]:
    if package_list is None:
        return None
    for p in package_list:
        if p['identifier'] == id:
            return p
    if required:
        raise ValueError(f'No package with the identifier {id} found')
    return None

def get_package_from_plugin_name(name: str, required: bool = False) -> Optional[MutableMapping]:
    if package_list is None:
        return None
    for p in package_list:
        if p['name'].casefold() == name.casefold():
            return p
    if required:
        raise ValueError(f'No package with the name {name} found')
    return None

def get_package_from_namespace(namespace: str, required: bool = False) -> Optional[MutableMapping]:
    if package_list is None:
        return None
    for p in package_list:
        if 'namespace' in p:
            if p['namespace'] == namespace:
                return p
    if required:
        raise ValueError(f'No package with the namespace {namespace} found')
    return None

def get_package_from_modulename(modulename: str, required: bool = False) -> Optional[MutableMapping]:
    if package_list is None:
        return None
    for p in package_list:
        if 'modulename' in p:
            if p['modulename'] == modulename:
                return p
    if required:
        raise ValueError(f'No package with the modulename {modulename} found')
    return None

def get_package_from_name(name: str) -> MutableMapping:
    p = get_package_from_id(name)
    if p is None:
        p = get_package_from_namespace(name)
    if p is None:
        p = get_package_from_modulename(name)
    if p is None:
        p = get_package_from_plugin_name(name)
    if p is None:
        raise ValueError(f'Package {name} not found')
    return p

def is_package_installed(id: str) -> bool:
    return id in installed_packages

def is_package_upgradable(id: str, force: bool) -> bool:
    pkg = get_package_from_id(id, True)
    if pkg is None:
        return False
    lastest_installable = get_latest_installable_release(pkg)
    if force:
        return (is_package_installed(id) and (lastest_installable is not None) and (installed_packages[id] != lastest_installable['version']))
    else:
        return (is_package_installed(id) and (lastest_installable is not None) and (installed_packages[id] != 'Unknown') and (installed_packages[id] != lastest_installable['version']))

def get_python_package_name(pkg: MutableMapping) -> str:
    if "wheelname" in pkg:
        return pkg["wheelname"].replace(".", "_").replace(" ", "_").replace("(", "_").replace(")", "")
    else:
        return pkg["name"].replace(".", "_").replace(" ", "_").replace("(", "_").replace(")", "")

def find_dist_version(pkg: MutableMapping, path: Optional[str]) -> Optional[str]:
    if path is None:
        return None

    name = get_python_package_name(pkg)
    versions: List[str] = []

    for targetname in os.listdir(path):
        if (targetname.startswith(f"{name}-") and targetname.endswith(".dist-info")):
            # only bother with dist-info dirs that actually have a usable record in case a package uninstall failed to delete the dir
            if os.path.isfile(os.path.join(path, targetname, 'RECORD')):
                versions.append(targetname[len(name)+1:-10])

    versions.sort(reverse=True)
    return versions[0] if len(versions) > 0 else None

def detect_installed_packages() -> None:
    if package_list is not None:
        for p in package_list:
            dest_path = get_install_path(p)
            if p['type'] == 'PyWheel':
                version = find_dist_version(p, dest_path)
                if version is not None:
                    installed_packages[p['identifier']] = version
            else:
                for v in p['releases']:
                    matched = True
                    exists = True
                    bin_name = get_bin_name(p)
                    if bin_name in v:
                        for f in v[bin_name]['files']:
                            try:
                                with open(os.path.join(dest_path, f), 'rb') as fh:
                                    if not check_hash(fh.read(), v[bin_name]['files'][f][1])[0]:
                                        matched = False
                            except FileNotFoundError:
                                exists = False
                                matched = False
                        if matched:
                            installed_packages[p['identifier']] = v['version']
                            break
                        elif exists:
                            installed_packages[p['identifier']] = 'Unknown'
    else:
        print('No valid package definitions found. Run update command first!')
        sys.exit(1)

def print_package_status(p: MutableMapping) -> None:
    lastest_installable = get_latest_installable_release(p)
    name = p['name']
    if is_package_upgradable(p['identifier'], False):
        name = '*' + name
    elif is_package_upgradable(p['identifier'], True):
        name = '+' + name
    print(package_print_string.format(name, p['namespace'] if p['type'] == 'VSPlugin' else p['modulename'], installed_packages.get(p['identifier'], ""), lastest_installable.get('version') if lastest_installable is not None else '', p['identifier']))

def list_installed_packages() -> None:
    print(package_print_string.format('Name', 'Namespace', 'Installed', 'Latest', 'Identifier'))
    for id in installed_packages:
        pkg = get_package_from_id(id, True)
        if pkg is not None:
            print_package_status(pkg)

def list_available_packages() -> None:
    print(package_print_string.format('Name', 'Namespace', 'Installed', 'Latest', 'Identifier'))
    if package_list is None:
        print("Nothing available to list, please try updating first.")
        return
    for p in package_list:
        print_package_status(p)

def get_latest_installable_release_with_index(p: MutableMapping) -> Tuple[int, Optional[MutableMapping]]:
    max_api = get_vapoursynth_api_version()
    package_api: int = 3
    if 'api' in p:
        package_api = int(p['api'])
    bin_name = get_bin_name(p)
    for idx, rel in enumerate(p['releases']):
        if not isinstance(rel, MutableMapping):
            continue
        if bin_name in rel:
            bin_api: int = package_api
            if 'api' in rel[bin_name]:
                bin_api = int(rel[bin_name]['api'])
            if bin_api <= max_api and bin_api >= 3:
                return (idx, rel)
    return (-1, None)

def get_latest_installable_release(p: MutableMapping) -> Optional[MutableMapping]:
    return get_latest_installable_release_with_index(p)[1]

def can_install(p: MutableMapping) -> bool:
    return get_latest_installable_release(p) is not None


def make_pyversion(version: str, index: int) -> str:
    PEP440REGEX = re.compile(r"(\d+!)?\d+(\.\d+)*((?:a|b|rc)\d+)?(\.post\d+)?(\.dev\d+)?(\+[a-zA-Z0-9]+)?")

    version = version.lower().replace("-", ".")

    if version.startswith("rev"):
        return make_pyversion(version[3:], index)

    elif version.startswith("release_"):
        return make_pyversion(version[8:], index)

    elif version.startswith("r") or version.startswith("v"):
        return make_pyversion(version[1:], index)

    elif version.startswith("test"):
        return make_pyversion(version[4:], index)

    elif version.startswith("git:"):
        version = version[4:]
        return f"{index}+{version}"

    elif PEP440REGEX.match(version):
        return version

    else:
        return str(index)


def rmdir(path: str) -> None:
    for path, _, fnames in os.walk(path, topdown=False):
        for fname in fnames:
            os.remove(os.path.join(path, fname))
        os.rmdir(path)

# Annotated as Iterator due to https://docs.python.org/3/library/typing.html#typing.Generator
# See the portion about only yielding values, it's an alternative to Generator[str, None, None]
def find_dist_dirs(name: str, path: Optional[str] = site_package_dir) -> Iterator[str]:
    if path is None:
        return

    for targetname in os.listdir(path):
        if not (targetname.startswith(f"{name}-") and targetname.endswith(".dist-info")):
            continue
        yield os.path.join(path, targetname)


def remove_package_meta(pkg: MutableMapping) -> None:
    if site_package_dir is None:
        return

    name = get_python_package_name(pkg)

    for dist_dir in find_dist_dirs(name):
        rmdir(dist_dir)


def install_package_meta(files: List[Tuple[str, str, str]], pkg: MutableMapping, rel: MutableMapping, index: int) -> None:
    if site_package_dir is None:
        return

    name = get_python_package_name(pkg)

    version = make_pyversion(rel["version"], index)
    dist_dir = os.path.join(site_package_dir, f"{name}-{version}.dist-info")

    remove_package_meta(pkg)

    os.mkdir(dist_dir)
    with open(os.path.join(dist_dir, "INSTALLER"), "w") as f:
        files.append((os.path.join(dist_dir, "INSTALLER"), "" ,""))
        f.write("vsrepo")
    with open(os.path.join(dist_dir, "METADATA"), "w") as f:
        files.append((os.path.join(dist_dir, "METADATA"), "" ,""))
        f.write(f"""Metadata-Version: 2.1
Name: {name}
Version: {version}
Summary: {pkg.get('description', name)}
Platform: All""")

    with open(os.path.join(dist_dir, "RECORD"), "w", newline="") as f:
        files.append((os.path.join(dist_dir, "RECORD"), "", ""))
        w = csv.writer(f)
        for filename, sha256hex, length in files:
            if sha256hex:
                sha256hex = "sha256=" + base64.urlsafe_b64encode(binascii.unhexlify(sha256hex.encode("ascii"))).rstrip(b"=").decode("ascii")
            try:
                filename = os.path.relpath(filename, site_package_dir)
            except ValueError:
                pass
            w.writerow([filename, sha256hex, length])


def install_files(p: MutableMapping) -> Tuple[int, int]:
    err = (0, 1)
    dest_path = get_install_path(p)
    bin_name = get_bin_name(p)
    idx, install_rel = get_latest_installable_release_with_index(p)
    if install_rel is None:
        return err
    url = install_rel[bin_name]['url']
    data: Optional[bytearray] = None
    try:
        data = fetch_url_cached(url, p['name'] + ' ' + install_rel['version'])
    except:
        print('Failed to download ' + p['name'] + ' ' + install_rel['version'] + ', skipping installation and moving on')
        return err

    files: List[Tuple[str, str, str]] = []

    if bin_name == 'wheel':
        try:
            hash_result = check_hash(data, install_rel[bin_name]['hash'])
            if not hash_result[0]:
                raise ValueError('Hash mismatch for ' + url + ' got ' + hash_result[1] + ' but expected ' + hash_result[2])
            with zipfile.ZipFile(io.BytesIO(data), 'r') as zf:
                basename: Optional[str] = None
                for fn in zf.namelist():
                    if fn.endswith('.dist-info/WHEEL'):
                        basename = fn[:-len('.dist-info/WHEEL')]
                        break
                if basename is None:
                    raise Exception('Wheel: failed to determine package base name')
                for fn in zf.namelist():
                    if fn.startswith(basename + '.data'):
                        raise Exception('Wheel: .data dir mapping not supported')
                wheelfile = zf.read(basename + '.dist-info/WHEEL').decode().splitlines()
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
                with open(os.path.join(dest_path, basename + '.dist-info', 'INSTALLER'), mode='w') as f:
                    f.write("vsrepo")
                with open(os.path.join(dest_path, basename + '.dist-info', 'RECORD')) as f:
                    contents = f.read()
                with open(os.path.join(dest_path, basename + '.dist-info', 'RECORD'), mode='a') as f:
                    if not contents.endswith("\n"):
                        f.write("\n")
                    f.write(basename + '.dist-info/INSTALLER,,\n')
        except BaseException as e:
            print('Failed to decompress ' + p['name'] + ' ' + install_rel['version'] + ' with error: ' + str(e) + ', skipping installation and moving on')
            return err
    else:
        single_file: Optional[Tuple[str, str, str]] = None
        if len(install_rel[bin_name]['files']) == 1:
            for key in install_rel[bin_name]['files']:
                single_file = (key, install_rel[bin_name]['files'][key][0], install_rel[bin_name]['files'][key][1])
        if (single_file is not None) and (single_file[1] == url.rsplit('/', 2)[-1]):
            install_fn = single_file[0]
            hash_result = check_hash(data, single_file[2])
            if not hash_result[0]:
                raise Exception('Hash mismatch for ' + install_fn + ' got ' + hash_result[1] + ' but expected ' + hash_result[2])
            uninstall_files(p)
            os.makedirs(os.path.join(dest_path, os.path.split(install_fn)[0]), exist_ok=True)
            with open(os.path.join(dest_path, install_fn), 'wb') as outfile:
                files.append((os.path.join(dest_path, install_fn), single_file[2], str(len(data))))
                outfile.write(data)
        else:
            tffd, tfpath = tempfile.mkstemp(prefix='vsm')
            with open(tffd, mode='wb') as tf:
                tf.write(data)
            result_cache = {}
            for install_fn in install_rel[bin_name]['files']:
                fn_props = install_rel[bin_name]['files'][install_fn]
                result = subprocess.run([cmd7zip_path, "e", "-so", tfpath, fn_props[0]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                result.check_returncode()
                hash_result = check_hash(result.stdout, fn_props[1])
                if not hash_result[0]:
                    raise Exception('Hash mismatch for ' + install_fn + ' got ' + hash_result[1] + ' but expected ' + hash_result[2])
                result_cache[install_fn] = (result.stdout, fn_props[1])
            uninstall_files(p)
            for install_fn in install_rel[bin_name]['files']:
                os.makedirs(os.path.join(dest_path, os.path.split(install_fn)[0]), exist_ok=True)
                with open(os.path.join(dest_path, install_fn), 'wb') as outfile:
                    files.append((os.path.join(dest_path, install_fn), str(result_cache[install_fn][1]), str(len(result_cache[install_fn][0]))))
                    outfile.write(result_cache[install_fn][0])
            os.remove(tfpath)

        install_package_meta(files, p, install_rel, idx)

    installed_packages[p['identifier']] = install_rel['version']
    print('Successfully installed ' + p['name'] + ' ' + install_rel['version'])
    return (1, 0)

def install_package(name: str) -> Tuple[int, int, int]:
    p = get_package_from_name(name)
    if get_vapoursynth_api_version() <= 3:
        if p['identifier'] in bundled_api3_plugins:
            print('Binaries are already bundled for ' + p['name'] + ', skipping installation')
            return (0, 0, 0)
    if can_install(p):
        inst = (0, 0, 0)
        if not args.skip_deps:
            if 'dependencies' in p:
                for dep in p['dependencies']:
                    if not isinstance(dep, str):
                        continue
                    res = install_package(dep)
                    inst = (inst[0], inst[1] + res[0] + res[1], inst[2] + res[2])
        if not is_package_installed(p['identifier']):
            fres = install_files(p)
            inst = (inst[0] + fres[0], inst[1], inst[2] + fres[1])
        return inst
    else:
        print('No binaries available for ' + args.target + ' in package ' + p['name'] + ', skipping installation')
        return (0, 0, 1)

def upgrade_files(p: MutableMapping) -> Tuple[int, int, int]:
    if can_install(p):
        inst = (0, 0, 0)
        if 'dependencies' in p:
            for dep in p['dependencies']:
                if not is_package_installed(dep):
                    res = install_package(dep)
                    inst = (inst[0], inst[1] + res[0] + res[1], inst[2] + res[2])
        fres = install_files(p)
        return (inst[0] + fres[0], inst[1], inst[2] + fres[1])
    else:
        print('No binaries available for ' + args.target + ' in package ' + p['name'] + ', skipping installation')
        return (0, 0, 1)

def upgrade_package(name, force) -> Tuple[int, int, int]:
    inst = (0, 0, 0)
    p = get_package_from_name(name)
    if not is_package_installed(p['identifier']):
        print('Package ' + p['name'] + ' not installed, can\'t upgrade')
    elif is_package_upgradable(p['identifier'], force):
        res = upgrade_files(p)
        return (res[0], 0, res[1])
    elif not is_package_upgradable(p['identifier'], True):
        print('Package ' + p['name'] + ' not upgraded, latest version installed')
    else:
        print('Package ' + p['name'] + ' not upgraded, unknown version must use -f to force replacement')
    return inst

def upgrade_all_packages(force: bool) -> Tuple[int, int, int]:
    inst = (0, 0, 0)
    installed_ids: List[str] = list(installed_packages.keys())
    for id in installed_ids:
        if is_package_upgradable(id, force):
            pkg = get_package_from_id(id, True)
            if pkg is None:
                return inst
            res = upgrade_files(pkg)
            inst = (inst[0] + res[0], inst[1] + res[1], inst[2] + res[2])
    return inst

def uninstall_files(p: MutableMapping) -> None:
    dest_path = get_install_path(p)
    bin_name = get_bin_name(p)

    if p['type'] == 'PyWheel':
        files: List[str] = []
        pyname = get_python_package_name(p)
        for dist_dir in find_dist_dirs(pyname, dest_path):
            with open(os.path.join(dest_path, dist_dir, 'RECORD'), mode='r') as rec:
                lines = rec.read().splitlines()
                for line in lines:
                    tmp = line.split(',')
                    if len(tmp) > 0 and len(tmp[0]) > 0:
                        files.append(tmp[0])
        print(files)
        for f in files:
            try:
                os.remove(os.path.join(dest_path, f))
            except BaseException as e:
                print('File removal error: ' + str(e))
        for dist_dir in find_dist_dirs(pyname, dest_path):
            rmdir(dist_dir)
    else:
        installed_rel: Optional[MutableMapping] = None
        if p['identifier'] in installed_packages:
            for rel in p['releases']:
                if rel['version'] == installed_packages[p['identifier']]:
                    installed_rel = rel
                    break
        if installed_rel is not None:
            for f in installed_rel[bin_name]['files']:
                os.remove(os.path.join(dest_path, f))

        remove_package_meta(p)

def uninstall_package(name: str) -> Tuple[int, int]:
    p = get_package_from_name(name)
    if is_package_installed(p['identifier']):
        if installed_packages[p['identifier']] == 'Unknown':
            print('Can\'t uninstall unknown version of package: ' + p['name'])
            return (0, 0)
        else:
            uninstall_files(p)
            print('Uninstalled package: ' + p['name'] + ' ' + installed_packages[p['identifier']])
            return (1, 0)
    else:
        print('No files installed for ' + p['name'] + ', skipping uninstall')
        return (0, 0)

def update_package_definition(url: str) -> None:
    localmtimeval = 0.0
    try:
        localmtimeval = os.path.getmtime(package_json_path)
    except:
        pass
    localmtime = email.utils.formatdate(localmtimeval + 10, usegmt=True)
    req_obj = urllib.request.Request(url, headers={ 'If-Modified-Since': localmtime, 'User-Agent': 'VSRepo' })
    try:
        with urllib.request.urlopen(req_obj) as urlreq:
            remote_modtime = email.utils.mktime_tz(email.utils.parsedate_tz(urlreq.info()['Last-Modified']))
            data = urlreq.read()
            with zipfile.ZipFile(io.BytesIO(data), 'r') as zf:
                with zf.open('vspackages3.json') as pkgfile:
                    with open(package_json_path, 'wb') as dstfile:
                        dstfile.write(pkgfile.read())
                    os.utime(package_json_path, times=(remote_modtime, remote_modtime))
    except urllib.error.HTTPError as httperr:
        if httperr.code == 304:
            print('Local definitions already up to date: ' + email.utils.formatdate(localmtimeval, usegmt=True))
        else:
            raise
    else:
        print('Local definitions updated to: ' + email.utils.formatdate(remote_modtime, usegmt=True))


def get_vapoursynth_version() -> int:
    try:
        import vapoursynth
    except ImportError:
        return 1

    if hasattr(vapoursynth, "__version__"):
        return vapoursynth.__version__[0]
    return vapoursynth.core.version_number()

def get_vapoursynth_api_version() -> int:
    try:
        import vapoursynth
    except ImportError:
        return 1

    if hasattr(vapoursynth, "__api_version__"):
        return vapoursynth.__api_version__[0]
    # assume lowest widespread api version, will probably error out somewhere else
    return 3


def update_genstubs() -> None:
    print("Updating VapourSynth stubs")

    if get_vapoursynth_api_version() > 3:
        genstubs = os.path.join(os.path.dirname(__file__), "vsgenstubs4/__init__.py")
    else:
        genstubs = os.path.join(os.path.dirname(__file__), "vsgenstubs/__init__.py")
    contents = subprocess.getoutput([sys.executable, genstubs, '-o', '-'])  # type: ignore

    site_package = False
    stubpath: Optional[str] = args.stub_output_file
    if stubpath == "-":
        stubpath = None
        fp = sys.stdout
    elif stubpath == "--":
        stubpath = None
        fp = sys.stderr
    else:
        if not stubpath:
            if site_package_dir:
                stubpath = site_package_dir
                site_package = True
            else:
                stubpath = "."

        if os.path.isdir(stubpath):
            stubpath = os.path.join(stubpath, "vapoursynth.pyi")

        fp = open(stubpath, "w")

    with fp:
        fp.write(contents)

    if site_package:
        if site_package_dir is None:
            return
        vs_stub_pkg = os.path.join(site_package_dir, "vapoursynth-stubs")
        if os.path.exists(vs_stub_pkg):
            rmdir(vs_stub_pkg)

        os.makedirs(vs_stub_pkg)

        if stubpath is None:
            return
        with open(stubpath, "rb") as src:
            with open(os.path.join(vs_stub_pkg, "__init__.pyi"), "wb") as dst:
                dst.write(src.read())
        os.remove(stubpath)
        stubpath = os.path.join(vs_stub_pkg, "__init__.pyi")

        for dist_dir in find_dist_dirs("VapourSynth"):
            with open(os.path.join(dist_dir, "RECORD")) as f:
                contents = f.read()

            try:
                filename = os.path.relpath(stubpath, site_package_dir)
            except ValueError:
                filename = stubpath

            if "__init__.pyi" not in contents or "vapoursynth.pyi" not in contents:
                with open(os.path.join(dist_dir, "RECORD"), "a") as f:
                    if not contents.endswith("\n"):
                        f.write("\n")
                    f.write(f"{filename},,\n")
            break

def rebuild_distinfo() -> None:
    print("Rebuilding dist-info dirs for other python package installers")
    for pkg_id, pkg_ver in installed_packages.items():
        pkg = get_package_from_id(pkg_id)
        if pkg is None:
            continue
        if pkg['type'] == 'PyWheel':
            continue

        for idx, rel in enumerate(pkg["releases"]):
            if rel["version"] == pkg_ver:
                break
        else:
            remove_package_meta(pkg)
            continue

        dest_path = get_install_path(pkg)
        bin_name = get_bin_name(pkg)
        files = [
            (os.path.join(dest_path, fn), fd[1], str(os.stat(os.path.join(dest_path, fn)).st_size))
            for fn, fd in rel[bin_name]["files"].items()
        ]

        install_package_meta(files, pkg, rel, idx)


def print_paths():
    print('Paths:')
    print('Definitions: ' + package_json_path)
    print('Binaries: ' + plugin_path)
    print('Scripts: ' + py_script_path)

    if site_package_dir is not None:
        print("Dist-Infos: " + site_package_dir)
    else:
        print("Dist-Infos: <Will not be installed>")

if args.operation != 'update' and package_list is None:
    print('Failed to open vspackages3.json. Run update command.')
    sys.exit(1)

for name in args.package:
    try:
        assert isinstance(name, str)
        get_package_from_name(name)
    except Exception as e:
        print(e)
        sys.exit(1)

if args.operation == 'install':
    detect_installed_packages()
    rebuild_distinfo()

    inst = (0, 0, 0)
    for name in args.package:
        res = install_package(name)
        inst = (inst[0] + res[0], inst[1] + res[1], inst[2] + res[2])

    update_genstubs()

    if (inst[0] == 0) and (inst[1] == 0):
        print('Nothing done')
    elif (inst[0] > 0) and (inst[1] == 0):
        print('{} {} installed'.format(inst[0], 'package' if inst[0] == 1 else 'packages'))
    elif (inst[0] == 0) and (inst[1] > 0):
        print('{} missing {} installed'.format(inst[1], 'dependency' if inst[1] == 1 else 'dependencies'))
    else:
        print('{} {} and {} additional {} installed'.format(inst[0], 'package' if inst[0] == 1 else 'packages', inst[1], 'dependency' if inst[1] == 1 else 'dependencies'))
    if (inst[2] > 0):
        print('{} {} failed'.format(inst[2], 'package' if inst[0] == 1 else 'packages'))
elif args.operation in ('upgrade', 'upgrade-all'):
    detect_installed_packages()
    rebuild_distinfo()

    inst = (0, 0, 0)
    if args.operation == 'upgrade-all':
        inst = upgrade_all_packages(args.force)
    else:
        for name in args.package:
            res = upgrade_package(name, args.force)
            inst = (inst[0] + res[0], inst[1] + res[1], inst[2] + res[2])

    update_genstubs()

    if (inst[0] == 0) and (inst[1] == 0):
        print('Nothing done')
    elif (inst[0] > 0) and (inst[1] == 0):
        print('{} {} upgraded'.format(inst[0], 'package' if inst[0] == 1 else 'packages'))
    elif (inst[0] == 0) and (inst[1] > 0):
        print('{} missing {} installed'.format(inst[1], 'dependency' if inst[1] == 1 else 'dependencies'))
    else:
        print('{} {} upgraded and {} additional {} installed'.format(inst[0], 'package' if inst[0] == 1 else 'packages', inst[1], 'dependency' if inst[1] == 1 else 'dependencies'))
    if (inst[2] > 0):
        print('{} {} failed'.format(inst[2], 'package' if inst[0] == 1 else 'packages'))
elif args.operation == 'uninstall':
    detect_installed_packages()
    uninst = (0, 0)
    for name in args.package:
        uninst_res = uninstall_package(name)
        uninst = (uninst[0] + uninst_res[0], uninst[1] + uninst_res[1])
    if uninst[0] == 0:
        print('No packages uninstalled')
    else:
        print('{} {} uninstalled'.format(uninst[0], 'package' if uninst[0] == 1 else 'packages'))
    update_genstubs()
elif args.operation == 'installed':
    detect_installed_packages()
    list_installed_packages()
elif args.operation == 'available':
    detect_installed_packages()
    list_available_packages()
elif args.operation == 'update':
    update_package_definition('http://www.vapoursynth.com/vsrepo/vspackages3.zip')
elif args.operation == 'paths':
    print_paths()
elif args.operation == "genstubs":
    update_genstubs()
elif args.operation == "gendistinfo":
    detect_installed_packages()
    rebuild_distinfo()


def noop():
    pass
