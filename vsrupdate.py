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

import urllib.request
from urllib.request import ProxyHandler, build_opener
import json
import sys
import os
import os.path
import argparse
import hashlib
import subprocess
import difflib
import tempfile
import ftplib

try:
    import winreg
except ImportError:
    print('{} is only supported on Windows.'.format(__file__))
    exit(1)

try:
    import tqdm
except ImportError:
    pass

parser = argparse.ArgumentParser(description='Package list generator for VSRepo')
parser.add_argument('operation', choices=['compile', 'update-local', 'upload'])
parser.add_argument('-g', dest='git_token', nargs=1, help='OAuth access token for github')
parser.add_argument('-p', dest='package', nargs=1, help='Package to update')
parser.add_argument('-o', action='store_true', dest='overwrite', help='Overwrite existing package file')
parser.add_argument('-host', dest='host', nargs=1, help='FTP Host')
parser.add_argument('-user', dest='user', nargs=1, help='FTP User')
parser.add_argument('-passwd', dest='passwd', nargs=1, help='FTP Password')
parser.add_argument('-dir', dest='dir', nargs=1, help='FTP dir')
parser.add_argument('-proxy', dest='proxy', default='', help='custom http download proxy')

args = parser.parse_args()

cmd7zip_path = '7z.exe'
try:
    with winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\7-Zip', reserved=0, access=winreg.KEY_READ) as regkey:
        cmd7zip_path = winreg.QueryValueEx(regkey, 'Path')[0] + '7z.exe'
except:
    pass

if args.proxy is not '':
    proxy_handler = urllib.request.ProxyHandler({'http': args.proxy, 'https': args.proxy})
    opener = urllib.request.build_opener(proxy_handler)
    urllib.request.install_opener(opener)

def similarity(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()

def get_most_similar(a, b):
    res = (0, '')
    for s in b:
        v = similarity(a, s)
        if v >= res[0]:
            res = (v, s)
    return res[1]

def get_git_api_url(url):
    if url.startswith('https://github.com/'):
        s = url.rsplit('/', 3)
        return 'https://api.github.com/repos/' + s[-2] + '/' + s[-1] + '/releases?access_token=' + args.git_token[0]
    else:
        return None

def fetch_url(url, desc = None):
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

def fetch_url_to_cache(url, name, tag_name, desc = None):
    cache_path = 'dlcache/' + name + '_' + tag_name + '/' + url.rsplit('/')[-1]
    if not os.path.isfile(cache_path):
        os.makedirs(os.path.split(cache_path)[0], exist_ok=True)
        with urllib.request.urlopen(urllib.request.Request(url, method='HEAD')) as urlreq:
            cache_path = 'dlcache/' + name + '_' + tag_name + '/' + urlreq.info().get_filename()
            if not os.path.isfile(cache_path):
                data = fetch_url(url, desc)
                with open(cache_path, 'wb') as pl:
                    pl.write(data)
    return cache_path

def list_archive_files(fn):
    result = subprocess.run([cmd7zip_path, "l", "-ba", fn], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result.check_returncode()
    l = {}
    lines = result.stdout.decode('utf-8').splitlines()
    for line in lines:
        t = line[53:].replace('\\', '/')
        l[t.lower()] = t
    return l

def generate_fn_candidates(fn):
    tmp_fn = fn.lower()
    return [
        tmp_fn,
        tmp_fn.replace('x64', 'win64'),
        tmp_fn.replace('win64', 'x64'),
        tmp_fn.replace('x86', 'win32'),
        tmp_fn.replace('win32', 'x86')]

def decompress_and_hash(archivefn, fn):
    existing_files = list_archive_files(archivefn)
    for fn_guess in generate_fn_candidates(fn):
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
            for fn_guess in generate_fn_candidates(mfn):
                if fn_guess in existing_files:  
                    result = subprocess.run([cmd7zip_path, "e", "-so", archivefn, fn_guess], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    result.check_returncode()
                    return (existing_files[fn_guess], hashlib.sha256(result.stdout).hexdigest())
    raise Exception('No file match found')

def get_latest_installable_release(p, bin_name):
    for rel in p['releases']:
        if bin_name in rel:
            return rel
    return None

def update_package(name):
    with open('local/' + name + '.json', 'r', encoding='utf-8') as ml:
        pfile = json.load(ml)
        existing_rel_list = []
        for rel in pfile['releases']:
            existing_rel_list.append(rel['version'])
        rel_order = list(existing_rel_list)
        
        if 'github' in pfile:
            new_rels = {}
            apifile = json.loads(fetch_url(get_git_api_url(pfile['github']), pfile['name']))
            is_plugin = (pfile['type'] == 'VSPlugin')
            for rel in apifile:
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
                                    new_fn, digest = decompress_and_hash(temp_fn, latest_rel['win32']['files'][fn][0])
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
                                    new_fn, digest = decompress_and_hash(temp_fn, latest_rel['win64']['files'][fn][0])
                                    new_rel_entry['win64']['files'][fn] = [new_fn, digest]
                        except:
                            new_rel_entry.pop('win64', None)
                            print('No win64 binary found')
                    else:
                        new_rel_entry = { 'version': rel['tag_name'], 'published': rel['published_at'] }
                        try:
                            latest_rel = get_latest_installable_release(pfile, 'script')
                            new_url = None
                            if ('/archive/' in latest_rel['script']['url']) or ('/zipball/' in latest_rel['script']['url']):
                                new_url = zipball
                            else:
                                new_url = get_most_similar(latest_rel['script']['url'], dl_files)
                            temp_fn = fetch_url_to_cache(new_url, name, rel['tag_name'], pfile['name'] + ' ' +rel['tag_name'] + ' script')
                            new_rel_entry['script'] = { 'url': new_url, 'files': {} }
                            for fn in latest_rel['script']['files']:
                                new_fn, digest = decompress_and_hash(temp_fn, latest_rel['script']['files'][fn][0])
                                new_rel_entry['script']['files'][fn] = [new_fn, digest]
                        except:
                            new_rel_entry.pop('script', None)
                            print('No script found')
                    new_rels[new_rel_entry['version']] = new_rel_entry
            has_new_releases = bool(new_rels)
            for rel in pfile['releases']:
                new_rels[rel['version']] = rel
            rel_list = []
            for rel_ver in rel_order:
                rel_list.append(new_rels[rel_ver])
            pfile['releases'] = rel_list
            pfile['releases'].sort(key=lambda r: r['published'], reverse=True)
            
            if has_new_releases:
                if args.overwrite:
                    with open('local/' + name + '.json', 'w', encoding='utf-8') as pl:
                        json.dump(fp=pl, obj=pfile, ensure_ascii=False, indent='\t')
                else:
                    with open('local/' + name + '.new.json', 'w', encoding='utf-8') as pl:
                        json.dump(fp=pl, obj=pfile, ensure_ascii=False, indent='\t')
                print('Release file updated')
                return 1
            else:
                print('Release file already up to date')
                return 0
        else:
            print('Only github projects supported, ' + name + ' not scanned')
            return -1

def verify_package(pfile, existing_identifiers):
    name = pfile['name']
    for key in pfile.keys():
        if key not in ('name', 'type', 'description', 'website', 'category', 'identifier', 'modulename', 'namespace', 'github', 'doom9', 'dependencies', 'ignore', 'releases'):
            raise Exception('Unkown key: ' + key + ' in ' + name)
    if pfile['type'] not in ('VSPlugin', 'PyScript'):
        raise Exception('Invalid type in ' + name)
    if (pfile['type'] == 'VSPlugin') and ('modulename' in pfile):
        raise Exception('Plugins can\'t have modulenames: ' + name)
    if (pfile['type'] == 'VSPlugin') and (('modulename' in pfile) or ('namespace' not in pfile)):
        raise Exception('Plugins must have namespace, not modulename: ' + name)
    if (pfile['type'] == 'PyScript') and (('namespace' in pfile) or ('modulename' not in pfile)):
        raise Exception('Scripts must have modulename, not namespace: ' + name)
    allowed_categories = ('Scripts', 'Plugin Dependency', 'Resizing and Format Conversion', 'Other', 'Dot Crawl and Rainbows', 'Sharpening', 'Denoising', 'Deinterlacing', 'Inverse Telecine', 'Source/Output', 'Subtitles', 'Color/Levels')
    if pfile['category'] not in allowed_categories:
        raise Exception('Not allowed catogry in ' + name + ': ' + pfile['category'] + ' not in ' + repr(allowed_categories))
    if 'dependencies' in pfile:
        for dep in pfile['dependencies']:
            if dep not in existing_identifiers:
                raise Exception('Referenced unknown identifier ' + dep + ' in ' + name)

if args.operation == 'compile':
    combined = []
    existing_identifiers = []
    for f in os.scandir('local'):
        if f.is_file() and f.path.endswith('.json'):
            with open(f.path, 'r', encoding='utf-8') as ml:
                pfile = json.load(ml)
                if pfile['identifier'] in existing_identifiers:
                    raise Exception('Duplicate identifier: ' + pfile['identifier'])
                existing_identifiers.append(pfile['identifier'])

    for f in os.scandir('local'):
        if f.is_file() and f.path.endswith('.json'):
            with open(f.path, 'r', encoding='utf-8') as ml:
                print('Combining: ' + f.path)
                pfile = json.load(ml)
                verify_package(pfile, existing_identifiers)
                pfile.pop('ignore', None)
                combined.append(pfile)

    with open('vspackages.json', 'w', encoding='utf-8') as pl:
        json.dump(fp=pl, obj={ 'file-format': 2, 'packages': combined}, ensure_ascii=False, indent=2)

    try:
        os.remove('vspackages.zip')
    except:
        pass
    result = subprocess.run([cmd7zip_path, 'a', '-tzip', 'vspackages.zip', 'vspackages.json'])
    result.check_returncode()
    
    print('Done')
elif args.operation == 'update-local':
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
        print('Summary:\nUpdated: {} \nNo change: {} \nSkipped: {}\n'.format(num_updated, num_nochange, num_skipped))
    else:
        update_package(args.package[0])
elif args.operation == 'upload':
    with open('vspackages.zip', 'rb') as pl:
        with ftplib.FTP_TLS(host=args.host[0], user=args.user[0], passwd=args.passwd[0]) as ftp:
            ftp.cwd(args.dir[0])
            try:
                ftp.delete('vspackages.zip')
            except:
                print('Failed to delete vspackages.zip')
            ftp.storbinary('STOR vspackages.zip', pl)
    print('Done')
