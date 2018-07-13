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
