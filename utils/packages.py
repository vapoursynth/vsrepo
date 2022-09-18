from typing import Dict, Literal, Optional, overload

from .site import InstallationInfo
from .types import VSPackage, VSPackageRel, VSPackages


class InstalledPackages(Dict[str, str]):
    def __init__(self, info: InstallationInfo, packages: VSPackages) -> None:
        self.info = info
        self.packages = packages

    @overload
    def get_package_from_id(self, id: str, required: Literal[True]) -> VSPackage[VSPackageRel]:
        ...

    @overload
    def get_package_from_id(self, id: str, required: bool = False) -> Optional[VSPackage[VSPackageRel]]:
        ...

    def get_package_from_id(self, id: str, required: bool = False) -> Optional[VSPackage[VSPackageRel]]:
        for p in self.packages:
            if p.identifier == id:
                return p

        if required:
            raise ValueError(f'No package with the identifier {id} found')

        return None

    @overload
    def get_package_from_plugin_name(self, name: str, required: Literal[True]) -> VSPackage[VSPackageRel]:
        ...

    @overload
    def get_package_from_plugin_name(self, name: str, required: bool = False) -> Optional[VSPackage[VSPackageRel]]:
        ...

    def get_package_from_plugin_name(self, name: str, required: bool = False) -> Optional[VSPackage[VSPackageRel]]:
        for p in self.packages:
            if p.name.casefold() == name.casefold():
                return p

        if required:
            raise ValueError(f'No package with the name {name} found')

        return None

    @overload
    def get_package_from_namespace(self, namespace: str, required: Literal[True]) -> VSPackage[VSPackageRel]:
        ...

    @overload
    def get_package_from_namespace(self, namespace: str, required: bool = False) -> Optional[VSPackage[VSPackageRel]]:
        ...

    def get_package_from_namespace(self, namespace: str, required: bool = False) -> Optional[VSPackage[VSPackageRel]]:
        for p in self.packages:
            if p.namespace == namespace:
                return p

        if required:
            raise ValueError(f'No package with the namespace {namespace} found')

        return None

    @overload
    def get_package_from_modulename(self, modulename: str, required: Literal[True]) -> VSPackage[VSPackageRel]:
        ...

    @overload
    def get_package_from_modulename(self, modulename: str, required: bool = False) -> Optional[VSPackage[VSPackageRel]]:
        ...

    def get_package_from_modulename(self, modulename: str, required: bool = False) -> Optional[VSPackage[VSPackageRel]]:
        for p in self.packages:
            if p.modulename == modulename:
                return p

        if required:
            raise ValueError(f'No package with the modulename {modulename} found')

        return None

    def get_package_from_name(self, name: str) -> VSPackage[VSPackageRel]:
        p = self.get_package_from_id(name)

        if p is None:
            p = self.get_package_from_namespace(name)

        if p is None:
            p = self.get_package_from_modulename(name)

        if p is None:
            p = self.get_package_from_plugin_name(name)

        if p is None:
            raise ValueError(f'Package {name} not found')

        return p

    def is_package_installed(self, id: str) -> bool:
        return id in self

    def is_package_upgradable(self, id: str, force: bool) -> bool:
        pkg = self.get_package_from_id(id, True)

        lastest_installable = pkg.get_latest_installable_release()

        if force:
            return (
                self.is_package_installed(id)
                and (lastest_installable is not None)
                and (self[id] != lastest_installable.version)
            )

        return (
            self.is_package_installed(id)
            and (lastest_installable is not None)
            and (self[id] != 'Unknown')
            and (self[id] != lastest_installable.version)
        )
