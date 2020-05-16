import os
import sys
import inspect
import argparse
import vapoursynth
from typing import Dict, Sequence, Union, NamedTuple


def indent(string: str, spaces: int) -> str:
    return "\n".join(" "*spaces + line for line in string.splitlines())


parser = argparse.ArgumentParser()
parser.add_argument("--plugin", "-p", action="append", help="Also include manually added plugin")
parser.add_argument("--avs-plugin", action="append", help="Also include manually added AviSynth plugin.")
parser.add_argument("--output", "-o", default="vapoursynth.pyi", help="Where to output the file. The special value '-' means output to stdout.")
parser.add_argument("--pyi-template", default=os.path.join(os.path.dirname(__file__), "_vapoursynth.part.pyi"), help="Don't use unless you know what you are doing.")


class PluginMeta(NamedTuple):
    name: str
    description: str
    functions: str


def prepare_cores(ns) -> vapoursynth.Core:
    core = vapoursynth.core.core
    if ns.plugin:
        for plugin in ns.plugin:
            core.std.LoadPlugin(os.path.abspath(plugin))

    if ns.avs_plugin:
        for plugin in ns.avs_plugin:
            core.avs.LoadPlugin(os.path.abspath(plugin))

    return core


def retrieve_ns_and_funcs(core: vapoursynth.Core, *, bound: bool=False) -> Dict[str, PluginMeta]:
    result = {}

    base = core
    if bound:
        base = core.std.BlankClip()

    for v in core.get_plugins().values():
        result[v["namespace"]] = PluginMeta(
            v["namespace"],
            v["name"],
            "\n".join(retrieve_func_sigs(base, v["namespace"], v["functions"].keys()))
        )
    return result


def retrieve_func_sigs(core: Union[vapoursynth.Core, vapoursynth.VideoNode], ns: str, funcs: Sequence[str]) -> str:
    result = []
    plugin = getattr(core, ns)
    for func in funcs:
        try:
            signature = str(inspect.signature(getattr(plugin, func)))
        except BaseException:
            signature = "(*args, **kwargs) -> Union[NoneType, VideoNode]"
        signature = signature.replace("Union", "typing.Union").replace("Sequence", "typing.Sequence")
        signature = signature.replace("vapoursynth.", "")
        signature = signature.replace("VideoNode", '"VideoNode"').replace("VideoFrame", '"VideoFrame"')
        signature = signature.replace("(", "(self, ").replace(", )", ")")
        result.append(f"    def {func}{signature}: ...")
    return result


def make_plugin_classes(suffix: str, sigs: Dict[str, PluginMeta]) -> str:
    result = []
    for pname, pfuncs in sigs.items():
        result.append(f"class Plugin_{pname}_{suffix}(Plugin):")
        result.append(pfuncs.functions)
        result.append("")
        result.append("")
    return "\n".join(result)


def make_instance_vars(suffix: str, sigs: Dict[str, PluginMeta]) -> str:
    result = []
    for pname, pfuncs in sigs.items():
        result.append("@property")
        result.append(f"def {pname}(self) -> Plugin_{pname}_{suffix}:")
        result.append('    """')
        result.append(f'    {pfuncs.description}')
        result.append('    """')
    return "\n".join(result)


def main(argv):
    args = parser.parse_args(args=argv)
    core = prepare_cores(args)

    bound = retrieve_ns_and_funcs(core, bound=True)
    unbound = retrieve_ns_and_funcs(core, bound=False)

    implementations = make_plugin_classes("Unbound", unbound) + "\n" + make_plugin_classes("Bound", bound)

    inject_bound = indent(make_instance_vars("Bound", bound), 4)
    inject_unbound = indent(make_instance_vars("Unbound", unbound), 4)

    with open(args.pyi_template) as f:
        template = f.read()

    template = template.replace("#include <plugins/implementations>", implementations)
    template = template.replace("#include <plugins/unbound>", inject_unbound)
    template = template.replace("#include <plugins/bound>", inject_bound)

    if args.output == "-":
        f = sys.stdout
    else:
        f = open(args.output, "w")
    
    with f:
        f.write(template)
        f.flush()

if __name__ == "__main__":
    main(sys.argv[1:])