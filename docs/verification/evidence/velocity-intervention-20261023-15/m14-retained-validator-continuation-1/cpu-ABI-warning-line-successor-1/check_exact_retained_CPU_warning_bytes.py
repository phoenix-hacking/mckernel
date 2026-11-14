#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure exact-retained-byte/source regression. No subprocess or compiler execution.
"""
import ast
import hashlib
import json
from pathlib import Path

BINDINGS = {'/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/fresh-copy2-binding-preparation-1/retained_artifact_validator.FRESH-COPY2.POSTBOUND.py': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/fresh-copy2-binding-preparation-1/retained_artifact_validator.FRESH-COPY2.POSTBOUND.py', 'bytes': 240759, 'sha256': 'e0728b22c6488c2343178f556d2d492c446ee7f22935a16881981cf5f9d548af'}, '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/cpu-ABI-warning-line-successor-1/retained_artifact_validator.CPU-WARNING-LINES.NOT-RELEASED.py': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/cpu-ABI-warning-line-successor-1/retained_artifact_validator.CPU-WARNING-LINES.NOT-RELEASED.py', 'bytes': 240759, 'sha256': 'ab5fb5a8ef7b7431731d732d4b3a4eed70c14b1b2c5fcfb73b085d41da2535ce'}, '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-10/m14-union2-default-image-preparation-1/source-materialization-CPU0-1/materialized-source/arch/x86_64/kernel/cpu.c': {'bytes': 95918, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-10/m14-union2-default-image-preparation-1/source-materialization-CPU0-1/materialized-source/arch/x86_64/kernel/cpu.c', 'sha256': '5574c151cef8d26fa14e3eac72d54b55703be153e4f147f831c5a9e9b63c70bc'}, '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/production-context-consumer-preparation-1/source/arch/x86_64/kernel/cpu.c': {'bytes': 95605, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/production-context-consumer-preparation-1/source/arch/x86_64/kernel/cpu.c', 'sha256': 'c779079fb6de66991c861c823dca06b2a9ceec16ac4c984995200b668d7e78ce'}, '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-2/owner-work/output/build/m14-production/retained-observations-1/successor-real-ABI-arch-x86_64-kernel-cpu-c.stderr': {'bytes': 1519, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-2/owner-work/output/build/m14-production/retained-observations-1/successor-real-ABI-arch-x86_64-kernel-cpu-c.stderr', 'sha256': '1e5638689ba3ee7e0bd5ba4d66fd1e004aa4088e23dd1e6ee79005eb34846f2b'}, '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/cpu-ABI-warning-line-successor-1/EXACT-SOURCE-AND-WARNING-CORRESPONDENCE.json': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/cpu-ABI-warning-line-successor-1/EXACT-SOURCE-AND-WARNING-CORRESPONDENCE.json', 'bytes': 4248, 'sha256': '7389d366e4bdfa781419988938a3ba8d3b176e594fb1d52532be9861d08bc589'}}
OLD = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/fresh-copy2-binding-preparation-1/retained_artifact_validator.FRESH-COPY2.POSTBOUND.py')
NEW = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/cpu-ABI-warning-line-successor-1/retained_artifact_validator.CPU-WARNING-LINES.NOT-RELEASED.py')
SOURCE = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-10/m14-union2-default-image-preparation-1/source-materialization-CPU0-1/materialized-source/arch/x86_64/kernel/cpu.c')
CAPTURE = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-2/owner-work/output/build/m14-production/retained-observations-1/successor-real-ABI-arch-x86_64-kernel-cpu-c.stderr')
PHASE = 'successor-real-ABI-arch-x86_64-kernel-cpu-c'

def need(condition, message):
    if not condition:
        raise ValueError(message)

def selected(path):
    tree = ast.parse(path.read_text())
    nodes = []
    pins = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = [target.id for target in node.targets if isinstance(target, ast.Name)]
            if 'M14_CURRENT_CPU_ABI_WARNINGS' in names:
                nodes.append(node)
            if 'M14_SOURCE_PINS' in names:
                pins = ast.literal_eval(node.value)
        elif isinstance(node, ast.FunctionDef) and node.name == '_m14_cpu_abi_stderr_allowed':
            nodes.append(node)
    need(len(nodes) == 2, 'one exact warning constant and actual allowance function')
    namespace = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)
    return namespace, pins

def main():
    for name, row in BINDINGS.items():
        raw = Path(name).read_bytes()
        need(len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256'],
             'exact frozen regression input: ' + name)
    old, old_pins = selected(OLD)
    new, new_pins = selected(NEW)
    source_sha = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    need(old_pins == new_pins and new_pins['arch/x86_64/kernel/cpu.c'] == source_sha,
         'unchanged genuine materialized CPU source pin')
    raw = CAPTURE.read_bytes()
    need(len(raw) == 1519, 'actual complete retained warning length')
    need(not old['_m14_cpu_abi_stderr_allowed'](PHASE, raw), 'genuine old rejection')
    need(new['_m14_cpu_abi_stderr_allowed'](PHASE, raw), 'exact actual new acceptance')
    negative_line = raw.replace(b'3746:37:', b'3746:38:', 1)
    negative_statement = raw.replace(b'&x86v->paniced, USER_END,',
                                     b'&x86v->paniced, USER_ENDX,', 1)
    need(negative_line != raw and negative_statement != raw, 'two distinct actual mutations')
    need(not new['_m14_cpu_abi_stderr_allowed'](PHASE, negative_line),
         'changed source column must fail')
    need(not new['_m14_cpu_abi_stderr_allowed'](PHASE, negative_statement),
         'changed statement must fail')
    print(json.dumps({'scope': 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
                      'status': 'PASS_EXACT_RETAINED1519_OLD_REJECT_NEW_ACCEPT_TWO_MUTATIONS_REJECT',
                      'retained_bytes': len(raw), 'source_sha256': source_sha,
                      'old_rejection': True, 'new_acceptance': True, 'negative_rejections': 2,
                      'compiler_commands': 0, 'real_children': 0, 'full_validator': False},
                     sort_keys=True))

if __name__ == '__main__':
    main()
