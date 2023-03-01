import re
import sys
from abc import abstractmethod
from argparse import ArgumentParser, Namespace
from inspect import Parameter, Signature
from itertools import chain
from keyword import kwlist as reserved_keywords
from os import SEEK_END, listdir, makedirs, path
from os.path import join as join_path
from pathlib import Path
from typing import (
    Any, Callable, Dict, Iterable, Iterator, List, NamedTuple, Optional, Protocol, Sequence, Tuple, TypeVar, Union,
    cast, runtime_checkable
)

import vapoursynth as vs

__all__ = [
    'main'
]

T = TypeVar('T')
CoreLike = Union[vs.Core, vs.RawNode]

SingleAndSequence = Union[T, Sequence[T]]


@runtime_checkable
class SupportsString(Protocol):
    @abstractmethod
    def __str__(self) -> str:
        ...


DataType = Union[str, bytes, bytearray, SupportsString]

_VapourSynthMapValue = Union[
    SingleAndSequence[int],
    SingleAndSequence[float],
    SingleAndSequence[DataType],
    SingleAndSequence[vs.VideoNode],
    SingleAndSequence[vs.VideoFrame],
    SingleAndSequence[vs.AudioNode],
    SingleAndSequence[vs.AudioFrame],
    SingleAndSequence['VSMapValueCallback[Any]']
]

BoundVSMapValue = TypeVar('BoundVSMapValue', bound=_VapourSynthMapValue)

VSMapValueCallback = Callable[..., BoundVSMapValue]


vs_value_type = '_VapourSynthMapValue'
site_package_dirname = 'vapoursynth-stubs'

parser = ArgumentParser()
parser.add_argument(
    "plugins",
    type=str, nargs="*",
    help="Only generate stubs for and inject specified plugin namespaces, "
    "append these if the stubs file already exists."
)
parser.add_argument(
    "--exclude-plugin", "-r",
    metavar="VS_EXCL_PLUGIN", action="append", help="Remove selected plugin from new stubs, "
    "or remove from existing stubs."
)
parser.add_argument(
    "--load-plugin", "-p",
    metavar="VS_PLUGIN", action="append", help="Load non-auto-loaded VapourSynth plugin."
)
parser.add_argument(
    '--avs-plugin', action='append', help='Manually load AviSynth plugin.'
)
parser.add_argument(
    '--output', '-o', default='@',
    help="Where to output the file. Can be a full file path or directory."
    "The special value '-' means output to stdout. "
    "The spcial value '@' will install it as a stub-package inside site-packages."
)
parser.add_argument(
    '--pyi-template',
    default=join_path(path.dirname(__file__), '_vapoursynth.part.pyi'),
    help='Don\'t use unless you know what you are doing.'
)
parser.add_argument(
    '--force', '-f',
    action='store_true',
    help='Force rewrite of the file.'
)


def indent(strings: Iterable[str], spaces: int = 4) -> str:
    return '\n'.join(' ' * spaces + line for line in strings)


anonymous_signature = Signature(
    [
        Parameter('args', Parameter.VAR_POSITIONAL, annotation=vs_value_type),
        Parameter('kwargs', Parameter.VAR_KEYWORD, annotation=vs_value_type)
    ],
    return_annotation=vs.VideoNode
)

sig_excepted_errors_list = [TypeError, ValueError]

if vs.__version__[0] < 60:
    sig_excepted_errors_list.append(IndexError)
    # it tried to delete the bound value even if the signature didn't have any
    # eg Version functions, their plugin is bound but the function hasn't got any params
    # https://github.com/vapoursynth/vapoursynth/pull/898


sig_excepted_errors = tuple(sig_excepted_errors_list)

types = {
    'int', 'float', 'DataType',
    'RawNode',
    'VideoNode', 'AudioNode',
    'RawFrame',
    'VideoFrame', 'AudioFrame'
}


def load_plugins(args: Namespace) -> vs.Core:
    def _check_plugin(path: str) -> str:
        pathl = Path(path).absolute()

        if not pathl.exists():
            raise ValueError(f'Plugin "{path}" was not found!')

        return str(pathl)

    if args.load_plugin:
        for plugin in args.load_plugin:
            vs.core.std.LoadPlugin(_check_plugin(plugin))

    if args.avs_plugin:
        if hasattr(vs.core, 'avs'):
            for plugin in args.avs_plugin:
                vs.core.avs.LoadPlugin(_check_plugin(plugin))
        else:
            raise AttributeError('Core is missing avs plugin!')

    return vs.core.core


def retrieve_func_sigs(core: Union[vs.Core, vs.RawNode], namespace: str) -> Iterator[str]:
    plugin = cast(vs.Plugin, getattr(core, namespace))

    ordered_functions = sorted(plugin.functions(), key=lambda x: x.name.lower())

    for func in ordered_functions:
        signature_base = anonymous_signature

        if func.name in dir(plugin):
            try:
                signature_base = Signature.from_callable(
                    cast(vs.Function, getattr(plugin, func.name)), follow_wrapped=True
                )
            except sig_excepted_errors:
                if isinstance(core, vs.RawNode):
                    signature_base.replace(return_annotation=core.__class__)

            if signature_base.return_annotation in {Any, Optional[Any]}:
                signature_base = signature_base.replace(return_annotation=vs.VideoNode)

            signature = str(signature_base)

            # Clean up the type annotations so that they are valid python syntax.
            signature = signature.replace('vapoursynth.', '').replace('vs.', '')
            signature = signature.replace('VideoNode', "'VideoNode'").replace('VideoFrame', "'VideoFrame'")
            signature = signature.replace('AudioNode', "'AudioNode'").replace('AudioFrame', "'AudioFrame'")
            signature = signature.replace('NoneType', 'None')
            signature = signature.replace('str, bytes, bytearray', 'DataType')

            for t in types:
                for t_ in {t, f"'{t}'"}:
                    signature = signature.replace(f'Union[{t_}]', f'{t_}')
                    signature = signature.replace(f'Union[{t_}, None]', f'Optional[{t_}]')
                    signature = signature.replace(f'Union[{t_}, Sequence[{t_}]]', f'SingleAndSequence[{t_}]')
                    signature = signature.replace(
                        f'Union[{t_}, Sequence[{t_}], None]', f'Optional[SingleAndSequence[{t}]]'
                    )

            callback_type = 'VSMapValueCallback[_VapourSynthMapValue]'

            # Make Callable definitions sensible
            signature = signature.replace('Union[Func, Callable]', callback_type)
            signature = signature.replace('Union[Func, Callable, None]', f'Optional[{callback_type}]')

            # Replace the keywords with valid values
            for kw in reserved_keywords:
                signature = signature.replace(f' {kw}:', f' {kw}_:')

            # Remove anonymous Anys
            signature = signature.replace(' **kwargs: Any', f' **kwargs: {vs_value_type}')

            # Add a self.
            signature = signature.replace('(', '(self, ').replace(', )', ')')

            yield f'    def {func.name}{signature}: ...'


class BoundSignature:
    def __init__(self, namespace: str, cores: Iterable[CoreLike]) -> None:
        self.namespace = namespace
        self.cores = cores

    def __iter__(self) -> Iterator[Tuple[str, Iterator[str]]]:
        for core in self.cores:
            signatures = retrieve_func_sigs(core, self.namespace)

            try:
                signature = next(signatures)
            except StopIteration:
                continue

            yield core.__class__.__name__, chain.from_iterable(([signature], signatures))


class PluginMeta(NamedTuple):
    name: str
    description: str
    bound: BoundSignature

    @classmethod
    def from_namespace(cls, namespace: str, cores: Sequence[CoreLike]) -> 'PluginMeta':
        try:
            plugin = cast(vs.Plugin, getattr(cores[0], namespace))
        except BaseException:
            raise ValueError(f'Invalid namespace! Plugin not found: "{namespace}"')

        return PluginMeta(
            plugin.namespace, plugin.name, BoundSignature(plugin.namespace, cores)
        )

    def _str_(self, kind: str, __x: Tuple[object, ...]) -> bool:
        return getattr(str, kind)(self.name.lower(), str(__x[0]).lower())

    def __gt__(self, x: 'PluginMeta', /) -> bool: return self._str_('__gt__', x)  # type: ignore[override]
    def __lt__(self, x: 'PluginMeta', /) -> bool: return self._str_('__lt__', x)  # type: ignore[override]
    def __ge__(self, x: 'PluginMeta', /) -> bool: return self._str_('__ge__', x)  # type: ignore[override]
    def __le__(self, x: 'PluginMeta', /) -> bool: return self._str_('__le__', x)  # type: ignore[override]
    def __eq__(self, x: 'PluginMeta', /) -> bool: return self._str_('__eq__', x)  # type: ignore[override]
    def __ne__(self, x: 'PluginMeta', /) -> bool: return self._str_('__ne__', x)  # type: ignore[override]


def retrieve_plugins(
    args: Namespace, core: vs.Core, cores: Iterable[CoreLike]
) -> Iterator[PluginMeta]:
    lower_plugins = list(map(str.lower, args.plugins)) if args.plugins else []

    if lower_plugins:
        find_plugins = lower_plugins.copy()

        for p in core.plugins():
            ns_lower = p.namespace.lower()

            if ns_lower in find_plugins:
                find_plugins.remove(ns_lower)

        if find_plugins:
            missing_plugins = ', '.join(find_plugins)

            raise ModuleNotFoundError(
                'Can\'t generate stubs for specific plugins, these are missing in your installation:'
                f'\n\t"{missing_plugins}"'
            )

    for p in core.plugins():
        if lower_plugins and (p.namespace.lower() not in lower_plugins):
            continue

        yield PluginMeta(p.namespace, p.name, BoundSignature(p.namespace, cores))


implementation_start = '# implementation'
implementation_end = '# end implementation'


class Implementation(NamedTuple):
    plugin: PluginMeta
    content: List[str]

    @classmethod
    def from_namespace(cls, namespace: str, cores: Sequence[CoreLike]) -> 'Implementation':
        return Implementation(PluginMeta.from_namespace(namespace, cores), [])

    @staticmethod
    def get_name(plugin: PluginMeta, core_name: str, /) -> str:
        return f'_Plugin_{plugin.name}_{core_name}_Bound'

    def __gt__(self, x: 'Implementation', /) -> bool: return self.plugin.__gt__(x.plugin)  # type: ignore[override]
    def __lt__(self, x: 'Implementation', /) -> bool: return self.plugin.__lt__(x.plugin)  # type: ignore[override]
    def __ge__(self, x: 'Implementation', /) -> bool: return self.plugin.__ge__(x.plugin)  # type: ignore[override]
    def __le__(self, x: 'Implementation', /) -> bool: return self.plugin.__le__(x.plugin)  # type: ignore[override]
    def __eq__(self, x: 'Implementation', /) -> bool: return self.plugin.__eq__(x.plugin)  # type: ignore[override]
    def __ne__(self, x: 'Implementation', /) -> bool: return self.plugin.__ne__(x.plugin)  # type: ignore[override]


def make_implementations(plugins: Iterable[PluginMeta]) -> Iterator[Implementation]:
    for plugin in plugins:
        implementation_content = chain.from_iterable(
            (
                '',
                f"class {Implementation.get_name(plugin, core_name)}(Plugin):",
                '    """'
                f'This class implements the module definitions for the "{plugin.name}" VapourSynth plugin.'
                '\\n\\n*This class cannot be imported.*'
                '"""',
                '\n'.join(signatures),
            ) for core_name, signatures in plugin.bound
        )

        content = chain.from_iterable([
            ['', f"{implementation_start}: {plugin.name}"],
            implementation_content,
            ['', implementation_end, '']
        ])

        yield Implementation(plugin, list(content))


instance_start = '# instance_bound_'
instance_end = '# end instance'

instance_bound_pattern = re.compile(fr"^{instance_start}([^:]+): (.+)")


class Instance(NamedTuple):
    plugin: PluginMeta
    core_name: str
    definition: List[str]

    @classmethod
    def from_namespace(cls, namespace: str, core_name: str, cores: Sequence[CoreLike]) -> 'Instance':
        return Instance(PluginMeta.from_namespace(namespace, cores), core_name, [])

    @staticmethod
    def get_head(plugin: PluginMeta, core_name: str) -> str:
        return f"{instance_start}{core_name}: {plugin.name}"

    def __gt__(self, x: 'Instance', /) -> bool: return self.plugin.__gt__(x.plugin)  # type: ignore[override]
    def __lt__(self, x: 'Instance', /) -> bool: return self.plugin.__lt__(x.plugin)  # type: ignore[override]
    def __ge__(self, x: 'Instance', /) -> bool: return self.plugin.__ge__(x.plugin)  # type: ignore[override]
    def __le__(self, x: 'Instance', /) -> bool: return self.plugin.__le__(x.plugin)  # type: ignore[override]
    def __eq__(self, x: 'Instance', /) -> bool: return self.plugin.__eq__(x.plugin)  # type: ignore[override]
    def __ne__(self, x: 'Instance', /) -> bool: return self.plugin.__ne__(x.plugin)  # type: ignore[override]


def make_instances(plugins: Iterable[PluginMeta]) -> Iterator[Instance]:
    for plugin in plugins:
        for core_name, _ in plugin.bound:
            definition = [
                Instance.get_head(plugin, core_name),
                "@property",
                f"def {plugin.name}(self) -> {Implementation.get_name(plugin, core_name)}:",
                f'    """{plugin.description}"""',
                instance_end,
            ]
            yield Instance(plugin, core_name, definition)


def locate_or_create_stub_file() -> str:
    site_package_dir = path.dirname(vs.__file__)
    stub_dir = join_path(site_package_dir, site_package_dirname)

    if not path.exists(stub_dir):
        makedirs(stub_dir)

    output_path = join_path(stub_dir, '__init__.pyi')

    for iname in listdir(site_package_dir):
        if iname.startswith('VapourSynth-') and iname.endswith('.dist-info'):
            break
    else:
        return output_path

    with open(join_path(site_package_dir, iname, 'RECORD'), 'a+', newline='') as f:
        f.seek(0)

        contents = f.read()

        if '__init__.pyi' not in contents:
            f.seek(0, SEEK_END)

            if not contents.endswith('\n'):
                f.write('\n')

            f.write(f'{site_package_dirname}/__init__.pyi,,\n')

    return output_path


def generate_template(
    args: Namespace, cores: Sequence[CoreLike],
    implementations: List[Implementation], instances: List[Instance],
    existing_stubs: Union[Path, None] = None
) -> str:
    template = Path(args.pyi_template).read_text()

    if args.plugins and existing_stubs:
        existing_implementations = get_existing_implementations(existing_stubs, cores)
        existing_instances = get_existing_instances(existing_stubs, cores)

        selected_implementations = [impl.plugin.name for impl in implementations]
        selected_instances = [inst.core_name for inst in instances]

        missing_impl = {*existing_implementations} - {*selected_implementations}

        total_core_names = {*existing_instances, *selected_instances}

        implementations.extend([
            existing_implementations[name] for name in missing_impl
        ])

        instances.extend([
            impl[inst_name]
            for impl in [
                existing_instances[core_name] for core_name in total_core_names
                if core_name in existing_instances
            ]
            for inst_name in missing_impl
            if inst_name in impl
        ])

    if args.exclude_plugin and existing_stubs:
        implementations = [x for x in implementations if x.plugin.name not in args.exclude_plugin]
        instances = [x for x in instances if x.plugin.name not in args.exclude_plugin]

    implementations = sorted(implementations)
    instances = sorted(instances)

    implementation_inject = indent('\n'.join(x.content) for x in implementations)

    template = template.replace('#include <plugins/implementations>', implementation_inject)

    for core in cores:
        this_core_name = core.__class__.__name__

        this_core_template = '\n'.join(
            indent(definition) for _, core_name, definition in instances if core_name == this_core_name
        )

        template = template.replace(f'#include <plugins/bound/{this_core_name}>', this_core_template)

    return template


def output_stubs(
    args: Namespace, cores: Sequence[CoreLike], implementations: List[Implementation], instances: List[Instance]
) -> None:
    existing_stubs: Union[Path, None] = None

    stubs_path = str(args.output)

    if stubs_path == '@' or not stubs_path:
        stubs_path = locate_or_create_stub_file()

    stubs = Path(stubs_path)

    if stubs_path != '-':
        if not stubs.is_absolute():
            if not stubs.parent:
                stubs = stubs.cwd() / stubs
            stubs = stubs.absolute()

        if not stubs.suffix:
            if stubs.name.lower() == 'vapoursynth':
                stubs /= '__init__.pyi'
            else:
                stubs /= 'vapoursynth.pyi'

        existing_stubs = stubs if stubs.exists() and stubs.is_file() else None

        if existing_stubs and args.force:
            existing_stubs.unlink(True)
            existing_stubs.touch()
        else:
            makedirs(stubs.parent, exist_ok=True)

    template = generate_template(args, cores, implementations, instances, existing_stubs)

    out_file = sys.stdout if stubs_path == '-' else open(str(stubs), 'w')

    with out_file:
        out_file.write(template)
        out_file.flush()


def get_existing_implementations(path: Union[str, Path], cores: Sequence[CoreLike]) -> Dict[str, Implementation]:
    result: Dict[str, Implementation] = {}

    with open(path, "r") as f:
        plugin_name: Optional[str] = None

        for orig_line in f:
            line = orig_line.strip()

            if line.startswith(implementation_start):
                plugin_name = line[len(implementation_start) + 1:].strip()
                result[plugin_name] = Implementation.from_namespace(plugin_name, cores)

            if plugin_name:
                result[plugin_name].content.append(orig_line.rstrip())

            if line.startswith(implementation_end):
                plugin_name = None

    return result


def get_existing_instances(path: Union[str, Path], cores: Sequence[CoreLike]) -> Dict[str, Dict[str, Instance]]:
    result: Dict[str, Dict[str, Instance]] = {}

    with open(path, "r") as f:
        core_name: str = ''
        plugin_name: Optional[str] = None

        for orig_line in f:
            line = orig_line.strip()

            if line.startswith(instance_start):
                core_name, plugin_name = instance_bound_pattern.findall(line)[0]

                assert plugin_name

                if core_name not in result:
                    result[core_name] = {}

                if plugin_name not in result[core_name]:
                    result[core_name][plugin_name] = Instance.from_namespace(
                        plugin_name, core_name, cores
                    )

            if plugin_name:
                result[core_name][plugin_name].definition.append(orig_line.rstrip()[4:])

            if line.startswith(instance_end):
                plugin_name = None

    return result


def main(argv: List[str] = sys.argv[1:]):
    args = parser.parse_args(args=argv)

    core = load_plugins(args)

    cores: List[CoreLike] = [core, core.std.BlankClip(), core.std.BlankAudio()]

    signatures = list(retrieve_plugins(args, core, cores))

    implementations = make_implementations(signatures)
    instances = make_instances(signatures)

    output_stubs(args, cores, list(implementations), list(instances))


if __name__ == '__main__':
    main()
