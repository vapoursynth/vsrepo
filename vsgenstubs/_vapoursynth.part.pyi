# Stop pep8 from complaining (hopefully)
# NOQA

# Ignore Flake Warnings
# flake8: noqa

# Ignore coverage
# (No coverage)

# From https://gist.github.com/pylover/7870c235867cf22817ac5b096defb768
# noinspection PyPep8
# noinspection PyPep8Naming
# noinspection PyTypeChecker
# noinspection PyAbstractClass
# noinspection PyArgumentEqualDefault
# noinspection PyArgumentList
# noinspection PyAssignmentToLoopOrWithParameter
# noinspection PyAttributeOutsideInit
# noinspection PyAugmentAssignment
# noinspection PyBroadException
# noinspection PyByteLiteral
# noinspection PyCallByClass
# noinspection PyChainedComparsons
# noinspection PyClassHasNoInit
# noinspection PyClassicStyleClass
# noinspection PyComparisonWithNone
# noinspection PyCompatibility
# noinspection PyDecorator
# noinspection PyDefaultArgument
# noinspection PyDictCreation
# noinspection PyDictDuplicateKeys
# noinspection PyDocstringTypes
# noinspection PyExceptClausesOrder
# noinspection PyExceptionInheritance
# noinspection PyFromFutureImport
# noinspection PyGlobalUndefined
# noinspection PyIncorrectDocstring
# noinspection PyInitNewSignature
# noinspection PyInterpreter
# noinspection PyListCreation
# noinspection PyMandatoryEncoding
# noinspection PyMethodFirstArgAssignment
# noinspection PyMethodMayBeStatic
# noinspection PyMethodOverriding
# noinspection PyMethodParameters
# noinspection PyMissingConstructor
# noinspection PyMissingOrEmptyDocstring
# noinspection PyNestedDecorators
# noinspection PynonAsciiChar
# noinspection PyNoneFunctionAssignment
# noinspection PyOldStyleClasses
# noinspection PyPackageRequirements
# noinspection PyPropertyAccess
# noinspection PyPropertyDefinition
# noinspection PyProtectedMember
# noinspection PyRaisingNewStyleClass
# noinspection PyRedeclaration
# noinspection PyRedundantParentheses
# noinspection PySetFunctionToLiteral
# noinspection PySimplifyBooleanCheck
# noinspection PySingleQuotedDocstring
# noinspection PyStatementEffect
# noinspection PyStringException
# noinspection PyStringFormat
# noinspection PySuperArguments
# noinspection PyTrailingSemicolon
# noinspection PyTupleAssignmentBalance
# noinspection PyTupleItemAssignment
# noinspection PyUnboundLocalVariable
# noinspection PyUnnecessaryBackslash
# noinspection PyUnreachableCode
# noinspection PyUnresolvedReferences
# noinspection PyUnusedLocal
# noinspection ReturnValueFromInit

import fractions
import typing
import ctypes
import types
import enum

from typing import overload


T = typing.TypeVar("T")
SingleAndSequence = typing.Union[T, typing.Sequence[T]]

###
# ENUMS AND CONSTANTS
class ColorFamily(int):
    name: str
    value: int

    GRAY: typing.ClassVar['ColorFamily']
    RGB: typing.ClassVar['ColorFamily']
    YUV: typing.ClassVar['ColorFamily']
    YCOCG: typing.ClassVar['ColorFamily']
    COMPAT: typing.ClassVar['ColorFamily']

GRAY: ColorFamily
RGB: ColorFamily
YUV: ColorFamily
YCOCG: ColorFamily
COMPAT: ColorFamily


class SampleType(int):
    name: str
    value: int

    INTEGER: typing.ClassVar['SampleType']
    FLOAT: typing.ClassVar['SampleType']


INTEGER: SampleType
FLOAT: SampleType


class PresetFormat(int):
    name: str
    value: int

    NONE = typing.ClassVar['PresetFormat']

    GRAY8 = typing.ClassVar['PresetFormat']
    GRAY16 = typing.ClassVar['PresetFormat']

    GRAYH = typing.ClassVar['PresetFormat']
    GRAYS = typing.ClassVar['PresetFormat']

    YUV420P8 = typing.ClassVar['PresetFormat']
    YUV422P8 = typing.ClassVar['PresetFormat']
    YUV444P8 = typing.ClassVar['PresetFormat']
    YUV410P8 = typing.ClassVar['PresetFormat']
    YUV411P8 = typing.ClassVar['PresetFormat']
    YUV440P8 = typing.ClassVar['PresetFormat']

    YUV420P9 = typing.ClassVar['PresetFormat']
    YUV422P9 = typing.ClassVar['PresetFormat']
    YUV444P9 = typing.ClassVar['PresetFormat']

    YUV420P10 = typing.ClassVar['PresetFormat']
    YUV422P10 = typing.ClassVar['PresetFormat']
    YUV444P10 = typing.ClassVar['PresetFormat']
    
    YUV420P12 = typing.ClassVar['PresetFormat']
    YUV422P12 = typing.ClassVar['PresetFormat']
    YUV444P12 = typing.ClassVar['PresetFormat']
    
    YUV420P14 = typing.ClassVar['PresetFormat']
    YUV422P14 = typing.ClassVar['PresetFormat']
    YUV444P14 = typing.ClassVar['PresetFormat']
    
    YUV420P16 = typing.ClassVar['PresetFormat']
    YUV422P16 = typing.ClassVar['PresetFormat']
    YUV444P16 = typing.ClassVar['PresetFormat']

    YUV444PH = typing.ClassVar['PresetFormat']
    YUV444PS = typing.ClassVar['PresetFormat']

    RGB24 = typing.ClassVar['PresetFormat']
    RGB27 = typing.ClassVar['PresetFormat']
    RGB30 = typing.ClassVar['PresetFormat']
    RGB48 = typing.ClassVar['PresetFormat']

    RGBH = typing.ClassVar['PresetFormat']
    RGBS = typing.ClassVar['PresetFormat']

    COMPATBGR32 = typing.ClassVar['PresetFormat']


NONE = PresetFormat

GRAY8 = PresetFormat
GRAY16 = PresetFormat

GRAYH = PresetFormat
GRAYS = PresetFormat

YUV420P8 = PresetFormat
YUV422P8 = PresetFormat
YUV444P8 = PresetFormat
YUV410P8 = PresetFormat
YUV411P8 = PresetFormat
YUV440P8 = PresetFormat

YUV420P9 = PresetFormat
YUV422P9 = PresetFormat
YUV444P9 = PresetFormat

YUV420P10 = PresetFormat
YUV422P10 = PresetFormat
YUV444P10 = PresetFormat

YUV420P12 = PresetFormat
YUV422P12 = PresetFormat
YUV444P12 = PresetFormat

YUV420P14 = PresetFormat
YUV422P14 = PresetFormat
YUV444P14 = PresetFormat

YUV420P16 = PresetFormat
YUV422P16 = PresetFormat
YUV444P16 = PresetFormat

YUV444PH = PresetFormat
YUV444PS = PresetFormat

RGB24 = PresetFormat
RGB27 = PresetFormat
RGB30 = PresetFormat
RGB48 = PresetFormat

RGBH = PresetFormat
RGBS = PresetFormat

COMPATBGR32 = PresetFormat


###
# VapourSynth Environment SubSystem

class EnvironmentData:
    """
    Contains the data VapourSynth stores for a specific environment.
    """


class Environment:
    alive: bool
    single: bool
    env_id: int
    active: bool

    def copy(self) -> Environment: ...
    def use(self) -> typing.ContextManager[None]: ...

    def __enter__(self) -> Environment: ...
    def __exit__(self, ty: typing.Type[BaseException], tv: BaseException, tb: types.TracebackType) -> None: ...

class EnvironmentPolicyAPI:
    def wrap_environment(self, environment_data: EnvironmentData) -> Environment: ...
    def create_environment(self) -> EnvironmentData: ...
    def unregister_policy(self) -> None: ...

class EnvironmentPolicy:
    def on_policy_registered(self, special_api: EnvironmentPolicyAPI) -> None: ...
    def on_policy_cleared(self) -> None: ...
    def get_current_environment(self) -> typing.Optional[EnvironmentData]: ...
    def set_environment(self, environment: typing.Optional[EnvironmentData]) -> None: ...
    def is_active(self, environment: EnvironmentData) -> bool: ...


_using_vsscript: bool


def register_policy(policy: EnvironmentPolicy) -> None: ...
def has_policy() -> None: ...

def vpy_current_environment() -> Environment: ...
def get_current_environment() -> Environment: ...


class AlphaOutputTuple(typing.NamedTuple):
    clip: 'VideoNode'
    alpha: 'VideoNode'

Func = typing.Callable[..., typing.Any]

class Error(Exception): ...

def set_message_handler(handler_func: typing.Callable[[int, str], None]) -> None: ...
def clear_output(index: int = 0) -> None: ...
def clear_outputs() -> None: ...
def get_outputs() -> typing.Mapping[int, typing.Union['VideoNode', AlphaOutputTuple]]: ...
def get_output(index: int = 0) -> typing.Union['VideoNode', AlphaOutputTuple]: ...


class Format:
    id: int
    color_family: ColorFamily
    sample_type: SampleType
    bits_per_sample: int
    bytes_per_sample: int
    subsampling_w: int
    subsampling_h: int
    num_planes: int
    
    def _as_dict(self) -> typing.Dict[str, typing.Any]: ...
    def replace(self, *,
                color_family: typing.Optional[ColorFamily] = None,
                sample_type: typing.Optional[SampleType] = None,
                bits_per_sample: typing.Optional[int] = None,
                subsampling_w: typing.Optional[int] = None,
                subsampling_h: typing.Optional[int] = None
                ) -> 'Format': ...

        
_VideoPropsValue = typing.Union[
    SingleAndSequence[int],
    SingleAndSequence[float],
    SingleAndSequence[str],
    SingleAndSequence['VideoNode'],
    SingleAndSequence['VideoFrame'],
    SingleAndSequence[typing.Callable[..., typing.Any]]
]

class VideoProps(typing.MutableMapping[str, _VideoPropsValue]):
    def __getattr__(self, name: str) -> _VideoPropsValue: ...
    def __setattr__(self, name: str, value: _VideoPropsValue) -> None: ...
    
    # mypy lo vult.
    # In all seriousness, why do I need to manually define them in a typestub?
    def __delitem__(self, name: str) -> None: ...
    def __setitem__(self, name: str, value: _VideoPropsValue) -> None: ...
    def __getitem__(self, name: str) -> _VideoPropsValue: ...
    def __iter__(self) -> typing.Iterator[str]: ...
    def __len__(self) -> int: ...

class VideoPlane:
    width: int
    height: int


class VideoFrame:
    props: VideoProps
    height: int
    width: int
    format: Format
    readonly: bool

    def copy(self) -> 'VideoFrame': ...

    def get_read_ptr(self, plane: int) -> ctypes.c_void_p: ...
    def get_read_array(self, plane: int) -> memoryview: ...
    def get_write_ptr(self, plane: int) -> ctypes.c_void_p: ...
    def get_write_array(self, plane: int) -> memoryview: ...

    def get_stride(self, plane: int) -> int: ...
    def planes(self) -> typing.Iterator['VideoPlane']: ...


class _Future(typing.Generic[T]):
    def set_result(self, value: T) -> None: ...
    def set_exception(self, exception: BaseException) -> None: ...
    def result(self) -> T: ...
    def exception(self) -> typing.Optional[typing.NoReturn]: ...


class Plugin:
    def get_functions(self) -> typing.Dict[str, str]: ...
    def list_functions(self) -> str: ...


#include <plugins/implementations>


class VideoNode:
#include <plugins/bound>

    format: typing.Optional[Format]
    
    fps: fractions.Fraction
    fps_den: int
    fps_num: int
        
    height: int
    width: int
    
    num_frames: int

    def get_frame(self, n: int) -> VideoFrame: ...
    def get_frame_async_raw(self, n: int, cb: _Future[VideoFrame], future_wrapper: typing.Optional[typing.Callable[..., None]]=None) -> _Future[VideoFrame]: ...
    def get_frame_async(self, n: int) -> _Future[VideoFrame]: ...

    def set_output(self, index: int=0, alpha: typing.Optional['VideoNode']=None) -> None: ...
    def output(self, fileobj: typing.BinaryIO, y4m: bool = False, progress_update: typing.Optional[typing.Callable[[int], int]]=None, prefetch: int = 0) -> None: ...

    def frames(self) -> typing.Iterator[VideoFrame]: ...

    def __add__(self, other: 'VideoNode') -> 'VideoNode': ...
    def __mul__(self, other: int) -> 'VideoNode': ...
    def __getitem__(self, other: typing.Union[int, slice]) -> 'VideoNode': ...
    def __len__(self) -> int: ...


class _PluginMeta(typing.TypedDict):
    namespace: str
    identifier: str
    name: str
    functions: typing.Dict[str, str]
        

class Core:
#include <plugins/unbound>

    num_threads: int
    max_cache_size: int
    add_cache: bool

    def set_max_cache_size(self, mb: int) -> int: ...
    def get_plugins(self) -> typing.Dict[str, _PluginMeta]: ...
    def list_functions(self) -> str: ...

    def register_format(self, color_family: ColorFamily, sample_type: SampleType, bits_per_sample: int, subsampling_w: int, subsampling_h: int) -> Format: ...
    def get_format(self, id: int) -> Format: ...

    def version(self) -> str: ...
    def version_number(self) -> int: ...


def get_core(threads: typing.Optional[int]=None, add_cache: typing.Optional[bool]=None) -> Core: ...


class _CoreProxy(Core):
    core: Core
core: _CoreProxy
