import urllib.request
import json
import os
import argparse

parser = argparse.ArgumentParser(description='Package list generator for VSRepo')
parser.add_argument('-l', action='store_true', dest='local', help='Only use local sources when generating output')
args = parser.parse_args()

combined = []
seen = {}
source_list = None

with open('sources.json', 'r', encoding='utf-8') as sl:
    source_list = json.load(sl)

for f in os.scandir('local'):
    if f.is_file():
        with open(f.path, 'r', encoding='utf-8') as ml:
            print('Combining: ' + f.path)
            combined.append(json.load(ml))

if not args.local:
    for url in source_list['sources']:
        print('Combining: ' + url)
        urllib.request.urlopen(url)
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
