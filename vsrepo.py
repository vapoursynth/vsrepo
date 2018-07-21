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
import platform
import io
import site
import os
import os.path
import subprocess
import tempfile
import argparse
import winreg

if platform.system() != 'Windows':
    raise Exception('Windows required')

def is_sitepackage_install_portable():
    try:
        import vapoursynth
    except ImportError:
        return False
    else:
        return os.path.exists(os.path.join(os.path.dirname(vapoursynth.__file__), 'portable.vs'))
    

is_64bits = sys.maxsize > 2**32

parser = argparse.ArgumentParser(description='A simple VapourSynth package manager')
parser.add_argument('operation', choices=['install', 'upgrade', 'installed', 'available'])
parser.add_argument('package', nargs='*', help='identifier, namespace or module to install or upgrade')
parser.add_argument('-f', action='store_true', dest='force', help='force upgrade for packages where the current version is unknown')
parser.add_argument('-t', choices=['win32', 'win64'], default='win64' if is_64bits else 'win32', dest='target', help='binaries to install, defaults to python\'s architecture')
parser.add_argument('-p', action='store_true', dest='portable', help='portable mode')
args = parser.parse_args()
is_64bits = (args.target == 'win64')

if ((args.operation == 'install') or (args.operation == 'upgrade')) == ((args.package is None) or len(args.package) == 0):
    raise Exception('Package argument required for install and upgrade operations')

py_script_path = '.\\' if args.portable else site.getusersitepackages() + '\\'

if args.portable:
    plugin32_path = 'vapoursynth32\\plugins\\'
    plugin64_path = 'vapoursynth64\\plugins\\'
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
	
os.makedirs(py_script_path, exist_ok=True)
os.makedirs(plugin_path, exist_ok=True)


cmd7zip_path = '7z.exe'
try:
    with winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\7-Zip', reserved=0, access=winreg.KEY_READ) as regkey:
        cmd7zip_path = winreg.QueryValueEx(regkey, 'Path')[0] + '7z.exe'
except:
    pass

installed_packages = {}
download_cache = {}

def fetch_url(url):
    data = download_cache.get(url, None)
    if data is None:
        print('Fetching: ' + url)
        urlreq = urllib.request.urlopen(url)
        data = urlreq.read()
        download_cache[url] = data
    return data

package_print_string = "{:25s} {:15s} {:11s} {:11s} {:s}"

package_list = None
with open('vspackages.json', 'r', encoding='utf-8') as pl:
    package_list = json.load(pl)

def get_bin_name(p):
    if p['type'] == 'PyScript':
        return 'script'
    elif p['type'] == 'Plugin':
        if is_64bits:
            return 'win64'
        else:
            return 'win32'
    else:
        raise Exception('Unknown install type')

def get_install_path(p):
    if p['type'] == 'PyScript':
        return py_script_path
    elif p['type'] == 'Plugin':
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
    for p in package_list:
        dest_path = get_install_path(p)
        for v in p['releases']:
            matched = True
            exists = True
            bin_name = get_bin_name(p)
            if bin_name in v:
                for f in v[bin_name]['hash']:
                    try:
                        with open(os.path.join(dest_path, f), 'rb') as fh:
                            digest = hashlib.sha1(fh.read()).hexdigest()
                            ref_digest = v[bin_name]['hash'][f]
                            if digest != ref_digest:
                                matched = False
                    except FileNotFoundError:
                        exists = False
                        matched = False
                if matched:
                    installed_packages[p['identifier']] = v['version']
                    break
                elif exists:
                    installed_packages[p['identifier']] = 'Unknown'

def print_package_status(p):
    lastest_installable = get_latest_installable_release(p)
    name = p['name']
    if is_package_upgradable(p['identifier'], False):
        name = '*' + name
    elif is_package_upgradable(p['identifier'], True):
        name = '+' + name
    print(package_print_string.format(name, p['namespace'] if p['type'] == 'Plugin' else p['modulename'], installed_packages[p['identifier']] if p['identifier'] in installed_packages else '', lastest_installable['version'] if lastest_installable is not None else '', p['identifier']))

def list_installed_packages():
    print(package_print_string.format('Name', 'Namespace', 'Installed', 'Latest', 'Identifier'))
    installed_ids = installed_packages.keys()
    for id in installed_ids:
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
    data = fetch_url(url)
    if url.endswith('.7z') or url.endswith('.zip'):
        tffd, tfpath = tempfile.mkstemp(prefix='vsm')
        tf = open(tffd, mode='wb')
        tf.write(data)
        tf.close()
        for filename in install_rel[bin_name]['files']:
            result = subprocess.run([cmd7zip_path, "e", "-so", tfpath, filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result.check_returncode()
            stripped_fn = filename.rsplit('/', 2)[-1]
            digest = hashlib.sha1(result.stdout).hexdigest()
            ref_digest = install_rel[bin_name]['hash'][stripped_fn]
            if digest != ref_digest:
                raise Exception('Hash mismatch got ' + digest + ' but expected ' + ref_digest)
            with open(os.path.join(dest_path, stripped_fn), 'wb') as outfile:
                outfile.write(result.stdout)
        os.remove(tfpath)
    elif len(install_rel[bin_name]['files']) == 1:
        filename = install_rel[bin_name]['files'][0]
        stripped_fn = filename.rsplit('/', 2)[-1]
        digest = hashlib.sha1(data).hexdigest()
        ref_digest = install_rel[bin_name]['hash'][stripped_fn]
        if digest != ref_digest:
            raise Exception('Hash mismatch got ' + digest + ' but expected ' + ref_digest)
        with open(os.path.join(dest_path, stripped_fn), 'wb') as outfile:
            outfile.write(data)
    else:
        raise Exception('Unsupported compression type')
    installed_packages[p['identifier']] = install_rel['version']
    print('Successfully installed ' + p['name'] + ' ' + install_rel['version'])

def install_package(name):    
    p = get_package_from_name(name)
    if can_install(p):
        inst = 0
        if 'dependencies' in p:
            for dep in p['dependencies']:
                res = install_package(dep)
                inst = inst + res[0] + res[1]
        if not is_package_installed(p['identifier']):
            install_files(p)
            return (1, inst)
        return (0, inst)
    else:   
        print('No binaries available for ' + args.target + ' in package ' + p['name'] + ', skipping installation')
        return (0, 0)

def upgrade_files(p):
    if can_install(p):
        inst = 0
        if 'dependencies' in p:
            for dep in p['dependencies']:
                if not is_package_installed(dep):
                    res = install_package(dep)
                    inst = inst + res[0] + res[1]
        install_files(p)
        return(1, inst)
    else:
        print('No binaries available for ' + args.target + ' in package ' + p['name'] + ', skipping installation')
        return (0, 0)

def upgrade_package(name, force):
    inst = (0, 0)
    if name == 'all':
        installed_ids = installed_packages.keys()
        for id in installed_ids:
            if is_package_upgradable(id, force): 
                res = upgrade_files(get_package_from_id(id, True))
                inst = (inst[0] + res[0], inst[1] + res[1])
    else:
        p = get_package_from_name(name)
        if is_package_upgradable(p['identifier'], force):
            inst = upgrade_files(p)
        elif not is_package_upgradable(p['identifier'], True):
            print('Package ' + p['name'] + ' not upgradaded, latest version installed')
        else:
            print('Package ' + p['name'] + ' not upgraded, unknown version must use -f to force replacement')
    return inst

detect_installed_packages()

if args.operation == 'install':
    inst = (0, 0)
    for name in args.package:
        res = install_package(name)
        inst = (inst[0] + res[0], inst[1] + res[1])
    if (inst[0] == 0) and (inst[1] == 0):
        print('All packages and dependencies are already installed')
    elif (inst[0] > 0) and (inst[1] == 0):
        print('{} {} installed'.format(inst[0], 'package' if inst[0] == 1 else 'packages'))
    elif (inst[0] == 0) and (inst[1] > 0):
        print('{} missing {} installed'.format(inst[1], 'dependency' if inst[1] == 1 else 'dependencies'))
    else:
        print('{} {} and {} additional {} installed'.format(inst[0], 'package' if inst[0] == 1 else 'packages', inst[1], 'dependency' if inst[1] == 1 else 'dependencies'))
elif args.operation == 'upgrade':
    inst = (0, 0)
    for name in args.package:
        res = upgrade_package(name, args.force)
        inst = (inst[0] + res[0], inst[1] + res[1])
    if (inst[0] == 0) and (inst[1] == 0):
        print('All packages are already up to date')
    elif (inst[0] > 0) and (inst[1] == 0):
        print('{} {} upgraded'.format(inst[0], 'package' if inst[0] == 1 else 'packages'))
    elif (inst[0] == 0) and (inst[1] > 0):
        print('{} missing {} installed'.format(inst[1], 'dependency' if inst[1] == 1 else 'dependencies'))
    else:
        print('{} {} upgraded and {} additional {} installed'.format(inst[0], 'package' if inst[0] == 1 else 'packages', inst[1], 'dependency' if inst[1] == 1 else 'dependencies'))
elif args.operation == 'installed':
    list_installed_packages()
elif args.operation == 'available':
    list_available_packages()

