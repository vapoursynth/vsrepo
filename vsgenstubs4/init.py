#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import sys
from argparse import ArgumentParser, Namespace
from inspect import Parameter, Signature
from itertools import chain
from keyword import kwlist as reserved_keywords
from os import SEEK_END, listdir, makedirs, path
from os.path import join as join_path
from pathlib import Path
from typing import Any, Iterable, Iterator, NamedTuple, Optional, Protocol, Sequence, TypeVar, Union

import vapoursynth as vs


__all__ = [
    'main'
]

T = TypeVar('T')
CoreLike = Union[vs.Core, vs.RawNode]

SingleAndSequence = Union[T, Sequence[T]]


class Callback(Protocol):
    def __call__(self, *args: Any, **kwds: Any) -> '_VapourSynthMapValue':
        ...


_VapourSynthMapValue = Union[
    SingleAndSequence[int],
    SingleAndSequence[float],
    SingleAndSequence[str],
    SingleAndSequence[vs.VideoNode],
    SingleAndSequence[vs.VideoFrame],
    SingleAndSequence[vs.AudioNode],
    SingleAndSequence[vs.AudioFrame],
    SingleAndSequence[Callback]
]

vs_value_type = '_VapourSynthMapValue'
site_package_dirname = 'vapoursynth-stubs'

parser = ArgumentParser()
parser.add_argument(
    "plugins",
    type=str, nargs="*",
    help="Only generate stubs for and inject specified plugin namespaces."
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
    help="Where to output the file. "
    "The special value '-' means output to stdout. "
    "The spcial value '@' will install it as a stub-package inside site-packages."
)
parser.add_argument(
    '--pyi-template',
    default=join_path(path.dirname(__file__), '_vapoursynth.part.pyi'),
    help='Don\'t use unless you know what you are doing.'
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
    if args.load_plugin:
        for plugin in args.load_plugin:
            vs.core.std.LoadPlugin(path.abspath(plugin))

    if args.avs_plugin:
        if hasattr(vs.core, 'avs'):
            for plugin in args.avs_plugin:
                vs.core.avs.LoadPlugin(path.abspath(plugin))
        else:
            raise AttributeError('Core is missing avs plugin!')

    return vs.core.core


def retrieve_func_sigs(core: Union[vs.Core, vs.RawNode], namespace: str) -> Iterator[str]:
    plugin = core.__getattr__(namespace)

    ordered_functions = sorted(plugin.functions(), key=lambda x: x.name.lower())

    for func in ordered_functions:
        signature_base = anonymous_signature

        if func.name in dir(plugin):
            try:
                signature_base = Signature.from_callable(
                    plugin.__getattr__(func.name), follow_wrapped=True, eval_str=False
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

            # Make Callable definitions sensible
            signature = signature.replace('Union[Func, Callable]', 'Callback')
            signature = signature.replace('Union[Func, Callable, None]', 'Optional[Callback]')

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

    def __iter__(self) -> Iterator[tuple[str, Iterator[str]]]:
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

    def _str_(self, kind: str, __x: tuple[object, ...]) -> bool:
        return getattr(str, kind)(self.name.lower(), str(__x[0]).lower())

    def __gt__(self, x: 'PluginMeta', /) -> bool: return self._str_('__gt__', x)  # type: ignore[override]
    def __lt__(self, x: 'PluginMeta', /) -> bool: return self._str_('__lt__', x)  # type: ignore[override]
    def __ge__(self, x: 'PluginMeta', /) -> bool: return self._str_('__ge__', x)  # type: ignore[override]
    def __le__(self, x: 'PluginMeta', /) -> bool: return self._str_('__le__', x)  # type: ignore[override]


def retrieve_plugins(
    core: vs.Core, cores: Iterable[CoreLike], *, only_plugins: Union[Sequence[str], None] = None
) -> Iterator[PluginMeta]:
    lower_plugins = list(map(str.lower, only_plugins)) if only_plugins else []

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


class Implementation(NamedTuple):
    plugin: PluginMeta
    classes: Iterable[str]

    @staticmethod
    def get_name(plugin: PluginMeta, core_name: str, /) -> str:
        return f'_Plugin_{plugin.name}_{core_name}_Bound'

    def get_own_name(self, core_name: str, /) -> str:
        return self.get_name(self.plugin, core_name)


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

        classes = chain.from_iterable([
            ['', f"# implementation: {plugin.name}"],
            implementation_content,
            ['', "# end implementation", '']
        ])

        yield Implementation(plugin, list(classes))


class Instance(NamedTuple):
    plugin: PluginMeta
    core_name: str
    definition: str


def make_instances(plugins: Iterable[PluginMeta]) -> Iterator[Instance]:
    for plugin in plugins:
        for core_name, _ in plugin.bound:
            definition = [
                f"# instance_bound_{core_name}: {plugin.name}",
                "@property",
                f"def {plugin.name}(self) -> {Implementation.get_name(plugin, core_name)}:",
                f'    """{plugin.description}"""',
                "# end instance",
            ]
            yield Instance(plugin, core_name, indent(definition))


def locat_or_creat_stub_file() -> str:
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
    args: Namespace, cores: Iterable[CoreLike], implementations: Iterable[Implementation], instances: Iterable[Instance]
) -> str:
    template = Path(args.pyi_template).read_text()

    implementation_inject = indent('\n'.join(x.classes) for x in implementations)

    template = template.replace('#include <plugins/implementations>', implementation_inject)

    for core in cores:
        this_core_name = core.__class__.__name__

        this_core_template = '\n'.join(
            definition for _, core_name, definition in instances if core_name == this_core_name
        )

        template = template.replace(f'#include <plugins/bound/{this_core_name}>', this_core_template)

    return template


def output_stubs(
    args: Namespace, cores: Iterable[CoreLike], implementations: Iterable[Implementation], instances: Iterable[Instance]
) -> None:
    if args.output == '-':
        outf = sys.stdout
    elif args.output == '@':
        outf = open(locat_or_creat_stub_file(), 'w')
    else:
        outf = open(args.output, 'w')

    template = generate_template(args, cores, implementations, instances)

    with outf:
        outf.write(template)
        outf.flush()


def main(argv: list[str] = sys.argv[1:]):
    args = parser.parse_args(args=argv)

    core = load_plugins(args)

    cores = list[CoreLike]([core, core.std.BlankClip(), core.std.BlankAudio()])

    signatures = sorted(retrieve_plugins(core, cores, only_plugins=args.plugins))

    implementations = make_implementations(signatures)
    instances = make_instances(signatures)

    output_stubs(args, cores, list(implementations), list(instances))


if __name__ == '__main__':
    main()
