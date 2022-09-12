from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, NamedTuple, TypedDict, Union

__all__ = [
    'VSPackageType',
    'VSPackagePlatformReleaseFile',
    'VSPackagePlatformRelease',
    'VSPackageRelease',
    'VSPackage',
    'VSPackages'
]


class VSPackageDeviceType(str, Enum):
    CPU = 'cpu'
    CUDA = 'cuda'
    OPENCL = 'opencl'
    VULKAN = 'vulkan'


class VSPackageType(str, Enum):
    SCRIPT = 'PyScript'
    WHEEL = 'PyWheel'
    PLUGIN = 'VSPlugin'

    def get_package_key(self, n_bits: int = 64) -> str:
        if self is VSPackageType.SCRIPT:
            return 'script'

        if self is VSPackageType.WHEEL:
            return 'wheel'

        if self is VSPackageType.PLUGIN:
            return f'win{n_bits}'


class VSPackagePlatformReleaseFile(NamedTuple):
    filename: str
    hash: str


@dataclass
class VSPackagePlatformReleaseWheel:
    url: str
    hash: str


@dataclass
class VSPackagePlatformRelease:
    url: str
    files: Dict[str, VSPackagePlatformReleaseFile]


class VSPackageRelease(TypedDict, total=False):
    version: str
    published: str


class VSPackageReleasePyScript(VSPackageRelease):
    script: VSPackagePlatformRelease


class VSPackageReleasePyWheel(VSPackageRelease):
    wheel: VSPackagePlatformReleaseWheel


class _VSPackageReleaseWin32(TypedDict, total=False):
    win32: VSPackagePlatformReleaseFile


class _VSPackageReleaseWin64(TypedDict, total=False):
    win64: VSPackagePlatformReleaseFile


class VSPackageReleaseWin32(_VSPackageReleaseWin32, VSPackageRelease):
    ...


class VSPackageReleaseWin64(_VSPackageReleaseWin64, VSPackageRelease):
    ...


class VSPackageReleaseWin(_VSPackageReleaseWin32, _VSPackageReleaseWin64, VSPackageRelease):
    ...


@dataclass
class VSPackage:
    name: str
    type: VSPackageType
    category: str
    description: str
    github: str
    identifier: str
    namespace: str
    releases: List[VSPackageRelease]
    dependencies: List[str] = field(default_factory=list)
    device: List[VSPackageDeviceType] = field(default_factory=list)
    modulename: Union[str, None] = None
    wheelname: Union[str, None] = None


@dataclass
class VSPackages:
    file_format: int
    packages: List[VSPackage]
