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

import urllib.request
import json
import sys
import os
import os.path
import datetime as dt
import argparse
import hashlib
import pathlib
import subprocess
import difflib
import ftplib
import zipfile
from typing import Any, List, MutableMapping, Optional, Dict, Sequence, Tuple, TypeVar, Union

is_windows: bool = True

try:
    import winreg
except ImportError:
    is_windows = False

try:
    import tqdm  # type: ignore
except ImportError:
    pass

parser = argparse.ArgumentParser(description='Package list generator for VSRepo')
parser.add_argument('operation', choices=['compile', 'update-local', 'upload', 'create-package'])
parser.add_argument('-g', dest='git_token', help='OAuth access token for github')
parser.add_argument('-p', dest='package', help='Package to update')
parser.add_argument('-o', action='store_true', dest='overwrite', help='Overwrite existing package file')
parser.add_argument('-multi-url', dest='multi_url', help='URL of GitHub repository, that provides releases for different plugins')
parser.add_argument('-host', dest='host', nargs=1, help='FTP Host')
parser.add_argument('-user', dest='user', nargs=1, help='FTP User')
parser.add_argument('-passwd', dest='passwd', nargs=1, help='FTP Password')
parser.add_argument('-dir', dest='dir', nargs=1, help='FTP dir')
parser.add_argument('-url', dest='packageurl', help='URL of the archive from which a package is to be created')
parser.add_argument('-pname', dest='packagename', help='Filename or namespace of your package')
parser.add_argument('-script', action='store_true', dest='packagescript', help='Type of the package is script. Otherwise a package of type plugin is created')
parser.add_argument('-types', dest='packagefiletypes', nargs='+', default=['.dll', '.so', '.dylib', '.py'], help='Which file types should be included. default is .dll/.so/.dylib/.py')
parser.add_argument('-kf', dest='keepfolder', type=int, default=-1, nargs='?', help='Keep the folder structure')

args = parser.parse_args()


time_limit: int = 14  # time limit after a commit is treated as new in days | (updatemode: git-commits)

if is_windows:
    cmd7zip_path: str = '7z.exe'
    try:
        with winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\7-Zip', reserved=0, access=winreg.KEY_READ) as regkey:
            cmd7zip_path = winreg.QueryValueEx(regkey, 'Path')[0] + '7z.exe'
    except OSError:
        pass
else:
    cmd7zip_path: str = '7z'

def similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()

def get_most_similar(a: str, b: Sequence[str]) -> str:
    res: Tuple[float, str] = (0.0, '')
    for s in b:
        v = similarity(a, s)
        if v >= res[0]:
            res = (v, s)
    return res[1]

def get_git_api_url(url: str, page: int = 0) -> Optional[str]:
    if url.startswith('https://github.com/'):
        s = url.rsplit('/', 3)
        return f'https://api.github.com/repos/{s[-2]}/{s[-1]}/releases' if page == 0 else f'https://api.github.com/repos/{s[-2]}/{s[-1]}/releases?page={str(page)}'
    else:
        return None

def get_git_api_commits_url(url: str, path: Optional[str] = None, branch: Optional[str] = None) -> Optional[str]:
    sha = f"sha={branch}&" if branch else ""
    if url.startswith('https://github.com/'):
        s = url.rsplit('/', 3)
        return f'https://api.github.com/repos/{s[-2]}/{s[-1]}/commits?{sha}' + f'path={path}' if path else ''
    else:
        return None

def get_git_api_zipball_url(url: str, ref: Optional[str] = None):
    if url.startswith('https://github.com/'):
        s = url.rsplit('/', 3)
        return f'https://api.github.com/repos/{s[-2]}/{s[-1]}/zipball' + f'/{ref}' if ref else ''
    else:
        return None

def get_pypi_api_url(name: str):
    return 'https://pypi.org/pypi/' + name + '/json'

def fetch_url(url: str, desc: Optional[str] = None, token: Optional[str] = None) -> bytearray:
    req = urllib.request.Request(url, headers={'Authorization': 'token ' + token}) if token is not None else urllib.request.Request(url)
    with urllib.request.urlopen(req) as urlreq:
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

def fetch_url_to_cache(url: str, name: str, tag_name: str, desc: Optional[str] = None) -> str:
    cache_path = os.path.join('dlcache', name + '_' + tag_name, os.path.basename(url))
    if not os.path.isfile(cache_path):
        os.makedirs(os.path.split(cache_path)[0], exist_ok=True)
        with urllib.request.urlopen(urllib.request.Request(url, method='HEAD')) as urlreq:
            if not os.path.isfile(cache_path):
                data = fetch_url(url, desc)
                with open(cache_path, 'wb') as pl:
                    pl.write(data)
    return cache_path

def get_multi_url_releases(multi_url: str) -> dict:
    rel = {}
    page = 1
    while True:
        apifile = json.loads(fetch_url(get_git_api_url(multi_url, page), 'Multi-release repository', token=args.git_token))
        page += 1
        if len(apifile) < 1:
            break
        for r in apifile:
            if r['tag_name'].startswith('vsplugin/') == False:
                continue
            if r['prerelease']:
                continue
            if len(r.get('assets', [])) < 1:
                continue
            r_info = r['tag_name'].split('/')
            if r_info[2].startswith('git-'):
                r_info[2] = r_info[2].replace('git-','git:')
            rel.setdefault(r_info[1], {})
            rel[r_info[1]].setdefault(r_info[2], {})
            rel[r_info[1]][r_info[2]][r_info[3]] = {'published': r['published_at'], 'url': r['assets'][0]['browser_download_url']}
    return rel

def list_archive_files(fn: str) -> MutableMapping:
    result = subprocess.run([cmd7zip_path, "l", "-ba", fn], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result.check_returncode()
    l = {}
    lines = result.stdout.decode('utf-8').splitlines()
    for line in lines:
        t = line[53:].replace('\\', '/')
        l[t.lower()] = t
    return l

def generate_fn_candidates(fn: str, insttype: str):
    tmp_fn = fn.lower()
    fn_guesses = [
        tmp_fn,
        tmp_fn.replace('x64', 'win64'),
        tmp_fn.replace('win64', 'x64'),
        tmp_fn.replace('x86', 'win32'),
        tmp_fn.replace('win32', 'x86')]
    if insttype == 'win32':
        return list(filter(lambda x: (x.find('64') == -1) and (x.find('x64') == -1) , fn_guesses))
    elif insttype == 'win64':
        return list(filter(lambda x: (x.find('32') == -1) and (x.find('x86') == -1) , fn_guesses))
    else:
        return fn_guesses

def decompress_and_hash(archivefn: str, fn: str, insttype: str) -> Tuple[Dict, str]:
    existing_files = list_archive_files(archivefn)
    for fn_guess in generate_fn_candidates(fn, insttype):
        if fn_guess in existing_files:
            result = subprocess.run([cmd7zip_path, "e", "-so", archivefn, fn_guess], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result.check_returncode()
            return (existing_files[fn_guess], hashlib.sha256(result.stdout).hexdigest())
    base_dirs = []
    for f in existing_files:
        bn = f.split('/')[0]
        if bn not in base_dirs:
            base_dirs.append(bn)
    if len(base_dirs) == 1:
        sfn = fn.split('/')
        if len(sfn) > 1:
            sfn[0] = base_dirs[0]
            mfn = '/'.join(sfn)
            for fn_guess in generate_fn_candidates(mfn, insttype):
                if fn_guess in existing_files:
                    result = subprocess.run([cmd7zip_path, "e", "-so", archivefn, fn_guess], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    result.check_returncode()
                    return (existing_files[fn_guess], hashlib.sha256(result.stdout).hexdigest())
    raise Exception('No file match found')

def get_installable_files_list(temp_fn: str) -> dict:
    ret = {}
    listzip = list_archive_files(temp_fn)
    files_to_hash: List[str] = []
    for f in listzip.values():
        if pathlib.Path(f).suffix: # simple folder filter
            if "*" in args.packagefiletypes:
                files_to_hash.append(str(f))
            else:
                if pathlib.Path(f).suffix in args.packagefiletypes:
                    files_to_hash.append(str(f))
    for fname in files_to_hash:
        fullpath, hash, arch = decompress_hash_simple(temp_fn, fname)
        ret[fname] = [ fullpath, hash ]
    return ret

def get_latest_installable_release(p: MutableMapping, bin_name: str) -> Optional[MutableMapping]:
    for rel in p['releases']:
        if bin_name in rel:
            return rel
    return None

def get_python_package_name(pkg: MutableMapping) -> str:
    return pkg.get("wheelname", pkg.get("name")).replace(".", "_").replace(" ", "_")

def write_new_releses(name: str, pfile: MutableMapping, new_rels: MutableMapping, rel_order: List) -> int:
    if bool(new_rels):
        for rel in pfile['releases']:
            new_rels[rel['version']] = rel
        rel_list = []
        for rel_ver in rel_order:
            rel_list.append(new_rels[rel_ver])
        pfile['releases'] = rel_list
        pfile['releases'].sort(key=lambda r: r['published'], reverse=True)

        fnext = '.json' if args.overwrite else '.new.json'
        with open('local/' + name + fnext, 'w', encoding='utf-8') as pl:
            json.dump(fp=pl, obj=pfile, ensure_ascii=False, indent='\t')
        print('Release file updated')
        return 1
    else:
        print('Release file already up to date')
        return 0

def update_package(name: str) -> int:
    with open('local/' + name + '.json', 'r', encoding='utf-8') as ml:
        pfile: Dict = json.load(ml)

    existing_rel_list = []
    for rel in pfile['releases']:
        existing_rel_list.append(rel['version'])
    rel_order = list(existing_rel_list)

    use_pypi = (pfile['type'] == 'PyWheel')
    if ('source' in pfile) and (pfile['source'] != 'pypi'):
        use_pypi = False

    if pfile['type'] == 'PyWheel':
        if use_pypi:
            new_rels = {}
            apifile: Dict = json.loads(fetch_url(get_pypi_api_url(get_python_package_name(pfile)), pfile['name']))
            for version in apifile['releases']:
                for rel in apifile['releases'][version]:
                    if rel['yanked'] or rel['packagetype'] != 'bdist_wheel':
                        continue
                    new_rel_entry = { 'version': version, 'published': rel['upload_time_iso_8601'], 'wheel': { 'url': rel['url'], 'hash': rel['digests']['sha256'] } }
                    new_rels[version] = new_rel_entry
                    if version not in rel_order:
                        rel_order.insert(0, version)
            return write_new_releses(name, pfile, new_rels, rel_order)
        else:
            print('PyWheel can only be scanned from pypi')
            return -1
    elif 'github' in pfile:
        new_rels = {}
        is_plugin = (pfile['type'] == 'VSPlugin')
        is_pyscript = (pfile['type'] == 'PyScript')
        is_pywheel = (pfile['type'] == 'PyWheel')

        if (is_pyscript and ('updatemode' in pfile) and pfile['updatemode'] == 'git-commits'):
            apifile = {} # no releases dummy
            new_rel_entry = { 'version': "", 'published': "" }
            try:
                latest_rel = get_latest_installable_release(pfile, 'script')
                fpath: str = os.path.basename(list(latest_rel['script']['files'].values())[0][0])  # type: ignore

                git_commits = json.loads(fetch_url(get_git_api_commits_url(url = pfile['github'], path = fpath, branch = pfile['gitbranch'] if 'gitbranch' in pfile else None) or "", pfile['name']))

                git_hash = git_commits[0]['sha']
                git_hash_short = git_hash[:7]

                try:
                    #diff_date_commit = (dt.datetime.now() - dt.datetime.strptime(git_commits[0]['commit']['committer']['date'], "%Y-%m-%dT%H:%M:%SZ")).days
                    diff_date_package = (dt.datetime.now() - dt.datetime.strptime(latest_rel['published'], "%Y-%m-%dT%H:%M:%SZ")).days  # type: ignore
                except:
                    print("Parsing published date failed")

                if(diff_date_package > time_limit):
                    if not any(('git:' + git_hash_short) in ver for ver in rel_order):
                        rel_order.insert(0, 'git:' + git_hash_short)
                        print('git:' + git_hash_short + ' (new)')
                    new_rel_entry = { 'version': 'git:' + git_hash_short, 'published': git_commits[0]['commit']['committer']['date'] }

                    new_url = get_git_api_zipball_url(pfile['github'], git_hash)
                    temp_fn = fetch_url_to_cache(new_url, name,  git_hash_short, pfile['name'] + ' ' + git_hash_short + ' script')
                    new_rel_entry['script'] = { 'url': new_url, 'files': {} }
                    for fn in latest_rel['script']['files']:  # type: ignore
                        new_fn, digest = decompress_and_hash(temp_fn, latest_rel['script']['files'][fn][0], 'script')  # type: ignore
                        new_rel_entry['script']['files'][fn] = [new_fn, digest]

                        new_rels[new_rel_entry['version']] = new_rel_entry
                else:
                    print(f'skipping git commit(s) - this and the last commit must be at least {time_limit} days apart')
                    

            except:
                new_rel_entry.pop('script', None)
                print('No script found')
        else:
            apifile = json.loads(fetch_url(get_git_api_url(pfile['github']) or "", pfile['name'], token=args.git_token))

        for rel in apifile:
            if rel['prerelease']:
                continue
            if rel['tag_name'] in pfile.get('ignore', []):
                continue
            if rel['tag_name'] not in rel_order:
                rel_order.insert(0, rel['tag_name'])
            if rel['tag_name'] not in existing_rel_list:
                print(rel['tag_name'] + ' (new)')
                zipball = rel['zipball_url']
                dl_files = []
                for asset in rel['assets']:
                    dl_files.append(asset['browser_download_url'])

                #ugly copypaste here because I'm lazy
                if is_plugin:
                    new_rel_entry = { 'version': rel['tag_name'], 'published': rel['published_at'] }
                    try:
                        latest_rel = get_latest_installable_release(pfile, 'win32')
                        if latest_rel is not None:
                            new_url = get_most_similar(latest_rel['win32']['url'], dl_files)
                            temp_fn = fetch_url_to_cache(new_url, name, rel['tag_name'], pfile['name'] + ' ' +rel['tag_name'] + ' win32')
                            new_rel_entry['win32'] = { 'url': new_url, 'files': {}}
                            for fn in latest_rel['win32']['files']:
                                new_fn, digest = decompress_and_hash(temp_fn, latest_rel['win32']['files'][fn][0], 'win32')
                                new_rel_entry['win32']['files'][fn] = [new_fn, digest]
                    except:
                        new_rel_entry.pop('win32', None)
                        print('No win32 binary found')
                    try:
                        latest_rel = get_latest_installable_release(pfile, 'win64')
                        if latest_rel is not None:
                            new_url = get_most_similar(latest_rel['win64']['url'], dl_files)
                            temp_fn = fetch_url_to_cache(new_url, name, rel['tag_name'], pfile['name'] + ' ' +rel['tag_name'] + ' win64')
                            new_rel_entry['win64'] = { 'url': new_url, 'files': {} }
                            for fn in latest_rel['win64']['files']:
                                new_fn, digest = decompress_and_hash(temp_fn, latest_rel['win64']['files'][fn][0], 'win64')
                                new_rel_entry['win64']['files'][fn] = [new_fn, digest]
                    except:
                        new_rel_entry.pop('win64', None)
                        print('No win64 binary found')
                else:
                    new_rel_entry = { 'version': rel['tag_name'], 'published': rel['published_at'] }
                    try:
                        latest_rel = get_latest_installable_release(pfile, 'script')
                        new_url = None
                        if ('/archive/' in latest_rel['script']['url']) or ('/zipball/' in latest_rel['script']['url']):  # type: ignore
                            new_url = zipball
                        else:
                            new_url = get_most_similar(latest_rel['script']['url'], dl_files)  # type: ignore
                        temp_fn = fetch_url_to_cache(new_url, name, rel['tag_name'], pfile['name'] + ' ' +rel['tag_name'] + ' script')
                        new_rel_entry['script'] = { 'url': new_url, 'files': {} }
                        for fn in latest_rel['script']['files']:  # type: ignore
                            new_fn, digest = decompress_and_hash(temp_fn, latest_rel['script']['files'][fn][0], 'script')  # type: ignore
                            new_rel_entry['script']['files'][fn] = [new_fn, digest]
                    except:
                        new_rel_entry.pop('script', None)
                        print('No script found')
                new_rels[new_rel_entry['version']] = new_rel_entry
        if is_plugin and multi_rel.get(pfile['identifier'], None) != None:
            for version, targets in multi_rel[pfile['identifier']].items():
                if version in existing_rel_list:
                    for rel in pfile['releases']:
                        if rel['version'] == version:
                            for target, t_data in targets.items():
                                if rel.get(target, None) == None:
                                    temp_fn = fetch_url_to_cache(t_data['url'], name, rel['version'], pfile['name'] + ' ' + rel['version'] + ' ' + target)
                                    rel[target] = { 'url': t_data['url'], 'files': get_installable_files_list(temp_fn)}
                                    new_rels[rel['version']] = rel
                            break
                else:
                    if version not in new_rels.keys():
                        print(version + ' (new from multi-url)')
                        new_rels[version] = { 'version': version }
                        if version not in rel_order:
                            rel_order.insert(0, version)
                    for target, t_data in targets.items():
                        if new_rels[version].get('published', None) == None:
                            new_rels[version]['published'] = t_data['published']
                        if new_rels[version].get(target, None) == None:
                            temp_fn = fetch_url_to_cache(t_data['url'], name, version, pfile['name'] + ' ' + version + ' ' + target)
                            new_rels[version][target] = { 'url': t_data['url'], 'files': get_installable_files_list(temp_fn)}
        return write_new_releses(name, pfile, new_rels, rel_order)
    else:
        print(f'Only github and pypi projects supported, {name} not scanned')
        return -1

def verify_package(pfile: MutableMapping, existing_identifiers: Sequence[str]) -> None:
    name: str = pfile['name']
    for key in pfile.keys():
        if key not in ('name', 'type', 'device', 'api', 'description', 'website', 'category', 'identifier', 'modulename', 'wheelname', 'namespace', 'github', 'doom9', 'dependencies', 'ignore', 'releases', 'updatemode', 'gitbranch'):
            raise Exception(f'Unknown key: {key} in {name}')
    if pfile['type'] not in ('VSPlugin', 'PyScript', 'PyWheel'):
        raise Exception('Invalid type in ' + name)
    if (pfile['type'] == 'VSPlugin') and ('modulename' in pfile):
        raise Exception('VSPlugin can\'t have modulenames: ' + name)
    if (pfile['type'] == 'VSPlugin') and (('modulename' in pfile) or ('namespace' not in pfile)):
        raise Exception('VSPlugin must have namespace, not modulename: ' + name)
    if (pfile['type'] == 'PyScript' or pfile['type'] == 'PyWheel') and (('namespace' in pfile) or ('modulename' not in pfile)):
        raise Exception('PyScript must have modulename, not namespace: ' + name)
    if ((pfile['type'] == 'PyScript' or pfile['type'] == 'VSPlugin') and 'wheelname' in pfile):
        raise Exception('Only PyWheel type can have wheelname: ' + name)
    allowed_categories = ('Scripts', 'Plugin Dependency', 'Resizing and Format Conversion', 'Other', 'Dot Crawl and Rainbows', 'Sharpening', 'Denoising', 'Deinterlacing', 'Inverse Telecine', 'Source/Output', 'Subtitles', 'Color/Levels')
    if pfile['category'] not in allowed_categories:
        raise Exception('Not allowed catogry in ' + name + ': ' + pfile['category'] + ' not in ' + repr(allowed_categories))
    if 'updatemode' in pfile:
        if pfile['updatemode'] not in ('git-commits'):
            raise Exception('Invalid updatemode in ' + name)
    if 'api' in pfile:
        if pfile['api'] not in (3, 4):
            raise Exception('Invalid api version in ' + name)
    if 'dependencies' in pfile:
        for dep in pfile['dependencies']:
            if dep not in existing_identifiers:
                raise Exception('Referenced unknown identifier ' + dep + ' in ' + name)
    if 'device' in pfile:
        for dev in pfile['device']:
            if dev not in ("cpu", "gpu", "cuda", "opencl", "vulkan", "hip", "sycl"):
                raise Exception('Invalid device in ' + name)

def compile_packages() -> None:
    combined = []
    existing_identifiers = []
    for f in os.scandir('local'):
        if f.is_file() and f.path.endswith('.json'):
            with open(f.path, 'r', encoding='utf-8') as ml:
                pfile: Dict = json.load(ml)
                if pfile['identifier'] in existing_identifiers:
                    raise Exception('Duplicate identifier: ' + pfile['identifier'])
                existing_identifiers.append(pfile['identifier'])

    for f in os.scandir('local'):
        if f.is_file() and f.path.endswith('.json') and not f.path.endswith('.new.json'):
            with open(f.path, 'r', encoding='utf-8') as ml:
                print('Combining: ' + f.path)
                pfile = json.load(ml)
                verify_package(pfile, existing_identifiers)
                pfile.pop('ignore', None)
                combined.append(pfile)

    data = json.dumps(obj={ 'file-format': 3, 'packages': combined}, ensure_ascii=False, indent=2)

    try:
        os.remove('vspackages3.zip')
    except:
        pass

    with zipfile.ZipFile('vspackages3.zip', mode='w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zf.writestr('vspackages3.json', data)


def getBinaryArch(bin: bytes) -> Optional[int]:
    if b"PE\x00\x00d\x86" in bin:     # hex: 50 45 00 00 64 86 | PE..d†
        return 64
    if b"PE\x00\x00L" in bin:         # hex: 50 45 00 00 4c     | PE..L
        return 32
    return None

def decompress_hash_simple(archive: str, file: str) -> Tuple[str, str, Optional[int]]:
    result = subprocess.run([cmd7zip_path, "e", "-so", archive, file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result.check_returncode()
    return (file, hashlib.sha256(result.stdout).hexdigest(), getBinaryArch(result.stdout))

def extract_git_repo(url: str) -> Optional[str]:
    if url.startswith('https://github.com/'):
        return '/'.join(url.split('/', 5)[:-1])
    else:
        return None

def keep_folder_structure(path: str, level: int = 0) -> str:
    folder = path.split('/', level)
    return folder[-1]

def blank_package(name: str = "", is_script: bool = False, is_wheel: bool = False, url: str = "") -> MutableMapping:
    giturl = extract_git_repo(url)
    p = {
            'name': '',
            'type': 'PyScript' if is_script else ('PyWheel' if is_wheel else 'VSPlugin'),
            'category': '',
            'description': '',
            'doom9': '',
            'website': '',
            'github': giturl if giturl else '',
            'identifier': name if is_script or is_wheel else '',
            'modulename' if is_script or is_wheel else 'namespace': name,
            'wheelname': name,
            'releases': ''
        }
    if not is_wheel:
        del p['wheelname']
    return p

if args.operation == 'compile':
    compile_packages()
    print('Packages successfully compiled')
elif args.operation == 'update-local':
    multi_rel = get_multi_url_releases(args.multi_url) if args.multi_url != None else {}
    if args.package is None:
        num_skipped = 0
        num_nochange = 0
        num_updated = 0
        for f in os.scandir('local'):
            if f.is_file() and f.path.endswith('.json'):
                result = update_package(os.path.splitext(os.path.basename(f))[0])
                if result == -1:
                    num_skipped = num_skipped + 1
                elif result == 1:
                    num_updated = num_updated + 1
                elif result == 0:
                    num_nochange = num_nochange + 1
        print(f'Summary:\nUpdated:   {num_updated}\nNo change: {num_nochange} \nSkipped:   {num_skipped}\n')
    else:
        update_package(args.package)
elif args.operation == 'create-package':

    if not args.packageurl:
        print('-url parameter is missing')
        sys.exit(1)
    if not args.packagename:
        print('-pname parameter is missing')
        sys.exit(1)

    url = args.packageurl
    is_wheel = pathlib.Path(url).suffix.lower() == '.whl'

    print("fetching remote url")
    dlfile = fetch_url_to_cache(url, "package", "creator", "")

    print("creating package")
    new_rel_entry: MutableMapping[str, Any] = { 'version': 'create-package', 'published': '' }


    if is_wheel:
        new_rel_entry['wheel'] = { 'url': url }
        new_rel_entry['wheel']['hash'] = hashlib.sha256(open(dlfile,'rb').read()).hexdigest()

    else: # is plugin or script
        listzip = list_archive_files(dlfile)
        files_to_hash: List[str] = []
        for f in listzip.values():
            if pathlib.Path(f).suffix: # simple folder filter
                if "*" in args.packagefiletypes:
                    files_to_hash.append(str(f))
                else:
                    if pathlib.Path(f).suffix in args.packagefiletypes:
                        files_to_hash.append(str(f))

        files_to_hash = sorted(files_to_hash)


        print("\n\nFound the following dlls:")
        for fname in files_to_hash:
            fullpath, hash, arch = decompress_hash_simple(dlfile, fname)
            if arch == 32:
                print('win32:', fullpath, hash)
            if arch == 64:
                print('win64:', fullpath, hash)
        print("\n\n")

        if not args.packagescript: # is plugin
            new_rel_entry['win32'] = { 'url': url, 'files': {} }
            new_rel_entry['win64'] = { 'url': url, 'files': {} }
            for fname in files_to_hash:
                fullpath, hash, arch = decompress_hash_simple(dlfile, fname)
                file = keep_folder_structure(fullpath, args.keepfolder) if args.keepfolder >= 0 else os.path.basename(fullpath)
                if arch == 32:
                    new_rel_entry['win32']['files'][file] = [fullpath, hash]
                if arch == 64:
                    new_rel_entry['win64']['files'][file] = [fullpath, hash]
                if arch == None:
                    new_rel_entry['win32']['files'][file] = [fullpath, hash]
                    new_rel_entry['win64']['files'][file] = [fullpath, hash]

            # remove 32/64 entry if no files are present
            if not new_rel_entry['win32']['files']:
                new_rel_entry.pop('win32', None)
            if not new_rel_entry['win64']['files']:
                new_rel_entry.pop('win64', None)

        else: # is script
            new_rel_entry['script'] = { 'url': url, 'files': {} }
            for fname in files_to_hash:
                fullpath, hash, arch = decompress_hash_simple(dlfile, fname)
                file = keep_folder_structure(fullpath, args.keepfolder) if args.keepfolder >= 0 else os.path.basename(fullpath)
                new_rel_entry['script']['files'][file] = [fullpath, hash]

    if not args.packagescript:
        if is_wheel:
            final_package = blank_package(name = args.packagename, url = url, is_wheel = True)
        else:
            final_package = blank_package(name = args.packagename, url = url)
    else:
        final_package = blank_package(name = args.packagename, url = url, is_script = True)
    final_package['releases'] = [ new_rel_entry ]


    print(json.dumps(final_package, indent=4))
    if not os.path.exists('local/' + args.packagename + '.json'):
        with open('local/' + args.packagename + '.json', 'x', encoding='utf-8') as pl:
            json.dump(fp=pl, obj=final_package, ensure_ascii=False, indent='\t')

        print("package created")

        if extract_git_repo(url) and not is_wheel:
            print("Is hosted on GitHub - auto updating package")
            args.overwrite = True
            update_package(args.packagename)

        if is_wheel and url.startswith('https://files.pythonhosted.org'):
            print("Auto updating wheel package")
            args.overwrite = True
            update_package(args.packagename)
    else:
        print("package file '{}'.json already exists. Skipping writing file.".format(args.packagename))


elif args.operation == 'upload':
    compile_packages()
    print('Packages successfully compiled')
    with open('vspackages3.zip', 'rb') as bpl:
        with ftplib.FTP_TLS(host=args.host[0], user=args.user[0], passwd=args.passwd[0]) as ftp:
            if args.dir is not None:
                ftp.cwd(args.dir[0])
            try:
                ftp.delete('vspackages3.zip')
            except:
                print('Failed to delete vspackages3.zip')
            ftp.storbinary('STOR vspackages3.zip', bpl)
    print('Upload done')

def noop():
    pass
