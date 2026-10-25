"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One source-bound BFD qualifier under the reviewed owned-capture lifecycle.
"""
from pathlib import Path
import ast
import hashlib
import json
import os
import resource
import signal
import sys

PREPARATION = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/equivalence-oracle-correction-source-7/selected-bootstrap-correction-source-8/coherent-cxx-bound-retained11-suffix10-source-2/BFD-PREPARATION.json')
PREPARATION_SHA = 'd68fdaf5153477a9f6cfedc86e17ad10f503a077635cb3ad6d0dc73000a78cfc'


def need(ok, message):
    if not ok:
        raise ValueError(message)


def main():
    need(sys.argv[1:] == ['--execute'], 'exact BFD driver mode')
    raw = PREPARATION.read_bytes()
    need(hashlib.sha256(raw).hexdigest() == PREPARATION_SHA, 'exact BFD preparation')
    prep = json.loads(raw)
    command_doc = json.loads(Path(prep['commands']['path']).read_bytes())
    need(hashlib.sha256(Path(prep['commands']['path']).read_bytes()).hexdigest() == prep['commands']['sha256'], 'exact BFD command')
    capture = Path('/work/evidence')
    need(not capture.exists() and not Path('/work/qualification-1').exists(), 'fresh BFD output/captures')
    capture.mkdir(mode=0o700)
    helper_path = Path(prep['capture_helper']['path'])
    helper = helper_path.read_bytes()
    need(hashlib.sha256(helper).hexdigest() == prep['capture_helper']['sha256'] == '990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8', 'exact reviewed h990 capture source')
    functions = {'need', 'write', 'hashed', 'stop', 'members', 'cpu_used', 'process_start', 'terminal_unreaped', 'wait_terminal', 'owned_capture'}
    constants = {'FIELDS', 'stopping', 'CENSUS_SOURCE', 'CENSUS_SHA', '_CENSUS', 'STOP_SIGNALS'}
    nodes = []
    for item in ast.parse(helper).body:
        if isinstance(item, (ast.Import, ast.ImportFrom)):
            nodes.append(item)
        elif isinstance(item, ast.FunctionDef) and item.name in functions:
            nodes.append(item)
        elif isinstance(item, ast.Assign) and any(isinstance(t, ast.Name) and t.id in constants for t in item.targets):
            nodes.append(item)
    need({item.name for item in nodes if isinstance(item, ast.FunctionDef)} == functions, 'complete capture function closure')
    namespace = {'__file__': str(helper_path), '__name__': 'bfd_owned_capture'}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(helper_path), 'exec'), namespace)
    for number in namespace['STOP_SIGNALS']:
        signal.signal(number, namespace['stop'])
    def limits():
        for kind, value in ((resource.RLIMIT_AS, 2<<30), (resource.RLIMIT_CPU, prep['timeout']),
                            (resource.RLIMIT_FSIZE, prep['output_budget_bytes']),
                            (resource.RLIMIT_NOFILE, 256), (resource.RLIMIT_CORE, 0)):
            resource.setrlimit(kind, (value,value))
    command = {'argv': command_doc['command'], 'scope': prep['scope']}
    namespace['write'](capture/'command.json', command)
    signal.setitimer(signal.ITIMER_REAL, prep['timeout'])
    try:
        result = namespace['owned_capture'](command, capture, prep['timeout']-6, limits)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    namespace['write'](capture/'qualifier-join.json', result)
    positive = (result['returncode'] == 0 and result['direct_child_joined'] and
                result['group_absent'] and result['closed_streams'] and
                result['error'] is None and result['retirement_error'] is None and
                not result['timed_out'] and result['captures']['stderr']['size'] == 0)
    receipt = {'schema':'mckernel.bfd-retained-prefix-sdk-suffix-receipt.v1',
               'scope':prep['scope'], 'status':'PASS_BFD_PREFIX_REUSED_SUFFIX_CAPTURE' if positive else 'FAIL_RETAINED_NO_RETRY',
               'preparation_sha256':PREPARATION_SHA, 'command':command_doc['command'],
               'capture':result, 'native_acceptance':False, 'M15_file_closure':False}
    if positive:
        result_path = Path('/work/qualification-1/RESULT.json')
        receipt['qualifier_result_sha256'] = hashlib.sha256(result_path.read_bytes()).hexdigest()
    namespace['write'](capture/'receipt.json', receipt)
    print(json.dumps({'status':receipt['status']}))
    return 0 if positive else 1


if __name__ == '__main__':
    raise SystemExit(main())
