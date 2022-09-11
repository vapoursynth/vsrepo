#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import argparse
import keyword
import os
import sys
from inspect import Parameter, Signature
from inspect import signature as signature_from
from typing import Any, Iterable, Iterator, List, NamedTuple, Optional, Union

import vapoursynth as vs


def indent(strings: Iterable[str], spaces: int = 4) -> str:
    return '\n'.join(' ' * spaces + line for line in strings)


parser = argparse.ArgumentParser()
parser.add_argument('--plugin', '-p', action='append', help='Also include manually added plugin')
parser.add_argument('--avs-plugin', action='append', help='Also include manually added AviSynth plugin.')
parser.add_argument(
    '--output', '-o', default='@',
    help="Where to output the file. The special value '-' means output to stdout. "
    "The spcial value '@' will install it as a stub-package inside site-packages."
)
parser.add_argument(
    '--pyi-template',
    default=os.path.join(os.path.dirname(__file__), '_vapoursynth.part.pyi'),
    help='Don\'t use unless you know what you are doing.'
)


class PluginMeta(NamedTuple):
    name: str
    description: str
    functions: str
    bound_to: str


site_package_dirname = 'vapoursynth-stubs'


def prepare_cores(ns) -> vs.Core:
    core = vs.core.core

    if ns.plugin:
        for plugin in ns.plugin:
            core.std.LoadPlugin(os.path.abspath(plugin))

    if ns.avs_plugin:
        for plugin in ns.avs_plugin:
            core.avs.LoadPlugin(os.path.abspath(plugin))

    return core


def retrieve_ns_and_funcs_unbound(core: vs.Core) -> List[PluginMeta]:
    return [
        PluginMeta(
            v.namespace, v.name,
            '\n'.join(retrieve_func_sigs(core, v.namespace)),
            'Core'
        ) for v in core.plugins()
    ]


def retrieve_ns_and_funcs_bound(core: vs.Core, *, audio: bool = False) -> Iterator[PluginMeta]:
    base = core.std.BlankAudio() if audio else core.std.BlankClip()

    for p in core.plugins():
        funcs = list(retrieve_func_sigs(base, p.namespace))

        if not funcs:
            continue

        yield PluginMeta(
            p.namespace, p.name, '\n'.join(funcs), base.__class__.__name__
        )


def retrieve_func_sigs(core: Union[vs.Core, vs.RawNode], namespace: str) -> Iterator[str]:
    plugin = core.__getattr__(namespace)

    for func in plugin.functions():
        if func.name in dir(plugin):
            signature: Union[str, Signature]
            try:
                signature = signature_from(getattr(plugin, func.name))
            except BaseException:
                signature = Signature(
                    [
                        Parameter('args', Parameter.VAR_POSITIONAL, annotation=Any),
                        Parameter('kwargs', Parameter.VAR_KEYWORD, annotation=Any)
                    ],
                    return_annotation=Optional[vs.VideoNode]
                )

            if signature.return_annotation in {Any, Optional[Any]}:
                signature = signature.replace(return_annotation=vs.VideoNode)

            signature = str(signature)

            # Clean up the type annotations so that they are valid python syntax.
            signature = signature.replace('vapoursynth.', '')
            signature = signature.replace('VideoNode', "'VideoNode'").replace('VideoFrame', "'VideoFrame'")
            signature = signature.replace('AudioNode', "'AudioNode'").replace('AudioFrame', "'AudioFrame'")
            signature = signature.replace('NoneType', 'None')
            signature = signature.replace('Optional', 'Optional')
            signature = signature.replace('Tuple', 'Tuple')

            # Make Callable definitions sensible
            signature = signature.replace('Union[Func, Callable]', 'Callback')
            signature = signature.replace('Union[Func, Callable, None]', 'Optional[Callback]')

            # Replace the keywords with valid values
            for kw in keyword.kwlist:
                signature = signature.replace(f' {kw}:', f' {kw}_:')

            # Add a self.
            signature = signature.replace('(', '(self, ').replace(', )', ')')

            yield f'    def {func.name}{signature}: ...'


def make_plugin_classes(suffix: str, sigs: Iterable[PluginMeta]) -> Iterator[str]:
    for p in sigs:
        yield f'class _Plugin_{p.name}_{p.bound_to}_{suffix}(Plugin):'
        yield '    """'
        yield f'    This class implements the module definitions for the "{p.name}" vs plugin.'
        yield '    This class cannot be imported.'
        yield '    """'
        yield p.functions
        yield ''
        yield ''


def make_instance_vars(suffix: str, sigs: Iterable[PluginMeta]) -> Iterator[str]:
    for p in sigs:
        yield '@property'
        yield f'def {p.name}(self) -> _Plugin_{p.name}_{p.bound_to}_{suffix}:'
        yield '    """'
        yield f'    {p.description}'
        yield '    """'


def inject_stub_package() -> str:
    site_package_dir = os.path.dirname(vs.__file__)
    stub_dir = os.path.join(site_package_dir, site_package_dirname)

    if not os.path.exists(stub_dir):
        os.makedirs(stub_dir)

    output_path = os.path.join(stub_dir, '__init__.pyi')

    for iname in os.listdir(site_package_dir):
        if iname.startswith('vs-') and iname.endswith('.dist-info'):
            break
    else:
        return output_path

    with open(os.path.join(site_package_dir, iname, 'RECORD'), 'a+', newline='') as f:
        f.seek(0)
        contents = f.read()
        if '__init__.pyi' not in contents:
            f.seek(0, os.SEEK_END)
            if not contents.endswith('\n'):
                f.write('\n')
            f.write(f'{site_package_dirname}/__init__.pyi,,\n')

    return output_path


def main(argv: Union[list[str], None] = None):
    if argv is None:
        argv = sys.argv[1:]

    args = parser.parse_args(args=argv)
    core = prepare_cores(args)

    # bound = retrieve_ns_and_funcs(core, bound=True)
    bound_video = retrieve_ns_and_funcs_bound(core, audio=False)
    bound_audio = retrieve_ns_and_funcs_bound(core, audio=True)

    unbound = retrieve_ns_and_funcs_unbound(core)

    implementations = '\n'.join([
        *make_plugin_classes('Unbound', unbound),
        *make_plugin_classes('Bound', bound_video),
        *make_plugin_classes('Bound', bound_audio)
    ])

    inject_bound_video = indent(make_instance_vars('Bound', bound_video), 4)
    inject_bound_audio = indent(make_instance_vars('Bound', bound_audio), 4)
    inject_unbound = indent(make_instance_vars('Unbound', unbound), 4)

    with open(args.pyi_template) as f:
        template = f.read()

    template = template.replace('#include <plugins/implementations>', implementations)
    template = template.replace('#include <plugins/unbound>', inject_unbound)
    template = template.replace('#include <plugins_vnode/bound>', inject_bound_video)
    template = template.replace('#include <plugins_anode/bound>', inject_bound_audio)

    if args.output == '-':
        outf = sys.stdout
    elif args.output == '@':
        stub_path = inject_stub_package()
        outf = open(stub_path, 'w')
    else:
        outf = open(args.output, 'w')

    with outf:
        outf.write(template)
        outf.flush()


if __name__ == '__main__':
    main(sys.argv[1:])
