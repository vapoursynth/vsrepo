#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import argparse
import inspect
import keyword
import os
import sys
from typing import List, NamedTuple, Union

import vapoursynth


def indent(string: str, spaces: int) -> str:
    return "\n".join(" "*spaces + line for line in string.splitlines())


parser = argparse.ArgumentParser()
parser.add_argument("--plugin", "-p", action="append", help="Also include manually added plugin")
parser.add_argument("--avs-plugin", action="append", help="Also include manually added AviSynth plugin.")
parser.add_argument("--output", "-o", default="@", help="Where to output the file. The special value '-' means output to stdout. The spcial value '@' will install it as a stub-package inside site-packages.")
parser.add_argument("--pyi-template", default=os.path.join(os.path.dirname(__file__), "_vapoursynth.part.pyi"), help="Don't use unless you know what you are doing.")


class PluginMeta(NamedTuple):
    name: str
    description: str
    functions: str
    bound_to: str


def prepare_cores(ns) -> vapoursynth.Core:
    core = vapoursynth.core.core
    if ns.plugin:
        for plugin in ns.plugin:
            core.std.LoadPlugin(os.path.abspath(plugin))

    if ns.avs_plugin:
        for plugin in ns.avs_plugin:
            core.avs.LoadPlugin(os.path.abspath(plugin))

    return core


def retrieve_ns_and_funcs_unbound(core: vapoursynth.Core) -> List[PluginMeta]:
    return [
        PluginMeta(
            v.namespace, v.name,
            "\n".join(retrieve_func_sigs(core, v.namespace)),
            'Core'
        ) for v in core.plugins()
    ]


def retrieve_ns_and_funcs_bound(core: vapoursynth.Core, *, audio: bool = False) -> List[PluginMeta]:

    if audio:
        base = core.std.BlankAudio()
    else:
        base = core.std.BlankClip()

    plugins: List[PluginMeta] = []

    for p in core.plugins():
        funcs = "\n".join(retrieve_func_sigs(base, p.namespace))
        if funcs:
            plugins.append(
                PluginMeta(
                    p.namespace, p.name, funcs, base.__class__.__name__
                )
            )

    return plugins


def retrieve_func_sigs(core: Union[vapoursynth.Core, vapoursynth.VideoNode, vapoursynth.AudioNode], ns: str) -> List[str]:
    result = []
    plugin = getattr(core, ns)
    for func in plugin.functions():
        if func.name in dir(plugin):
            try:
                signature = str(inspect.signature(getattr(plugin, func.name)))
            except BaseException:
                signature = "(*args: typing.Any, **kwargs: typing.Any) -> Union[NoneType, VideoNode]"

            # Clean up the type annotations so that they are valid python syntax.
            signature = signature.replace("Union", "typing.Union").replace("Sequence", "typing.Sequence")
            signature = signature.replace("vapoursynth.", "")
            signature = signature.replace("VideoNode", '"VideoNode"').replace("VideoFrame", '"VideoFrame"')
            signature = signature.replace("AudioNode", '"AudioNode"').replace("AudioFrame", '"AudioFrame"')
            signature = signature.replace("NoneType", "None")
            signature = signature.replace("Optional", "typing.Optional")

            # Make Callable definitions sensible
            signature = signature.replace("typing.Union[Func, Callable]", "typing.Callable[..., typing.Any]")
            signature = signature.replace("typing.Union[Func, Callable, None]", "typing.Optional[typing.Callable[..., typing.Any]]")

            # Replace the keywords with valid values
            for kw in keyword.kwlist:
                signature = signature.replace(f" {kw}:", f" {kw}_:")

            # Add a self.
            signature = signature.replace("(", "(self, ").replace(", )", ")")
            result.append(f"    def {func.name}{signature}: ...")
    return result


def make_plugin_classes(suffix: str, sigs: List[PluginMeta]) -> str:
    result = []
    for p in sigs:
        result.append(f"class _Plugin_{p.name}_{p.bound_to}_{suffix}(Plugin):")
        result.append('    """')
        result.append('    This class implements the module definitions for the corresponding VapourSynth plugin.')
        result.append('    This class cannot be imported.')
        result.append('    """')
        result.append(p.functions)
        result.append("")
        result.append("")
    return "\n".join(result)


def make_instance_vars(suffix: str, sigs: List[PluginMeta]) -> str:
    result = []
    for p in sigs:
        result.append("@property")
        result.append(f"def {p.name}(self) -> _Plugin_{p.name}_{p.bound_to}_{suffix}:")
        result.append('    """')
        result.append(f'    {p.description}')
        result.append('    """')
    return "\n".join(result)


def inject_stub_package() -> str:
    site_package_dir = os.path.dirname(vapoursynth.__file__)
    stub_dir = os.path.join(site_package_dir, "vapoursynth-stubs")
    if not os.path.exists(stub_dir):
        os.makedirs(stub_dir)
    output_path = os.path.join(stub_dir, "__init__.pyi")

    for iname in os.listdir(site_package_dir):
        if iname.startswith("VapourSynth-") and iname.endswith(".dist-info"):
            break
    else:
        return output_path

    with open(os.path.join(site_package_dir, iname, "RECORD"), "a+", newline="") as f:
        f.seek(0)
        contents = f.read()
        if "__init__.pyi" not in contents:
            f.seek(0, os.SEEK_END)
            if not contents.endswith("\n"):
                f.write("\n")
            f.write("vapoursynth-stubs/__init__.pyi,,\n")

    return output_path


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    args = parser.parse_args(args=argv)
    core = prepare_cores(args)

    # bound = retrieve_ns_and_funcs(core, bound=True)
    boundv = retrieve_ns_and_funcs_bound(core, audio=False)
    bounda = retrieve_ns_and_funcs_bound(core, audio=True)

    unbound = retrieve_ns_and_funcs_unbound(core)

    implementations = (
        make_plugin_classes("Unbound", unbound)
        + "\n" + make_plugin_classes("Bound", boundv)
        + "\n" + make_plugin_classes("Bound", bounda)
    )

    inject_boundv = indent(make_instance_vars("Bound", boundv), 4)
    inject_bounda = indent(make_instance_vars("Bound", bounda), 4)
    inject_unbound = indent(make_instance_vars("Unbound", unbound), 4)


    with open(args.pyi_template) as f:
        template = f.read()

    template = template.replace("#include <plugins/implementations>", implementations)
    template = template.replace("#include <plugins/unbound>", inject_unbound)
    template = template.replace("#include <plugins_vnode/bound>", inject_boundv)
    template = template.replace("#include <plugins_anode/bound>", inject_bounda)

    if args.output == "-":
        f = sys.stdout
    elif args.output == "@":
        stub_path = inject_stub_package()
        f = open(stub_path, "w")
    else:
        f = open(args.output, "w")

    with f:
        f.write(template)
        f.flush()


if __name__ == "__main__":
    main(sys.argv[1:])
