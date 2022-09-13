import json
import logging
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Generic, Iterator, List, NamedTuple, Type, TypedDict, TypeVar, Union

T = TypeVar('T')


class DescriptorBase(Generic[T]):
    cls_type: Type[T]

    def __class_getitem__(cls, new_cls_type: Type[T]) -> 'DescriptorBase[T]':
        class inner_Descriptor(cls):  # type: ignore
            if isinstance(new_cls_type, type):
                cls_type = new_cls_type
            else:
                @property  # type: ignore
                def cls_type(cls) -> Type[T]:
                    if not hasattr(cls, '_cls_type'):
                        cls._cls_type = eval(new_cls_type)
                    return cls._cls_type

        return inner_Descriptor  # type: ignore

    def __init__(self, default: T) -> None:
        self._default = default

    def __set_name__(self, owner: object, name: str) -> None:
        self._name = '_' + name

    def __get__(self, obj: object, ctype: type) -> T:
        if obj is None:
            return self._default

        return getattr(obj, self._name, self._default)

    def __set__(self, obj: object, value: T) -> None:
        setattr(obj, self._name, self.cls_type(value))  # type: ignore


class CustomEnum(Enum):
    @classmethod
    def Descriptor(cls: Type[T], default: T) -> T:
        return DescriptorBase[cls](default)  # type: ignore


class VSPackageUpdateMode(str, CustomEnum):
    MANUAL = 'manual'
    GIT = 'git-commits'


class VSPackageDeviceType(str, CustomEnum):
    CPU = 'cpu'
    CUDA = 'cuda'
    OPENCL = 'opencl'
    VULKAN = 'vulkan'


class VSPackageType(str, CustomEnum):
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
    api: int = 3


class VSPackageRelease(TypedDict, total=False):
    version: str
    published: str


class VSPackageReleasePyScript(VSPackageRelease):
    script: VSPackagePlatformRelease


class VSPackageReleasePyWheel(VSPackageRelease):
    wheel: VSPackagePlatformReleaseWheel


class _VSPackageReleaseWin32(TypedDict, total=False):
    win32: VSPackagePlatformRelease


class _VSPackageReleaseWin64(TypedDict, total=False):
    win64: VSPackagePlatformRelease


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
    identifier: str
    github: str = ''
    namespace: str = ''
    website: str = ''
    doom9: str = ''
    api: int = 3
    type: VSPackageType = VSPackageType.Descriptor(VSPackageType.SCRIPT)
    updatemode: VSPackageUpdateMode = VSPackageUpdateMode.Descriptor(VSPackageUpdateMode.MANUAL)
    releases: List[VSPackageRelease] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    device: List[VSPackageDeviceType] = field(default_factory=list)
    modulename: Union[str, None] = None
    wheelname: Union[str, None] = None


@dataclass
class VSPackages:
    file_format: int
    packages: List[VSPackage]

    def __iter__(self) -> Iterator[VSPackage]:
        return iter(self.packages)

    @classmethod
    def from_file(cls, filepath: Path, /) -> 'VSPackages':
        try:
            vspackages = json.loads(filepath.read_text())

            if vspackages is None:
                raise ValueError

            file_format = int(vspackages['file-format'])

            if file_format != 3:
                raise ValueError(
                    f'Package definition format is {file_format} but only version 3 is supported'
                )

            packages = [
                VSPackage(**package) for package in vspackages['packages']
            ]
        except (OSError, FileExistsError, ValueError) as e:
            message = str(e) or 'No valid package definitions found. Run update command first!'

            logging.error(message)

            sys.exit(1)

        return VSPackages(file_format, packages)
