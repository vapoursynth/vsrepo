import json
import logging
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Generic, Iterator, List, Literal, NamedTuple, Tuple, Type, TypeVar, Union, overload

from .installations import get_vapoursynth_api_version
from .site import InstallationInfo
from .utils import sanitize_dict

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

        raise ValueError


class VSPackagePlatformReleaseFile(NamedTuple):
    filename: str
    hash: str


@dataclass
class VSPackagePlatformReleaseWheel:
    url: str
    hash: str
    api: int = 3


@dataclass
class VSPackagePlatformRelease:
    url: str
    files: Dict[Path, VSPackagePlatformReleaseFile]
    api: int = 3


@dataclass
class VSPackageRel:
    version: str
    published: str

    @staticmethod
    def from_dict(obj: Dict[str, Any]) -> 'VSPackageRel':
        cls: Type[VSPackageRel] = VSPackageRel
        if (key := VSPackageType.SCRIPT.get_package_key()) in obj:
            cls = VSPackageRelPyScript
        elif (whl_key := VSPackageType.WHEEL.get_package_key()) in obj:
            cls = VSPackageRelPyWheel
        else:
            win32 = (win32_key := VSPackageType.PLUGIN.get_package_key(32)) in obj
            win64 = (win64_key := VSPackageType.PLUGIN.get_package_key(64)) in obj

            if win64 and win32:
                cls = VSPackageRelWin
            elif win64:
                cls = VSPackageRelWin64
                key = win64_key
            elif win32:
                cls = VSPackageRelWin32
                key = win32_key

        if cls is VSPackageRelPyWheel:
            obj[whl_key] = VSPackagePlatformReleaseWheel(**obj[whl_key])
        elif cls is not VSPackageRel:
            keys = [win32_key, win64_key] if cls is VSPackageRelWin else [key]
            for key in keys:
                obj[key] = VSPackagePlatformRelease(**sanitize_dict(obj[key], 'platform_release'))

        # kw_only is Py3.10 only...
        if 'published' not in obj:
            obj['published'] = '2000-01-01T00:00:00Z'

        return cls(**sanitize_dict(obj, 'release'))

    @overload
    def get_release(self, pkg_type: Literal[VSPackageType.WHEEL]) -> Union[  # type: ignore
        VSPackagePlatformReleaseWheel, None
    ]:
        ...

    @overload
    def get_release(self, pkg_type: VSPackageType) -> Union[VSPackagePlatformRelease, None]:
        ...

    def get_release(self, pkg_type: VSPackageType) -> Union[
        VSPackagePlatformRelease, VSPackagePlatformReleaseWheel, None
    ]:
        return getattr(self, pkg_type.get_package_key(), None)


@dataclass
class VSPackageRelPyScript(VSPackageRel):
    script: VSPackagePlatformRelease


@dataclass
class VSPackageRelPyWheel(VSPackageRel):
    wheel: VSPackagePlatformReleaseWheel


@dataclass
class VSPackageRelWin32(VSPackageRel):
    win32: VSPackagePlatformRelease


@dataclass
class VSPackageRelWin64(VSPackageRel):
    win64: VSPackagePlatformRelease


@dataclass
class VSPackageRelWin(VSPackageRelWin32, VSPackageRelWin64):
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
    pkg_type: VSPackageType = VSPackageType.Descriptor(VSPackageType.SCRIPT)
    updatemode: VSPackageUpdateMode = VSPackageUpdateMode.Descriptor(VSPackageUpdateMode.MANUAL)
    releases: List[VSPackageRel] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    device: List[VSPackageDeviceType] = field(default_factory=list)
    modulename: Union[str, None] = None
    wheelname: Union[str, None] = None

    def is_type(self, pkg_type: VSPackageType) -> bool:
        return self.pkg_type is pkg_type

    def get_latest_installable_release_with_index(self) -> Tuple[int, Union[VSPackageRel, None]]:
        max_api = get_vapoursynth_api_version()

        for idx, rel in enumerate(self.releases):
            prel = rel.get_release(self.pkg_type)

            if prel:
                bin_api = max(self.api, prel.api)

                if 3 <= bin_api <= max_api:
                    return (idx, rel)

        return (-1, None)

    def get_latest_installable_release(self) -> Union[VSPackageRel, None]:
        return self.get_latest_installable_release_with_index()[1]

    def get_install_path(self, info: InstallationInfo) -> Path:
        if self.pkg_type in {VSPackageType.SCRIPT, VSPackageType.WHEEL}:
            return info.py_script_path

        if self.pkg_type is VSPackageType.PLUGIN:
            return info.plugin_path

        raise ValueError('Unknown install type')

    def get_python_name(self) -> str:
        package_name = self.wheelname or self.name

        return package_name.replace('.', '_').replace(' ', '_').replace('(', '_').replace(')', '')


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
                VSPackage(**sanitize_dict(package, 'package'))
                for package in vspackages['packages']
            ]
        except (OSError, FileExistsError, ValueError) as e:
            message = str(e) or 'No valid package definitions found. Run update command first!'

            logging.error(message)

            sys.exit(1)

        return VSPackages(file_format, packages)
