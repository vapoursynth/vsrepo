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
import json
import os
import os.path
import argparse
import zipfile
import hashlib
import subprocess
import winreg
import difflib
import tempfile

parser = argparse.ArgumentParser(description='Package list generator for VSRepo')
parser.add_argument('operation', choices=['compile', 'update-local', 'check-updates'])
parser.add_argument('-l', action='store_true', dest='local', help='Only use local sources when generating output')
parser.add_argument('-g', dest='git_token', nargs=1, help='OAuth access token for github')
parser.add_argument('-p', dest='package', nargs=1, help='Package to update')
parser.add_argument('-o', action='store_true', dest='overwrite', help='Overwrite existing package file')
args = parser.parse_args()

cmd7zip_path = '7z.exe'
try:
    with winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\7-Zip', reserved=0, access=winreg.KEY_READ) as regkey:
        cmd7zip_path = winreg.QueryValueEx(regkey, 'Path')[0] + '7z.exe'
except:
    pass

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

def fetch_url(url):
    urlreq = urllib.request.urlopen(url)
    data = urlreq.read()
    return data

def fetch_url_to_cache(url, name, tag_name):
    cache_path = 'dlcache/' + name + '_' + tag_name + '/' + url.rsplit('/')[-1]
    if not os.path.isfile(cache_path):
        os.makedirs(os.path.split(cache_path)[0], exist_ok=True)
        req = urllib.request.Request(url, method='HEAD')
        urlreq = urllib.request.urlopen(req)
        cache_path = 'dlcache/' + name + '_' + tag_name + '/' + urlreq.info().get_filename()
        if not os.path.isfile(cache_path):
            print('Download required: ' + url)
            urlreq = urllib.request.urlopen(url)
            data = urlreq.read()
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
            return (existing_files[fn_guess], hashlib.sha1(result.stdout).hexdigest())
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
                    return (existing_files[fn_guess], hashlib.sha1(result.stdout).hexdigest())
    raise Exception('No file match found')

def update_package(name):
    with open('local/' + name + '.json', 'r', encoding='utf-8') as ml:
        pfile = json.load(ml)
        existing_rel_list = []
        rel_order = []
        for rel in pfile['releases']:
            existing_rel_list.append(rel['version'])
        
        url = get_git_api_url(pfile['website'])
        if url is None:
            print('Only github projects supported, ' + name + ' not scanned')
        else:
            print('Scanning: ' + url)
            new_rels = {}
            apifile = None
            apifile = json.loads(fetch_url(get_git_api_url(pfile['website'])))
            is_plugin = (pfile['type'] == 'Plugin')
            for rel in apifile:
                rel_order.append(rel['tag_name'])
                if rel['tag_name'] in existing_rel_list:
                    print(rel['tag_name'] + ' (known)')
                else:
                    print(rel['tag_name'] + ' (new)')
                    zipball = rel['zipball_url']
                    dl_files = []
                    for asset in rel['assets']:
                        dl_files.append(asset['browser_download_url'])
                    
                    #ugly copypaste here because I'm lazy
                    lastest_rel = pfile['releases'][0]
                    if is_plugin:
                        new_rel_entry = { 'version': rel['tag_name'] }
                        try:
                            if 'win32' in lastest_rel:
                                new_url = get_most_similar(lastest_rel['win32']['url'], dl_files)
                                temp_fn = fetch_url_to_cache(new_url, name, rel['tag_name'])
                                new_rel_entry['win32'] = { 'url': new_url, 'files': [], 'hash': {} }
                                for fn in lastest_rel['win32']['files']:
                                    stripped_fn = fn.rsplit('/', 2)[-1]
                                    new_fn, digest = decompress_and_hash(temp_fn, fn)
                                    new_rel_entry['win32']['files'].append(new_fn)
                                    new_rel_entry['win32']['hash'][stripped_fn] = digest
                        except:
                            new_rel_entry.pop('win32', None)
                            print('No win32 binary found')
                        try:
                            if 'win64' in lastest_rel:
                                new_url = get_most_similar(lastest_rel['win64']['url'], dl_files)
                                temp_fn = fetch_url_to_cache(new_url, name, rel['tag_name'])
                                new_rel_entry['win64'] = { 'url': new_url, 'files': [], 'hash': {} }
                                for fn in lastest_rel['win64']['files']:
                                    stripped_fn = fn.rsplit('/', 2)[-1]
                                    new_fn, digest = decompress_and_hash(temp_fn, fn)
                                    new_rel_entry['win64']['files'].append(new_fn)
                                    new_rel_entry['win64']['hash'][stripped_fn] = digest
                        except:
                            new_rel_entry.pop('win64', None)
                            print('No win64 binary found')
                    else:
                        new_rel_entry = { 'version': rel['tag_name'] }
                        try:
                            new_url = None
                            if ('/archive/' in lastest_rel['script']['url']) or ('/zipball/' in lastest_rel['script']['url']):
                                new_url = zipball
                            else:
                                new_url = get_most_similar(lastest_rel['script']['url'], dl_files)
                            temp_fn = fetch_url_to_cache(new_url, name, rel['tag_name'])
                            new_rel_entry['script'] = { 'url': new_url, 'files': [], 'hash': {} }
                            for fn in lastest_rel['script']['files']:
                                stripped_fn = fn.rsplit('/', 2)[-1]
                                new_fn, digest = decompress_and_hash(temp_fn, fn)
                                new_rel_entry['script']['files'].append(new_fn)
                                new_rel_entry['script']['hash'][stripped_fn] = digest
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
            
            if has_new_releases:
                if args.overwrite:
                    with open('local/' + name + '.json', 'w', encoding='utf-8') as pl:
                        json.dump(fp=pl, obj=pfile, ensure_ascii=False, indent='\t')
                else:
                    with open('local/' + name + '.new.json', 'w', encoding='utf-8') as pl:
                        json.dump(fp=pl, obj=pfile, ensure_ascii=False, indent='\t')
                print('Release file updated')
            else:
                print('Release file already up to date')
                

if args.operation == 'compile':
    combined = []
    seen = {}

    for f in os.scandir('local'):
        if f.is_file():
            with open(f.path, 'r', encoding='utf-8') as ml:
                print('Combining: ' + f.path)
                combined.append(json.load(ml))

    if not args.local:
        with open('sources.json', 'r', encoding='utf-8') as sl:
            source_list = json.load(sl)
            for url in source_list['sources']:
                print('Combining: ' + url)
                urlreq = urllib.request.urlopen(url)
                data = urlreq.read()
                combined.append(json.loads(data))

    for p in combined:
        if p['identifier'] in seen:
            raise Exception('Duplicate identifier: ' + p['identifier'])
        else:
            seen[p['identifier']] = True

    with open('vspackages.json', 'w', encoding='utf-8') as pl:
        json.dump(fp=pl, obj=combined, ensure_ascii=False, indent=4)

    print('Done')
elif args.operation == 'update-local':
    if args.package[0] == 'all':
        for f in os.scandir('local'):
            if f.is_file() and f.path.endswith('.json'):
                update_package(os.path.splitext(os.path.basename(f))[0])
    else:
        update_package(args.package[0])
        
