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

from __future__ import annotations

import ctypes
import enum
import fractions
import inspect
import types
import typing

T = typing.TypeVar("T")
SingleAndSequence = typing.Union[T, typing.Sequence[T]]


###
# ENUMS AND CONSTANTS
class MediaType(enum.IntEnum):
    VIDEO: MediaType
    AUDIO: MediaType


VIDEO: MediaType
AUDIO: MediaType


class ColorFamily(enum.IntEnum):
    GRAY: ColorFamily
    RGB: ColorFamily
    YUV: ColorFamily


GRAY: ColorFamily
RGB: ColorFamily
YUV: ColorFamily


class SampleType(enum.IntEnum):
    INTEGER: SampleType
    FLOAT: SampleType


INTEGER: SampleType
FLOAT: SampleType


class PresetFormat(enum.IntEnum):
    NONE: PresetFormat

    GRAY8: PresetFormat
    GRAY9: PresetFormat
    GRAY10: PresetFormat
    GRAY12: PresetFormat
    GRAY14: PresetFormat
    GRAY16: PresetFormat
    GRAY32: PresetFormat

    GRAYH: PresetFormat
    GRAYS: PresetFormat

    YUV420P8: PresetFormat
    YUV422P8: PresetFormat
    YUV444P8: PresetFormat
    YUV410P8: PresetFormat
    YUV411P8: PresetFormat
    YUV440P8: PresetFormat

    YUV420P9: PresetFormat
    YUV422P9: PresetFormat
    YUV444P9: PresetFormat

    YUV420P10: PresetFormat
    YUV422P10: PresetFormat
    YUV444P10: PresetFormat

    YUV420P12: PresetFormat
    YUV422P12: PresetFormat
    YUV444P12: PresetFormat

    YUV420P14: PresetFormat
    YUV422P14: PresetFormat
    YUV444P14: PresetFormat

    YUV420P16: PresetFormat
    YUV422P16: PresetFormat
    YUV444P16: PresetFormat

    YUV444PH: PresetFormat
    YUV444PS: PresetFormat

    RGB24: PresetFormat
    RGB27: PresetFormat
    RGB30: PresetFormat
    RGB36: PresetFormat
    RGB42: PresetFormat
    RGB48: PresetFormat

    RGBH: PresetFormat
    RGBS: PresetFormat


NONE: PresetFormat

GRAY8: PresetFormat
GRAY9: PresetFormat
GRAY10: PresetFormat
GRAY12: PresetFormat
GRAY14: PresetFormat
GRAY16: PresetFormat
GRAY32: PresetFormat

GRAYH: PresetFormat
GRAYS: PresetFormat

YUV420P8: PresetFormat
YUV422P8: PresetFormat
YUV444P8: PresetFormat
YUV410P8: PresetFormat
YUV411P8: PresetFormat
YUV440P8: PresetFormat

YUV420P9: PresetFormat
YUV422P9: PresetFormat
YUV444P9: PresetFormat

YUV420P10: PresetFormat
YUV422P10: PresetFormat
YUV444P10: PresetFormat

YUV420P12: PresetFormat
YUV422P12: PresetFormat
YUV444P12: PresetFormat

YUV420P14: PresetFormat
YUV422P14: PresetFormat
YUV444P14: PresetFormat

YUV420P16: PresetFormat
YUV422P16: PresetFormat
YUV444P16: PresetFormat

YUV444PH: PresetFormat
YUV444PS: PresetFormat

RGB24: PresetFormat
RGB27: PresetFormat
RGB30: PresetFormat
RGB36: PresetFormat
RGB42: PresetFormat
RGB48: PresetFormat

RGBH: PresetFormat
RGBS: PresetFormat


class AudioChannels(enum.IntEnum):
    FRONT_LEFT: AudioChannels
    FRONT_RIGHT: AudioChannels
    FRONT_CENTER: AudioChannels
    LOW_FREQUENCY: AudioChannels
    BACK_LEFT: AudioChannels
    BACK_RIGHT: AudioChannels
    FRONT_LEFT_OF_CENTER: AudioChannels
    FRONT_RIGHT_OF_CENTER: AudioChannels
    BACK_CENTER: AudioChannels
    SIDE_LEFT: AudioChannels
    SIDE_RIGHT: AudioChannels
    TOP_CENTER: AudioChannels
    TOP_FRONT_LEFT: AudioChannels
    TOP_FRONT_CENTER: AudioChannels
    TOP_FRONT_RIGHT: AudioChannels
    TOP_BACK_LEFT: AudioChannels
    TOP_BACK_CENTER: AudioChannels
    TOP_BACK_RIGHT: AudioChannels
    STEREO_LEFT: AudioChannels
    STEREO_RIGHT: AudioChannels
    WIDE_LEFT: AudioChannels
    WIDE_RIGHT: AudioChannels
    SURROUND_DIRECT_LEFT: AudioChannels
    SURROUND_DIRECT_RIGHT: AudioChannels
    LOW_FREQUENCY2: AudioChannels


FRONT_LEFT: AudioChannels
FRONT_RIGHT: AudioChannels
FRONT_CENTER: AudioChannels
LOW_FREQUENCY: AudioChannels
BACK_LEFT: AudioChannels
BACK_RIGHT: AudioChannels
FRONT_LEFT_OF_CENTER: AudioChannels
FRONT_RIGHT_OF_CENTER: AudioChannels
BACK_CENTER: AudioChannels
SIDE_LEFT: AudioChannels
SIDE_RIGHT: AudioChannels
TOP_CENTER: AudioChannels
TOP_FRONT_LEFT: AudioChannels
TOP_FRONT_CENTER: AudioChannels
TOP_FRONT_RIGHT: AudioChannels
TOP_BACK_LEFT: AudioChannels
TOP_BACK_CENTER: AudioChannels
TOP_BACK_RIGHT: AudioChannels
STEREO_LEFT: AudioChannels
STEREO_RIGHT: AudioChannels
WIDE_LEFT: AudioChannels
WIDE_RIGHT: AudioChannels
SURROUND_DIRECT_LEFT: AudioChannels
SURROUND_DIRECT_RIGHT: AudioChannels
LOW_FREQUENCY2: AudioChannels


class MessageType(enum.IntEnum):
    MESSAGE_TYPE_DEBUG: MessageType
    MESSAGE_TYPE_INFORMATION: MessageType
    MESSAGE_TYPE_WARNING: MessageType
    MESSAGE_TYPE_CRITICAL: MessageType
    MESSAGE_TYPE_FATAL: MessageType


MESSAGE_TYPE_DEBUG: MessageType
MESSAGE_TYPE_INFORMATION: MessageType
MESSAGE_TYPE_WARNING: MessageType
MESSAGE_TYPE_CRITICAL: MessageType
MESSAGE_TYPE_FATAL: MessageType


class VapourSynthVersion(typing.NamedTuple):
    release_major: int
    release_minor: int


__version__: VapourSynthVersion


class VapourSynthAPIVersion(typing.NamedTuple):
    api_major: int
    api_minor: int


__api_version__: VapourSynthAPIVersion


class ColorRange(enum.IntEnum):
    RANGE_FULL: ColorRange
    RANGE_LIMITED: ColorRange


RANGE_FULL: ColorRange
RANGE_LIMITED: ColorRange


class ChromaLocation(enum.IntEnum):
    CHROMA_LEFT: ChromaLocation
    CHROMA_CENTER: ChromaLocation
    CHROMA_TOP_LEFT: ChromaLocation
    CHROMA_TOP: ChromaLocation
    CHROMA_BOTTOM_LEFT: ChromaLocation
    CHROMA_BOTTOM: ChromaLocation


CHROMA_LEFT: ChromaLocation
CHROMA_CENTER: ChromaLocation
CHROMA_TOP_LEFT: ChromaLocation
CHROMA_TOP: ChromaLocation
CHROMA_BOTTOM_LEFT: ChromaLocation
CHROMA_BOTTOM: ChromaLocation


class FieldBased(enum.IntEnum):
    FIELD_PROGRESSIVE: FieldBased
    FIELD_TOP: FieldBased
    FIELD_BOTTOM: FieldBased


FIELD_PROGRESSIVE: FieldBased
FIELD_TOP: FieldBased
FIELD_BOTTOM: FieldBased


class MatrixCoefficients(enum.IntEnum):
    MATRIX_RGB: MatrixCoefficients
    MATRIX_BT709: MatrixCoefficients
    MATRIX_UNSPECIFIED: MatrixCoefficients
    MATRIX_FCC: MatrixCoefficients
    MATRIX_BT470_BG: MatrixCoefficients
    MATRIX_ST170_M: MatrixCoefficients
    MATRIX_YCGCO: MatrixCoefficients
    MATRIX_BT2020_NCL: MatrixCoefficients
    MATRIX_BT2020_CL: MatrixCoefficients
    MATRIX_CHROMATICITY_DERIVED_NCL: MatrixCoefficients
    MATRIX_CHROMATICITY_DERIVED_CL: MatrixCoefficients
    MATRIX_ICTCP: MatrixCoefficients


MATRIX_RGB: MatrixCoefficients
MATRIX_BT709: MatrixCoefficients
MATRIX_UNSPECIFIED: MatrixCoefficients
MATRIX_FCC: MatrixCoefficients
MATRIX_BT470_BG: MatrixCoefficients
MATRIX_ST170_M: MatrixCoefficients
MATRIX_YCGCO: MatrixCoefficients
MATRIX_BT2020_NCL: MatrixCoefficients
MATRIX_BT2020_CL: MatrixCoefficients
MATRIX_CHROMATICITY_DERIVED_NCL: MatrixCoefficients
MATRIX_CHROMATICITY_DERIVED_CL: MatrixCoefficients
MATRIX_ICTCP: MatrixCoefficients


class TransferCharacteristics(enum.IntEnum):
    TRANSFER_BT709: TransferCharacteristics
    TRANSFER_UNSPECIFIED: TransferCharacteristics
    TRANSFER_BT470_M: TransferCharacteristics
    TRANSFER_BT470_BG: TransferCharacteristics
    TRANSFER_BT601: TransferCharacteristics
    TRANSFER_ST240_M: TransferCharacteristics
    TRANSFER_LINEAR: TransferCharacteristics
    TRANSFER_LOG_100: TransferCharacteristics
    TRANSFER_LOG_316: TransferCharacteristics
    TRANSFER_IEC_61966_2_4: TransferCharacteristics
    TRANSFER_IEC_61966_2_1: TransferCharacteristics
    TRANSFER_BT2020_10: TransferCharacteristics
    TRANSFER_BT2020_12: TransferCharacteristics
    TRANSFER_ST2084: TransferCharacteristics
    TRANSFER_ARIB_B67: TransferCharacteristics


TRANSFER_BT709: TransferCharacteristics
TRANSFER_UNSPECIFIED: TransferCharacteristics
TRANSFER_BT470_M: TransferCharacteristics
TRANSFER_BT470_BG: TransferCharacteristics
TRANSFER_BT601: TransferCharacteristics
TRANSFER_ST240_M: TransferCharacteristics
TRANSFER_LINEAR: TransferCharacteristics
TRANSFER_LOG_100: TransferCharacteristics
TRANSFER_LOG_316: TransferCharacteristics
TRANSFER_IEC_61966_2_4: TransferCharacteristics
TRANSFER_IEC_61966_2_1: TransferCharacteristics
TRANSFER_BT2020_10: TransferCharacteristics
TRANSFER_BT2020_12: TransferCharacteristics
TRANSFER_ST2084: TransferCharacteristics
TRANSFER_ARIB_B67: TransferCharacteristics


class ColorPrimaries(enum.IntEnum):
    PRIMARIES_BT709: ColorPrimaries
    PRIMARIES_UNSPECIFIED: ColorPrimaries
    PRIMARIES_BT470_M: ColorPrimaries
    PRIMARIES_BT470_BG: ColorPrimaries
    PRIMARIES_ST170_M: ColorPrimaries
    PRIMARIES_ST240_M: ColorPrimaries
    PRIMARIES_FILM: ColorPrimaries
    PRIMARIES_BT2020: ColorPrimaries
    PRIMARIES_ST428: ColorPrimaries
    PRIMARIES_ST431_2: ColorPrimaries
    PRIMARIES_ST432_1: ColorPrimaries
    PRIMARIES_EBU3213_E: ColorPrimaries


PRIMARIES_BT709: ColorPrimaries
PRIMARIES_UNSPECIFIED: ColorPrimaries
PRIMARIES_BT470_M: ColorPrimaries
PRIMARIES_BT470_BG: ColorPrimaries
PRIMARIES_ST170_M: ColorPrimaries
PRIMARIES_ST240_M: ColorPrimaries
PRIMARIES_FILM: ColorPrimaries
PRIMARIES_BT2020: ColorPrimaries
PRIMARIES_ST428: ColorPrimaries
PRIMARIES_ST431_2: ColorPrimaries
PRIMARIES_ST432_1: ColorPrimaries
PRIMARIES_EBU3213_E: ColorPrimaries


class FilterMode(enum.IntEnum):
    fmParallel: FilterMode
    fmParallelRequests: FilterMode
    fmUnordered: FilterMode
    fmFrameState: FilterMode


fmParallel: FilterMode
fmParallelRequests: FilterMode
fmUnordered: FilterMode
fmFrameState: FilterMode


###
# VapourSynth Environment SubSystem
class EnvironmentData:
    """
    Contains the data VapourSynth stores for a specific environment.
    """


class Environment:
    @property
    def alive(self) -> bool: ...
    @property
    def single(self) -> bool: ...
    @property
    def env_id(self) -> int: ...
    @property
    def active(self) -> bool: ...
    @property
    def env(self) -> EnvironmentData: ...
    @property
    def env_id(self) -> int: ...
    @classmethod
    def is_single(cls) -> bool: ...
    def copy(self) -> Environment: ...
    def use(self) -> typing.ContextManager[None]: ...

    def __enter__(self) -> Environment: ...

    def __exit__(
        self, ty: typing.Type[BaseException] | None, tv: BaseException | None, tb: types.TracebackTyp | None
    ) -> None: ...


class EnvironmentPolicyAPI:
    def wrap_environment(self, environment_data: EnvironmentData) -> Environment: ...
    def create_environment(self, flags: int = 0) -> EnvironmentData: ...
    def set_logger(self, env: Environment, logger: typing.Callable[[int, str], None]) -> None: ...
    def destroy_environment(self, env: EnvironmentData) -> None: ...
    def unregister_policy(self) -> None: ...


class EnvironmentPolicy:
    def on_policy_registered(self, special_api: EnvironmentPolicyAPI) -> None: ...
    def on_policy_cleared(self) -> None: ...
    def get_current_environment(self) -> EnvironmentData | None: ...
    def set_environment(self, environment: EnvironmentData | None) -> None: ...
    def is_active(self, environment: EnvironmentData) -> bool: ...


def register_policy(policy: EnvironmentPolicy) -> None: ...
def has_policy() -> bool: ...


def get_current_environment() -> Environment: ...


def construct_signature(
    signature: str, return_signature: str, injected: str | None = None
) -> inspect.Signature: ...


class VideoOutputTuple(typing.NamedTuple):
    clip: VideoNode
    alpha: VideoNode | None
    alt_output: int


class Error(Exception):
    ...


def set_message_handler(handler_func: typing.Callable[[int, str], None]) -> None: ...
def clear_output(index: int = 0) -> None: ...
def clear_outputs() -> None: ...
def get_outputs() -> types.MappingProxyType[int, VideoOutputTuple | AudioNode]: ...
def get_output(index: int = 0) -> VideoOutputTuple | AudioNode: ...


class VideoFormat:
    id: int
    name: str
    color_family: ColorFamily
    sample_type: SampleType
    bits_per_sample: int
    bytes_per_sample: int
    subsampling_w: int
    subsampling_h: int
    num_planes: int

    def __int__(self) -> int: ...

    def _as_dict(self) -> typing.Dict[str, typing.Any]: ...

    def replace(
        self, *,
        color_family: ColorFamily | None = None,
        sample_type: SampleType | None = None,
        bits_per_sample: int | None = None,
        subsampling_w: int | None = None,
        subsampling_h: int | None = None
    ) -> VideoFormat: ...


_FramePropsValue = typing.Union[
    SingleAndSequence[int],
    SingleAndSequence[float],
    SingleAndSequence[str],
    SingleAndSequence[VideoNode],
    SingleAndSequence[VideoFrame],
    SingleAndSequence[AudioNode],
    SingleAndSequence[AudioFrame],
    SingleAndSequence[typing.Callable[..., typing.Any]]
]


class FrameProps(typing.MutableMapping[str, _FramePropsValue]):

    def copy(self) -> typing.Dict[str, _FramePropsValue]: ...

    def __getattr__(self, name: str) -> _FramePropsValue: ...
    def __setattr__(self, name: str, value: _FramePropsValue) -> None: ...

    # mypy lo vult.
    # In all seriousness, why do I need to manually define them in a typestub?
    def __delitem__(self, name: str) -> None: ...
    def __setitem__(self, name: str, value: _FramePropsValue) -> None: ...
    def __getitem__(self, name: str) -> _FramePropsValue: ...
    def __iter__(self) -> typing.Iterator[str]: ...
    def __len__(self) -> int: ...


RawFrameType = typing.TypeVar('RawFrameType', VideoFrame, AudioFrame)


class _RawFrame(typing.Generic[RawFrameType]):
    @property
    def readonly(self) -> bool: ...

    @property
    def props(self) -> FrameProps: ...

    def get_read_ptr(self, plane: int) -> ctypes.c_void_p: ...
    def get_write_ptr(self, plane: int) -> ctypes.c_void_p: ...
    def get_stride(self, plane: int) -> int: ...

    @property
    def closed(self) -> bool: ...

    def close(self) -> None: ...

    def copy(self) -> RawFrameType: ...

    def __enter__(self) -> RawFrameType: ...

    def __exit__(
        self, ty: typing.Type[BaseException] | None, tv: BaseException | None, tb: types.TracebackType | None
    ) -> None: ...

    def __getitem__(self, index: int) -> memoryview: ...
    def __len__(self) -> int: ...


class VideoFrame(_RawFrame[VideoFrame]):
    height: int
    width: int
    format: VideoFormat

    def _writelines(self, write: typing.Callable[[memoryview], None]) -> None: ...


class AudioFrame(_RawFrame[AudioFrame]):
    sample_type: SampleType
    bits_per_sample: int
    bytes_per_sample: int
    channel_layout: int
    num_channels: int


class _Future(typing.Generic[T]):
    def set_result(self, value: T) -> None: ...
    def set_exception(self, exception: BaseException) -> None: ...
    def result(self) -> T: ...
    def exception(self) -> typing.NoReturn | None: ...


Func = typing.Callable[..., typing.Any]


class Plugin:
    identifier: str
    namespace: str
    name: str

    def functions(self) -> typing.Iterator[Function]: ...


class Function:
    plugin: Plugin
    name: str
    signature: str
    return_signature: str

    @property
    def __signature__(self) -> inspect.Signature: ...
    def __call__(self, *args: typing.Any, **kwargs: typing.Any) -> typing.Any: ...


#include <plugins/implementations>

RawNodeType = typing.TypeVar('RawNodeType', VideoNode, AudioNode)


class _RawNode(typing.Generic[RawNodeType], typing.Generic[RawFrameType]):
    num_frames: int

    def get_frame_async(self, n: int) -> _Future[RawFrameType]: ...
    def frames(
        self, prefetch: int | None = None, backlog: int | None = None, close: bool = False
    ) -> typing.Iterator[RawFrameType]: ...

    def get_frame(self, n: int) -> RawFrameType: ...

    # Inspect API
    def is_inspectable(self, version: int | None = None) -> bool: ...
    @property
    def _node_name(self) -> str: ...
    @property
    def _inputs(self) -> typing.Dict[str, str]: ...
    @property
    def _mode(self) -> FilterMode: ...
    @property
    def _dependencies(self) -> typing.Tuple[VideoNode, ...]: ...

    def __add__(self, other: RawNodeType) -> RawNodeType: ...
    def __radd__(self, other: RawNodeType) -> RawNodeType: ...
    def __mul__(self, other: int) -> RawNodeType: ...
    def __rmul__(self, other: int) -> RawNodeType: ...
    def __getitem__(self, other: int | slice) -> RawNodeType: ...
    def __len__(self) -> int: ...


class VideoNode(_RawNode[VideoNode, VideoFrame]):
#include <plugins_vnode/bound>

    format: VideoFormat | None

    fps: fractions.Fraction
    fps_den: int
    fps_num: int

    height: int
    width: int

    def set_output(self, index: int = 0, alpha: VideoNode | None = None, alt_output: int = 0) -> None: ...
    def output(
        self,
        fileobj: typing.BinaryIO, y4m: bool = False,
        progress_update: typing.Callable[[int, int], None] | None = None,
        prefetch: int = 0, backlog: int = -1
    ) -> None: ...


class AudioNode(_RawNode[AudioNode, AudioFrame]):
#include <plugins_anode/bound>

    sample_type: SampleType
    bits_per_sample: int
    bytes_per_sample: int
    channel_layout: int
    num_channels: int
    sample_rate: int
    num_samples: int

    def set_output(self, index: int = 0) -> None: ...


class _PluginMeta(typing.TypedDict):
    namespace: str
    identifier: str
    name: str
    functions: typing.Dict[str, str]


class LogHandle:
    handler_func: typing.Callable[[MessageType, str], None]


class Core:
#include <plugins/unbound>

    flags: int

    @property
    def num_threads(self) -> int: ...
    @num_threads.setter
    def num_threads(self) -> None: ...
    @property
    def max_cache_size(self) -> int: ...
    @max_cache_size.setter
    def max_cache_size(self) -> None: ...

    def plugins(self) -> typing.Iterator[Plugin]: ...

    def query_video_format(
        self,
        color_family: ColorFamily,
        sample_type: SampleType,
        bits_per_sample: int,
        subsampling_w: int = 0,
        subsampling_h: int = 0
    ) -> VideoFormat: ...

    def get_video_format(self, id: int | VideoFormat | PresetFormat) -> VideoFormat: ...
    def log_message(self, message_type: MessageType, message: str) -> None: ...
    def add_log_handler(self, handler_func: typing.Callable[[MessageType, str], None] | None) -> LogHandle: ...

    def remove_log_handler(self, handle: LogHandle) -> None: ...

    def version(self) -> str: ...
    def version_number(self) -> int: ...


class _CoreProxy(Core):
    @property
    def core(self) -> Core: ...


core: _CoreProxy
