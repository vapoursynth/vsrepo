##    MIT License
##
##    Copyright (c) 2018 Fredrik Mellbin
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

import sys
import json
import hashlib
import urllib.request
import io
import site
import os
import os.path
import subprocess
import tempfile
import argparse
import email.utils
import time
import zipfile

try:
    import winreg
except ImportError:
    print('{} is only supported on Windows.'.format(__file__))
    exit(1)

try:
    import tqdm
except ImportError:
    pass


def is_sitepackage_install_portable():
    try:
        import vapoursynth
    except ImportError:
        return False
    else:
        return os.path.exists(os.path.join(os.path.dirname(vapoursynth.__file__), 'portable.vs'))

is_64bits = sys.maxsize > 2**32

parser = argparse.ArgumentParser(description='A simple VapourSynth package manager')
parser.add_argument('operation', choices=['install', 'update', 'upgrade', 'upgrade-all', 'uninstall', 'installed', 'available', 'paths'])
parser.add_argument('package', nargs='*', help='identifier, namespace or module to install, upgrade or uninstall')
parser.add_argument('-f', action='store_true', dest='force', help='force upgrade for packages where the current version is unknown')
parser.add_argument('-t', choices=['win32', 'win64'], default='win64' if is_64bits else 'win32', dest='target', help='binaries to install, defaults to python\'s architecture')
parser.add_argument('-p', action='store_true', dest='portable', help='use paths suitable for portable installs')
parser.add_argument('-b', dest='binary_path', help='custom binary install path')
parser.add_argument('-s', dest='script_path', help='custom script install path')
args = parser.parse_args()
is_64bits = (args.target == 'win64')

if (args.operation in ['install', 'upgrade', 'uninstall']) == ((args.package is None) or len(args.package) == 0):
    print('Package argument only required for install, upgrade and uninstall operations')
    exit(1)

package_json_path = os.path.join(os.path.dirname(__file__), 'vspackages.json') if args.portable else os.path.join(os.getenv('APPDATA'), 'VapourSynth', 'vsrepo', 'vspackages.json')

py_script_path = os.path.dirname(__file__) if args.portable else site.getusersitepackages()
if args.script_path is not None:
    py_script_path = args.script_path

if args.portable:
    base_path = os.path.dirname(__file__)
    plugin32_path = os.path.join(base_path, 'vapoursynth32', 'plugins')
    plugin64_path = os.path.join(base_path, 'vapoursynth64', 'plugins')
elif is_sitepackage_install_portable():
    import vapoursynth
    base_path = os.path.dirname(vapoursynth.__file__)
    plugin32_path = os.path.join(base_path, 'vapoursynth32', 'plugins')
    plugin64_path = os.path.join(base_path, 'vapoursynth64', 'plugins')
    del vapoursynth
else:
    plugin32_path = os.path.join(os.getenv('APPDATA'), 'VapourSynth', 'plugins32')
    plugin64_path = os.path.join(os.getenv('APPDATA'), 'VapourSynth', 'plugins64')

plugin_path = plugin64_path if is_64bits else plugin32_path
if args.binary_path is not None:
    plugin_path = args.binary_path
	
os.makedirs(py_script_path, exist_ok=True)
os.makedirs(plugin_path, exist_ok=True)
os.makedirs(os.path.dirname(package_json_path), exist_ok=True)

cmd7zip_path = '7z.exe'
try:
    with winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\7-Zip', reserved=0, access=winreg.KEY_READ) as regkey:
        cmd7zip_path = winreg.QueryValueEx(regkey, 'Path')[0] + '7z.exe'
except:
    pass

installed_packages = {}
download_cache = {}

def fetch_ur1(url, desc = None):
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

def fetch_url_cached(url, desc):
    data = download_cache.get(url, None)
    if data is None:
        data = fetch_ur1(url, desc)
        download_cache[url] = data
    return data

package_print_string = "{:25s} {:15s} {:11s} {:11s} {:s}"

package_list = None
try:
    with open(package_json_path, 'r', encoding='utf-8') as pl:
        package_list = json.load(pl)       
    if package_list['file-format'] != 2:
        print('Package definition format is {} but only version 1 is supported'.format(package_list['file_format']))
        package_list = None
    package_list = package_list['packages']
except:
    pass

def check_hash(data, ref_hash):
    data_hash = hashlib.sha256(data).hexdigest()
    return (data_hash == ref_hash, data_hash, ref_hash)        

def get_bin_name(p):
    if p['type'] == 'PyScript':
        return 'script'
    elif p['type'] == 'VSPlugin':
        if is_64bits:
            return 'win64'
        else:
            return 'win32'
    else:
        raise Exception('Unknown install type')

def get_install_path(p):
    if p['type'] == 'PyScript':
        return py_script_path
    elif p['type'] == 'VSPlugin':
        return plugin_path
    else:
        raise Exception('Unknown install type')

def get_package_from_id(id, required = False):
    for p in package_list:
        if p['identifier'] == id:
            return p
    if required:
        raise Exception('No package with the identifier ' + id + ' found')
    return None
	
def get_package_from_plugin_name(name, required = False):
    for p in package_list:
        if p['name'].casefold() == name.casefold():
            return p
    if required:
        raise Exception('No package with the name ' + name + ' found')
    return None

def get_package_from_namespace(namespace, required = False):
    for p in package_list:
        if 'namespace' in p:
            if p['namespace'] == namespace:
                return p
    if required:
        raise Exception('No package with the namespace ' + namespace + ' found')
    return None

def get_package_from_modulename(modulename, required = False):
    for p in package_list:
        if 'modulename' in p:
            if p['modulename'] == modulename:
                return p
    if required:
        raise Exception('No package with the modulename ' + modulename + ' found')
    return None

def get_package_from_name(name):
    p = get_package_from_id(name)
    if p is None:
        p = get_package_from_namespace(name)
    if p is None:
        p = get_package_from_modulename(name)
    if p is None:
        p = get_package_from_plugin_name(name)
    if p is None:
        raise Exception('Package ' + name + ' not found')
    return p

def is_package_installed(id):
    return id in installed_packages

def is_package_upgradable(id, force):
    lastest_installable = get_latest_installable_release(get_package_from_id(id, True))
    if force:
        return (is_package_installed(id) and (lastest_installable is not None) and (installed_packages[id] != lastest_installable['version']))
    else:
        return (is_package_installed(id) and (lastest_installable is not None) and (installed_packages[id] != 'Unknown') and (installed_packages[id] != lastest_installable['version']))

def detect_installed_packages():
    if package_list is not None:
        for p in package_list:
            dest_path = get_install_path(p)
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

def print_package_status(p):
    lastest_installable = get_latest_installable_release(p)
    name = p['name']
    if is_package_upgradable(p['identifier'], False):
        name = '*' + name
    elif is_package_upgradable(p['identifier'], True):
        name = '+' + name
    print(package_print_string.format(name, p['namespace'] if p['type'] == 'VSPlugin' else p['modulename'], installed_packages[p['identifier']] if p['identifier'] in installed_packages else '', lastest_installable['version'] if lastest_installable is not None else '', p['identifier']))

def list_installed_packages():
    print(package_print_string.format('Name', 'Namespace', 'Installed', 'Latest', 'Identifier'))
    for id in installed_packages:
        print_package_status(get_package_from_id(id, True))

def list_available_packages():
    print(package_print_string.format('Name', 'Namespace', 'Installed', 'Latest', 'Identifier'))
    for p in package_list:
        print_package_status(p)

def get_latest_installable_release(p):
    bin_name = get_bin_name(p)
    for rel in p['releases']:
        if bin_name in rel:
            return rel
    return None

def can_install(p):
    return get_latest_installable_release(p) is not None
    
def install_files(p):
    dest_path = get_install_path(p)
    bin_name = get_bin_name(p)
    install_rel = get_latest_installable_release(p)
    url = install_rel[bin_name]['url']
    data = None
    try:
        data = fetch_url_cached(url, p['name'] + ' ' + install_rel['version'])
    except:
        print('Failed to download ' + p['name'] + ' ' + install_rel['version'] + ', skipping installation and moving on')
        return (0, 1)

    single_file = None
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
            outfile.write(data)
    else:
        tffd, tfpath = tempfile.mkstemp(prefix='vsm')
        tf = open(tffd, mode='wb')
        tf.write(data)
        tf.close()
        result_cache = {}
        for install_fn in install_rel[bin_name]['files']:
            fn_props = install_rel[bin_name]['files'][install_fn]
            result = subprocess.run([cmd7zip_path, "e", "-so", tfpath, fn_props[0]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result.check_returncode()
            hash_result = check_hash(result.stdout, fn_props[1])
            if not hash_result[0]:
                raise Exception('Hash mismatch for ' + install_fn + ' got ' + hash_result[1] + ' but expected ' + hash_result[2])
            result_cache[install_fn] = result.stdout
        uninstall_files(p)
        for install_fn in install_rel[bin_name]['files']:
            os.makedirs(os.path.join(dest_path, os.path.split(install_fn)[0]), exist_ok=True)
            with open(os.path.join(dest_path, install_fn), 'wb') as outfile:
                outfile.write(result_cache[install_fn])
        os.remove(tfpath)
    installed_packages[p['identifier']] = install_rel['version']
    print('Successfully installed ' + p['name'] + ' ' + install_rel['version'])
    return (1, 0)

def install_package(name):    
    p = get_package_from_name(name)
    if can_install(p):
        inst = (0, 0, 0)
        if 'dependencies' in p:
            for dep in p['dependencies']:
                res = install_package(dep)
                inst = (inst[0], inst[1] + res[0] + res[1], inst[2] + res[2])
        if not is_package_installed(p['identifier']):
            res = install_files(p)
            inst = (inst[0] + res[0], inst[1], inst[2] + res[1])
        return inst
    else:
        print('No binaries available for ' + args.target + ' in package ' + p['name'] + ', skipping installation')
        return (0, 0, 1)

def upgrade_files(p):
    if can_install(p):
        inst = (0, 0, 0)
        if 'dependencies' in p:
            for dep in p['dependencies']:
                if not is_package_installed(dep):
                    res = install_package(dep)
                    inst = (inst[0], inst[1] + res[0] + res[1], inst[2] + res[2])
        res = install_files(p)
        return (inst[0] + res[0], inst[1], inst[2] + res[1])
    else:
        print('No binaries available for ' + args.target + ' in package ' + p['name'] + ', skipping installation')
        return (0, 0, 1)

def upgrade_package(name, force):
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

def upgrade_all_packages(force):
    inst = (0, 0, 0)
    installed_ids = list(installed_packages.keys())
    for id in installed_ids:
        if is_package_upgradable(id, force): 
            res = upgrade_files(get_package_from_id(id, True))
            inst = (inst[0] + res[0], inst[1] + res[1], inst[2] + res[2])
    return inst

def uninstall_files(p):
    dest_path = get_install_path(p)
    bin_name = get_bin_name(p)
    installed_rel = None
    if p['identifier'] in installed_packages:
        for rel in p['releases']:
            if rel['version'] == installed_packages[p['identifier']]:
                installed_rel = rel
                break
    if installed_rel is not None:
        for f in installed_rel[bin_name]['files']:
            os.remove(os.path.join(dest_path, f))

def uninstall_package(name):
    p = get_package_from_name(name)
    if is_package_installed(p['identifier']):
        if installed_packages[p['identifier']] == 'Unknown':
            print('Can\'t uninstall unknown version package: ' + p['name'])
            return (0, 0)
        else:
            uninstall_files(p)
            print('Uninstalled package: ' + p['name'] + ' ' + installed_packages[p['identifier']])
            return (1, 0)
    else:   
        print('No files installed for ' + p['name'] + ', skipping uninstall')
        return (0, 0)
    
def update_package_definition(url):
    localmtimeval = 0
    try:
        localmtimeval = os.path.getmtime(package_json_path)
    except:
        pass
    localmtime = email.utils.formatdate(localmtimeval + 10, usegmt=True)
    req_obj = urllib.request.Request(url, headers={ 'If-Modified-Since': localmtime })
    try:
        with urllib.request.urlopen(req_obj) as urlreq:
            remote_modtime = email.utils.mktime_tz(email.utils.parsedate_tz(urlreq.info()['Last-Modified']))
            data = urlreq.read()
            with zipfile.ZipFile(io.BytesIO(data), 'r') as zf:
                with zf.open('vspackages.json') as pkgfile:
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

def print_paths():
    print('Paths:')
    print('Definitions: ' + package_json_path)
    print('Binaries: ' + plugin_path)
    print('Scripts: ' + py_script_path)    

for name in args.package:
    try:
        get_package_from_name(name)
    except Exception as e:
        print(e)
        exit(1)

if args.operation == 'install':
    detect_installed_packages()
    inst = (0, 0, 0)
    for name in args.package:
        res = install_package(name)
        inst = (inst[0] + res[0], inst[1] + res[1], inst[2] + res[2])
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
    inst = (0, 0, 0)
    if args.operation == 'upgrade-all':
        inst = upgrade_all_packages(args.force)
    else:
        for name in args.package:
            res = upgrade_package(name, args.force)
            inst = (inst[0] + res[0], inst[1] + res[1], inst[2] + res[2])
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
        res = uninstall_package(name)
        uninst = (uninst[0] + res[0], uninst[1] + res[1])
    if uninst[0] == 0:
        print('No packages uninstalled')
    else:
        print('{} {} uninstalled'.format(uninst[0], 'package' if uninst[0] == 1 else 'packages'))
elif args.operation == 'installed':
    detect_installed_packages()
    list_installed_packages()
elif args.operation == 'available':
    detect_installed_packages()
    list_available_packages()
elif args.operation == 'update':
    update_package_definition('http://www.vapoursynth.com/vsrepo/vspackages.zip')
elif args.operation == 'paths':
    print_paths()
