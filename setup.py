#!/usr/bin/env python3

import platform
from pathlib import Path

import setuptools

package_name = 'vsrepo'

is_windows = platform.platform().startswith('Windows')

packages = ['vsgenstubs', 'vsgenstubs4']
modules = requirements = []

if is_windows:
    modules = ['vsrepo', 'vsrupdate']
    requirements = ['tqdm']

entrypoints = [*packages, *modules]


setuptools.setup(
    name=package_name,
    version='50',
    author='Myrsloik',
    author_email='fredrik.mellbin@gmail.com',
    description='A simple package repository for VapourSynth',
    long_description=Path('README.md').read_text(),
    long_description_content_type='text/markdown',
    url='https://www.vapoursynth.com/',
    project_urls={
        'Issues': 'https://github.com/vapoursynth/vsrepo/issues',
        'Source': 'https://github.com/vapoursynth/vsrepo'
    },
    install_requires=requirements,
    python_requires='>=3.8',
    py_modules=modules,
    packages=[
        package_name
    ],
    include_package_data=True,
    package_data={
        package: ['*.pyi', 'py.typed'] for package in packages
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    entry_points={
        'console_scripts': [
            f'{module}={module}:main'
            for module in entrypoints
        ]
    }
)
