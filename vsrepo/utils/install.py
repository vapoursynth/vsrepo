from typing import NamedTuple, Union, overload


class InstallFileResult(NamedTuple):
    success: int = 0
    error: int = 0

    @overload  # type: ignore
    def __add__(self, other: 'InstallFileResult') -> 'InstallFileResult':
        ...

    @overload
    def __add__(self, other: 'InstallPackageResult') -> 'InstallPackageResult':
        ...

    def __add__(
        self, other: 'Union[InstallFileResult, InstallPackageResult]'
    ) -> 'Union[InstallFileResult, InstallPackageResult]':
        return add_result(self, other)

    @overload  # type: ignore
    def __iadd__(self, other: 'InstallFileResult') -> 'InstallFileResult':
        ...

    @overload
    def __iadd__(self, other: 'InstallPackageResult') -> 'InstallPackageResult':
        ...

    def __iadd__(  # type: ignore
        self, other: 'Union[InstallFileResult, InstallPackageResult]'
    ) -> 'Union[InstallFileResult, InstallPackageResult]':
        return add_result(self, other)


class InstallPackageResult(NamedTuple):
    success: int = 0
    success_dependecies: int = 0
    error: int = 0

    def __add__(  # type: ignore[override]
        self, other: 'Union[InstallFileResult, InstallPackageResult]'
    ) -> 'InstallPackageResult':
        return add_result(self, other)

    def __iadd__(  # type: ignore[override]
        self, other: 'Union[InstallFileResult, InstallPackageResult]'
    ) -> 'InstallPackageResult':
        return add_result(self, other)


@overload
def add_result(
    self: InstallPackageResult, other: Union[InstallFileResult, InstallPackageResult]
) -> InstallPackageResult:
    ...


@overload
def add_result(
    self: Union[InstallFileResult, InstallPackageResult], other: InstallPackageResult
) -> InstallPackageResult:
    ...


@overload
def add_result(
    self: Union[InstallFileResult, InstallPackageResult], other: Union[InstallFileResult, InstallPackageResult]
) -> Union[InstallFileResult, InstallPackageResult]:
    ...


def add_result(
    self: Union[InstallFileResult, InstallPackageResult], other: Union[InstallFileResult, InstallPackageResult]
) -> Union[InstallFileResult, InstallPackageResult]:
    if isinstance(other, InstallPackageResult):
        deps = other.success_dependecies

        if isinstance(self, InstallPackageResult):
            deps += self.success_dependecies

        return InstallPackageResult(self.error + other.success, deps, self.error + other.error)

    if isinstance(self, InstallFileResult):
        return InstallFileResult(
            self.success + other.success, self.error + other.error
        )

    return add_result(other, self)
