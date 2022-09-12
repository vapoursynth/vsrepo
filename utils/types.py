from dataclasses import dataclass, field
from enum import Enum
import json
import logging
from pathlib import Path
import sys
from typing import Dict, Generic, List, NamedTuple, Tuple, Type, TypeVar, TypedDict, Union

T = TypeVar('T')
VT = TypeVar('VT')


class DescriptorBase(Generic[VT, T]):
    cls_type: Type[T]

    def __class_getitem__(cls, new_cls_type: Tuple[Type[VT], Type[T]]) -> 'Type[DescriptorBase[VT, T]]':
        class inner_Descriptor(cls):  # type: ignore
            @property
            def cls_type(cls) -> Type[T]:
                if not hasattr(cls, '_cls_type'):
                    cls._cls_type = eval(new_cls_type[-1])  # type: ignore
                return cls._cls_type  # type: ignore

        return inner_Descriptor

    def __init__(self, *, default: T) -> None:
        self._default = default

    def __set_name__(self, owner: object, name: str) -> None:
        self._name = "_" + name

    def __get__(self, obj: object, ctype: type) -> T:
        if obj is None:
            return self._default

        return getattr(obj, self._name, self._default)

    def __set__(self, obj: object, value: Union[VT, T]) -> None:
        setattr(obj, self._name, self.cls_type(value))  # type: ignore


class VSPackageUpdateMode(str, Enum):
    MANUAL = 'manual'
    GIT = 'git-commits'

    class Descriptor(DescriptorBase[str, 'VSPackageUpdateMode']):
        ...


class VSPackageDeviceType(str, Enum):
    CPU = 'cpu'
    CUDA = 'cuda'
    OPENCL = 'opencl'
    VULKAN = 'vulkan'

    class Descriptor(DescriptorBase[str, 'VSPackageDeviceType']):
        ...


class VSPackageType(str, Enum):
    SCRIPT = 'PyScript'
    WHEEL = 'PyWheel'
    PLUGIN = 'VSPlugin'

    class Descriptor(DescriptorBase[str, 'VSPackageType']):
        ...

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
    category: str
    description: str
    github: str
    identifier: str
    namespace: str
    releases: List[VSPackageRelease]
    type: VSPackageType.Descriptor = VSPackageType.Descriptor(default=VSPackageType.SCRIPT)
    updatemode: VSPackageUpdateMode.Descriptor = VSPackageUpdateMode.Descriptor(default=VSPackageUpdateMode.MANUAL)
    dependencies: List[str] = field(default_factory=list)
    device: List[VSPackageDeviceType] = field(default_factory=list)
    modulename: Union[str, None] = None
    wheelname: Union[str, None] = None


@dataclass
class VSPackages:
    file_format: int
    packages: List[VSPackage]
