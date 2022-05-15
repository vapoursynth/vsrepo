from setuptools import setup
from os import path

import platform

modules = []
packages = [
    "vsgenstubs"
]
requirements = []
entrypoints = ["vsgenstubs=vsgenstubs:main"]

if platform.platform().startswith("Windows"):
    modules.extend(["vsrepo", "vsrupdate"])
    entrypoints.extend([
        "vsrepo=vsrepo:noop",
        "vsrupdate=vsrupdate:noop"
    ])
    requirements.append("tqdm")

here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="vsrepo",
    version="50",
    description="A simple package repository for VapourSynth.",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    url="http://www.vapoursynth.com/",
    author = "Myrsloik",
    packages=["vsgenstubs"],
    py_modules = modules,
    install_requires=requirements,
    include_package_data=True,
    package_data={
        "vsgenstubs": ["*.pyi"]
    },
    entry_points = {
        'console_scripts': entrypoints
    },
    project_urls={
        "Issues": "https://github.com/vapoursynth/vsrepo/issues",
        "Source": "https://github.com/vapoursynth/vsrepo"
    }
)
