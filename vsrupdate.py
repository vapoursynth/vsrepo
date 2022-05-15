#    MIT License
#
#    Copyright (c) 2018-2020 Fredrik Mellbin
#
#    Permission is hereby granted, free of charge, to any person obtaining a copy
#    of this software and associated documentation files (the "Software"), to deal
#    in the Software without restriction, including without limitation the rights
#    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#    copies of the Software, and to permit persons to whom the Software is
#    furnished to do so, subject to the following conditions:
#
#    The above copyright notice and this permission notice shall be included in all
#    copies or substantial portions of the Software.
#
#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#    SOFTWARE.

import argparse
import difflib
import ftplib
import hashlib
import json
import os
import subprocess
import sys
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, MutableMapping, MutableSequence, Optional, Sequence, Set, Tuple
from urllib.error import URLError, HTTPError

try:
    import winreg
except ImportError:
    print(f'{__file__} is only supported on Windows.')
    sys.exit(1)

try:
    import tqdm  # type: ignore
except ImportError:
    pass

parser = argparse.ArgumentParser(description='Package list generator for VSRepo')
parser.add_argument('operation', choices=['compile', 'update-local', 'upload', 'create-package'])
parser.add_argument('-g', dest='git_token', help='OAuth access token for github')
parser.add_argument('-p', dest='package', help='Package to update')
parser.add_argument('-o', action='store_true', dest='overwrite', help='Overwrite existing package file')
parser.add_argument('-host', dest='host', nargs=1, help='FTP Host')
parser.add_argument('-user', dest='user', nargs=1, help='FTP User')
parser.add_argument('-passwd', dest='passwd', nargs=1, help='FTP Password')
parser.add_argument('-dir', dest='dir', nargs=1, help='FTP dir')
parser.add_argument('-url', dest='packageurl', help='URL of the archive from which a package is to be created')
parser.add_argument('-pname', dest='packagename', help='Filename or namespace of your package')
parser.add_argument('-outpath', dest='outpath', required=False, default=None,
                    help='Directory for package definitions, default is the `local` folder in the vsrepo directory.'
                    'Appends `local` to the given path if the last component is not `local`.')
parser.add_argument('-script', action='store_true', dest='packagescript',
                    help='Type of the package is script. Otherwise a package of type plugin is created')
parser.add_argument('-types', dest='packagefiletypes', nargs='+', default=['.dll', '.py'],
                    help='Which file types should be included. default is .dll')
parser.add_argument('-kf', dest='keepfolder', type=int, default=-1, nargs='?', help='Keep the folder structure')

args = parser.parse_args()

localpath = Path(args.outpath) if args.outpath is not None else Path(__file__).parent
if not localpath.name == 'local':
    localpath = localpath.joinpath('local')
if not localpath.exists():
    localpath.mkdir()
    print(f'outputting all packages to {localpath}')

time_limit: int = 14  # time limit after a commit is treated as new in days | (updatemode: git-commits)
cmd7zip_path: str = '7z.exe'

try:
    with winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\7-Zip', reserved=0, access=winreg.KEY_READ) as regkey:
        cmd7zip_path = winreg.QueryValueEx(regkey, 'Path')[0] + '7z.exe'
except OSError:
    pass


def similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()


def get_most_similar(a: str, b: Sequence[str]) -> str:
    res: Tuple[float, str] = (0.0, '')
    for s in b:
        v = similarity(a, s)
        if v >= res[0]:
            res = (v, s)
    return res[1]


def get_git_api_url(url: str) -> Optional[str]:
    if url.startswith('https://github.com/'):
        s = url.rsplit('/', 3)
        return f'https://api.github.com/repos/{s[-2]}/{s[-1]}/releases'
    else:
        return None


def get_git_api_commits_url(url: str, path: Optional[str] = None, branch: Optional[str] = None) -> Optional[str]:
    sha = f'sha={branch}&' if branch else ''
    if url.startswith('https://github.com/'):
        s = url.rsplit('/', 3)
        return f'https://api.github.com/repos/{s[-2]}/{s[-1]}/commits?{sha}' + (f'path={path}' if path else '')
    else:
        return None


def get_git_api_zipball_url(url: str, ref: Optional[str] = None) -> Optional[str]:
    if url.startswith('https://github.com/'):
        s = url.rsplit('/', 3)
        return f'https://api.github.com/repos/{s[-2]}/{s[-1]}/zipball' + (f'/{ref}' if ref else '')
    else:
        return None


def get_pypi_api_url(name: str):
    return f'https://pypi.org/pypi/{name}/json'


def fetch_url(url: str, desc: Optional[str] = None, token: Optional[str] = None) -> bytearray:
    headers = {'Authorization': 'token ' + token} if token is not None else None
    req = urllib.request.Request(url, headers=headers) if headers else urllib.request.Request(url)
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


def fetch_url_to_cache(url: str, name: str, tag_name: str, desc: Optional[str] = None) -> Path:
    cache_path = Path('dlcache').joinpath(f'{name}_{tag_name}', os.path.basename(url))
    if not cache_path.parent.exists():
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        if not cache_path.exists():
            data = fetch_url(url, desc)
            with open(cache_path, 'wb') as pl:
                pl.write(data)
    return cache_path


def list_archive_files(fn: Path) -> MutableMapping:
    result = subprocess.run([cmd7zip_path, 'l', '-ba', str(fn)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result.check_returncode()
    list_arch = {}
    lines = result.stdout.decode('utf-8').splitlines()
    for line in lines:
        t = line[53:].replace('\\', '/')
        list_arch[t.lower()] = t
    return list_arch


def generate_fn_candidates(fn: str, insttype: str) -> List[str]:
    tmp_fn = fn.lower()
    fn_guesses = [tmp_fn,
                  tmp_fn.replace('x64', 'win64'),
                  tmp_fn.replace('win64', 'x64'),
                  tmp_fn.replace('x86', 'win32'),
                  tmp_fn.replace('win32', 'x86')]
    if insttype == 'win32':
        return [x for x in fn_guesses if '64' not in x]
    elif insttype == 'win64':
        return [x for x in fn_guesses if '64' in x]
    else:
        return fn_guesses


def decompress_and_hash(archivefn: Path, fn: str, insttype: str) -> Tuple[MutableMapping, str]:
    existing_files = list_archive_files(archivefn)
    for fn_guess in generate_fn_candidates(fn, insttype):
        if fn_guess in existing_files:
            result = subprocess.run([cmd7zip_path, 'e', '-so', str(archivefn), fn_guess],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result.check_returncode()
            return (existing_files[fn_guess], hashlib.sha256(result.stdout).hexdigest())
    base_dirs: Set[str] = set()
    for f in existing_files:
        bn = f.split('/')[0]
        base_dirs.add(bn)
    if len(base_dirs) == 1:
        sfn = fn.split('/')
        if len(sfn) > 1:
            sfn[0] = base_dirs.pop()
            mfn = '/'.join(sfn)
            for fn_guess in generate_fn_candidates(mfn, insttype):
                if fn_guess in existing_files:
                    result = subprocess.run([cmd7zip_path, 'e', '-so', str(archivefn), fn_guess],
                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    result.check_returncode()
                    return (existing_files[fn_guess], hashlib.sha256(result.stdout).hexdigest())
    raise ValueError('No file match found')


def get_latest_installable_release(p: MutableMapping, bin_name: str) -> Optional[MutableMapping]:
    for rel in p['releases']:
        if bin_name in rel:
            return rel
    return None


def get_python_package_name(pkg: MutableMapping) -> str:
    return pkg.get('wheelname', pkg.get('name')).replace('.', '_').replace(' ', '_').replace('(', '_').replace(')', '')


def write_new_releses(name: str, pfile: MutableMapping, new_rels: MutableMapping, rel_order: MutableSequence) -> bool:
    if new_rels:
        for rel in pfile['releases']:
            new_rels[rel['version']] = rel
        rel_list = []
        for rel_ver in rel_order:
            # This is a placeholder default for creating packages. Yeet it.
            if rel_ver == 'create-package':
                continue
            rel_list.append(new_rels[rel_ver])
        pfile['releases'] = rel_list
        pfile['releases'].sort(key=lambda r: r['published'], reverse=True)

        fnext = '.json' if args.overwrite else '.new.json'
        with open(localpath.joinpath(name + fnext), 'w', encoding='utf-8') as pl:
            json.dump(fp=pl, obj=pfile, ensure_ascii=False, indent=4)
        print('Release file updated')
        return True
    else:
        print('Release file already up to date')
        return False


def get_new_rel(name: str, reltype: str, rel: MutableMapping,
                pfile: MutableMapping, dl_files: MutableSequence,
                zipball: Optional[str] = None) -> Optional[MutableMapping[str, Any]]:
    ret_rel_entry = {'version': rel['tag_name'], 'published': rel['published_at']}
    latest_rel = get_latest_installable_release(pfile, reltype)
    if latest_rel is None or latest_rel.get(reltype) is None:
        return None
    new_url = None
    if reltype == 'script' and ('/archive/' in latest_rel['script']['url'] or
                                '/zipball/' in latest_rel['script']['url']):
        new_url = zipball
    if new_url is None:
        new_url = get_most_similar(latest_rel[reltype]['url'], dl_files)
    try:
        temp_fn = fetch_url_to_cache(new_url, name, rel['tag_name'],
                                     f"{pfile['name']} {rel['tag_name']} {reltype}")
        ret_rel_entry[reltype] = {'url': new_url, 'files': {}}
        for fn in latest_rel[reltype]['files']:
            new_fn, digest = decompress_and_hash(temp_fn, fn[0], reltype)
    except (URLError, subprocess.CalledProcessError, ValueError):
        print(f'No {reltype} release found.')
        return None
    ret_rel_entry[reltype]['files'][fn] = [new_fn, digest]
    return ret_rel_entry


def update_package(name: str) -> int:
    with open(localpath.joinpath(name + '.json'), 'r', encoding='utf-8') as ml:
        pfile: Dict = json.load(ml)

    new_rel_entry: Optional[MutableMapping[str, Any]] = {'version': '', 'published': ''}
    assert isinstance(new_rel_entry, MutableMapping)

    existing_rel_list = []
    for rel in pfile['releases']:
        existing_rel_list.append(rel['version'])
    rel_order = existing_rel_list.copy()

    use_pypi = pfile['type'] == 'PyWheel' and (pfile.get('source', 'pypi') == 'pypi')

    if pfile['type'] == 'PyWheel':
        if use_pypi:
            new_rels = {}
            apifile: Dict = json.loads(fetch_url(get_pypi_api_url(get_python_package_name(pfile)), pfile['name']))
            for version in apifile['releases']:
                version = str(version)
                for rel in apifile['releases'][version]:
                    if rel['yanked'] or rel['packagetype'] != 'bdist_wheel':
                        break
                    new_rel_entry = {'version': version, 'published': rel['upload_time_iso_8601'],
                                     'wheel': {'url': rel['url'], 'hash': rel['digests']['sha256']}
                                     }
                    new_rels[version] = new_rel_entry
                    if version not in rel_order:
                        rel_order.insert(0, version)
            return int(write_new_releses(name, pfile, new_rels, rel_order))
        else:
            print('PyWheel can only be scanned from pypi')
            return -1
    elif 'github' in pfile:
        new_rels = {}
        is_pyscript = pfile['type'] == 'PyScript'

        if is_pyscript and pfile.get('updatemode', '') == 'git-commits':
            apifile = {}  # no releases dummy
            try:
                latest_rel = get_latest_installable_release(pfile, 'script')
                if latest_rel is None:
                    return 0
                fpath = Path(list(latest_rel['script']['files'].values())[0][0]).name  # type: ignore

                git_commits = json.loads(
                    fetch_url(
                        get_git_api_commits_url(pfile['github'], fpath, pfile.get('gitbranch')) or '',
                        pfile['name']
                    )
                )

                git_hash = git_commits[0]['sha']
                git_hash_short = git_hash[:7]
                git_datetime_fmt = '%Y-%m-%dT%H:%M:%SZ'

                try:
                    # commit_date = datetime.strptime(git_commits[0]['commit']['committer']['date'], git_datetime_fmt)
                    # diff_date_commit = (datetime.now() - commit_date).days
                    pub_date = datetime.strptime(latest_rel.get('published', ''), git_datetime_fmt)
                    diff_date_package = (datetime.now() - pub_date).days
                except ValueError:
                    print('Parsing published date failed')
                    diff_date_package = 0

                if(diff_date_package > time_limit):
                    git_txt = f'git:{git_hash_short}'
                    if not any(git_txt in ver for ver in rel_order):
                        rel_order.insert(0, git_txt)
                        print(f'{git_txt} (new)')
                    new_rel_entry.update({'version': git_txt,
                                          'published': git_commits[0]['commit']['committer']['date']})

                    new_url = get_git_api_zipball_url(pfile['github'], git_hash)
                    if new_url is None:
                        return 0
                    temp_fn = fetch_url_to_cache(new_url, name, git_hash_short,
                                                 f"{pfile['name']} {git_hash_short} script")
                    new_rel_entry['script'] = {'url': new_url, 'files': {}}
                    for fn in latest_rel['script']['files']:
                        new_fn, digest = decompress_and_hash(temp_fn, fn[0], 'script')
                        new_rel_entry['script']['files'][fn] = [new_fn, digest]
                    assert isinstance(new_rel_entry, dict)
                    new_rels[new_rel_entry['version']] = new_rel_entry
						
                        new_rels[new_rel_entry['version']] = new_rel_entry
                else:
                    print(f'skipping git commit(s) - this and the last commit must be at least {time_limit} days apart')

            except Exception:
                new_rel_entry.pop('script', None)
                print('No script found')
        else:
            apifile = json.loads(fetch_url(get_git_api_url(pfile['github']) or '', pfile['name'], token=args.git_token))

        for rel in apifile:
            zipball = None
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

                new_rel_entry = (get_new_rel(name, 'win32', rel, pfile, dl_files) or
                                 get_new_rel(name, 'win64', rel, pfile, dl_files) or
                                 get_new_rel(name, 'script', rel, pfile, dl_files, zipball))
                if new_rel_entry is None:
                    return 0

                assert isinstance(new_rel_entry, dict)
                new_rels[new_rel_entry['version']] = new_rel_entry
        return int(write_new_releses(name, pfile, new_rels, rel_order))
    else:
        print(f'Only github and pypi projects supported, {name} not scanned')
        return -1


def verify_package(pfile: MutableMapping, existing_identifiers: Sequence[str]) -> None:
    name: str = pfile['name']
    for key in pfile.keys():
        if key not in ('name', 'type', 'device', 'api', 'description', 'website', 'category', 'identifier',
                       'modulename', 'wheelname', 'namespace', 'github', 'doom9', 'dependencies', 'ignore',
                       'releases', 'updatemode', 'gitbranch'):
            raise ValueError(f'Unknown key: {key} in {name}')
    if pfile['type'] not in ('VSPlugin', 'PyScript', 'PyWheel'):
        raise ValueError('Invalid type in ' + name)
    if (pfile['type'] == 'VSPlugin') and ('modulename' in pfile):
        raise ValueError(f"VSPlugin can't have modulenames: {name}")
    if (pfile['type'] == 'VSPlugin') and (('modulename' in pfile) or ('namespace' not in pfile)):
        raise ValueError('VSPlugin must have namespace, not modulename: ' + name)
    if (pfile['type'] in ('PyScript', 'PyWheel')) and ('namespace' in pfile or 'modulename' not in pfile):
        raise ValueError('PyScript must have modulename, not namespace: ' + name)
    if ((pfile['type'] == 'PyScript' or pfile['type'] == 'VSPlugin') and 'wheelname' in pfile):
        raise ValueError('Only PyWheel type can have wheelname: ' + name)
    allowed_categories = ('Scripts', 'Plugin Dependency', 'Resizing and Format Conversion', 'Other',
                          'Dot Crawl and Rainbows', 'Sharpening', 'Denoising', 'Deinterlacing', 'Inverse Telecine',
                          'Source/Output', 'Subtitles', 'Color/Levels')
    if pfile['category'] not in allowed_categories:
        raise ValueError(f"Not allowed catogry in {name}: {pfile['category']} not in {repr(allowed_categories)}")
    if 'updatemode' in pfile:
        if pfile['updatemode'] not in ('git-commits'):
            raise ValueError('Invalid updatemode in ' + name)
    if 'api' in pfile:
        if pfile['api'] not in (3, 4):
            raise ValueError('Invalid api version in ' + name)
    if 'dependencies' in pfile:
        for dep in pfile['dependencies']:
            if dep not in existing_identifiers:
                raise ValueError('Referenced unknown identifier ' + dep + ' in ' + name)
    if 'device' in pfile:
        for dev in pfile['device']:
            if dev not in ('cpu', 'cuda', 'opencl', 'vulkan'):
                raise ValueError('Invalid device in ' + name)


def compile_packages() -> None:
    combined = []
    existing_identifiers = []
    for f in localpath.iterdir():
        if f.is_file() and f.name.endswith('.json'):
            with open(f, 'r', encoding='utf-8') as ml:
                pfile: Dict = json.load(ml)
                if pfile.get('identifier', 'vsrupdate_default') in existing_identifiers:
                    raise ValueError('Duplicate identifier: ' + pfile['identifier'])
                existing_identifiers.append(pfile['identifier'])

    for f in localpath.iterdir():
        if f.is_file() and f.name.endswith('.json') and not f.name.endswith('.new.json'):
            with open(f, 'r', encoding='utf-8') as ml:
                pfile = json.load(ml)
            print('Combining: ' + f.name)
            verify_package(pfile, existing_identifiers)
            pfile.pop('ignore', None)
            combined.append(pfile)

    data = json.dumps(obj={'file-format': 3, 'packages': combined}, ensure_ascii=False, indent=4)
    Path('vspackages3.zip').unlink(missing_ok=True)

    with zipfile.ZipFile('vspackages3.zip', mode='w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zf.writestr('vspackages3.json', data)


def getBinaryArch(bin: bytes) -> Optional[int]:
    if b'PE\x00\x00d\x86' in bin:     # hex: 50 45 00 00 64 86 | PE..d†
        return 64
    if b'PE\x00\x00L' in bin:         # hex: 50 45 00 00 4c     | PE..L
        return 32
    return None


def decompress_hash_simple(archive: Path, file: str) -> Tuple[str, str, Optional[int]]:
    result = subprocess.run([cmd7zip_path, 'e', '-so', str(archive), file],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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


def blank_package(name: str, url: str, is_script: bool = False, is_wheel: bool = False) -> MutableMapping:
    giturl = extract_git_repo(url)
    p = {
            'name': name,
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
    if args.package is None:
        num_skipped = 0
        num_nochange = 0
        num_updated = 0
        ratelimited = False
        for f in localpath.iterdir():
            if f.is_file() and f.name.endswith('.json'):
                try:
                    result = update_package(f.stem)
                except HTTPError as e:
                    if e.code == 403:
                        print(f'Ratelimit exceeded for {e.geturl()} Aborting!')
                        ratelimited = True
                        result = -1
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
    print(f'outputting the new package definition to {localpath}')

    if not args.packageurl:
        print('-url parameter is missing')
        sys.exit(1)
    if not args.packagename:
        print('-pname parameter is missing')
        sys.exit(1)

    url = args.packageurl
    is_wheel = Path(url).suffix.lower() == '.whl'

    print('fetching remote url')
    dlfile = fetch_url_to_cache(url, 'package', 'creator', '')

    print('creating package')
    new_rel_entry: MutableMapping[str, Any] = {'version': 'create-package', 'published': ''}

    if is_wheel:
        new_rel_entry['wheel'] = {'url': url}
        new_rel_entry['wheel']['hash'] = hashlib.sha256(open(dlfile, 'rb').read()).hexdigest()

    # is plugin or script
    else:
        listzip = list_archive_files(dlfile)
        files_to_hash: List[str] = []
        for f in listzip.values():
            # simple folder filter
            if Path(f).suffix:
                if '*' in args.packagefiletypes:
                    files_to_hash.append(str(f))
                else:
                    if Path(f).suffix in args.packagefiletypes:
                        files_to_hash.append(str(f))

        files_to_hash = sorted(files_to_hash)

        print('\n\nFound the following dlls:')
        for fname in files_to_hash:
            fullpath, hash, arch = decompress_hash_simple(dlfile, fname)
            if arch == 32:
                print('win32:', fullpath, hash)
            if arch == 64:
                print('win64:', fullpath, hash)
        print('\n\n')

        # is plugin
        if not args.packagescript:
            new_rel_entry['win32'] = {'url': url, 'files': {}}
            new_rel_entry['win64'] = {'url': url, 'files': {}}
            for fname in files_to_hash:
                fullpath, hash, arch = decompress_hash_simple(dlfile, fname)
                file = keep_folder_structure(fullpath, args.keepfolder) if args.keepfolder >= 0 else Path(fullpath).name
                if arch == 32:
                    new_rel_entry['win32']['files'][file] = [fullpath, hash]
                if arch == 64:
                    new_rel_entry['win64']['files'][file] = [fullpath, hash]
                if arch is None:
                    new_rel_entry['win32']['files'][file] = [fullpath, hash]
                    new_rel_entry['win64']['files'][file] = [fullpath, hash]

            # remove 32/64 entry if no files are present
            if not new_rel_entry['win32']['files']:
                new_rel_entry.pop('win32', None)
            if not new_rel_entry['win64']['files']:
                new_rel_entry.pop('win64', None)

        else:  # is script
            new_rel_entry['script'] = {'url': url, 'files': {}}
            for fname in files_to_hash:
                fullpath, hash, arch = decompress_hash_simple(dlfile, fname)
                file = keep_folder_structure(fullpath, args.keepfolder) if args.keepfolder >= 0 else Path(fullpath).name
                new_rel_entry['script']['files'][file] = [fullpath, hash]

    if not args.packagescript:
        if is_wheel:
            final_package = blank_package(args.packagename, url, is_wheel=True)
        else:
            final_package = blank_package(args.packagename, url)
    else:
        final_package = blank_package(args.packagename, url, is_script=True)
    final_package['releases'] = [new_rel_entry]

    print(json.dumps(final_package, indent=4))
    pkgfile = localpath.joinpath(args.packagename + '.json')
    if not pkgfile.exists():
        with open(pkgfile, 'x', encoding='utf-8') as pl:
            json.dump(fp=pl, obj=final_package, ensure_ascii=False, indent=4)

        print('package created')

        if extract_git_repo(url) and not is_wheel:
            print('Is hosted on GitHub - auto updating package')
            args.overwrite = True
            update_package(args.packagename)

        if is_wheel and url.startswith('https://files.pythonhosted.org'):
            print('Auto updating wheel package')
            args.overwrite = True
            update_package(args.packagename)
    else:
        print(f"package file '{args.packagename}.json' already exists. Skipping writing file.")
elif args.operation == 'upload':
    compile_packages()
    print('Packages successfully compiled')
    with open('vspackages3.zip', 'rb') as bpl:
        with ftplib.FTP_TLS(host=args.host[0], user=args.user[0], passwd=args.passwd[0]) as ftp:
            if args.dir is not None:
                ftp.cwd(args.dir[0])
            try:
                ftp.delete('vspackages3.zip')
            except (ftplib.error_perm, ftplib.error_reply):
                print('Failed to delete vspackages3.zip')
            ftp.storbinary('STOR vspackages3.zip', bpl)
    print('Upload done')
