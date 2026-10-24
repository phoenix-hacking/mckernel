"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Materialize unchanged accepted reader functions from explicit root namespace DATA.
No product imports, runtime observation, root/query/guest/Docker or fixture run.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path

D = Path(__file__).resolve().parent
R = D.parent
BASE = Path('/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/runtime-sdk8-snapshot-equality-successor-1/early-read-preparation-1/read_live_LONG_prefix.py')
BASE_SHA = 'd295f9f4d84989be2369c0d2592193a1eca4f587d47db1c2a226136efca3214c'
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'


def pin(path):
    path = Path(path); raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def substitute(source, name, expression):
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))
    return source.replace(ast.get_source_segment(source, node), name+' = '+expression, 1)


def functions(source):
    return {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(source).body
            if isinstance(n, (ast.FunctionDef, ast.ClassDef))}


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--namespace', type=Path, default=R/'ROOT-NAMESPACE.PENDING.json')
parser.add_argument('--cohort', type=Path, default=R/'COHORT-BINDINGS.json')
args = parser.parse_args()
base = BASE.read_text()
assert pin(BASE)['sha256'] == BASE_SHA
namespace = json.loads(args.namespace.read_text())
cohort = json.loads(args.cohort.read_text())
decoder = cohort['p12_long_session.py']
assert pin(decoder['path']) == decoder
assert decoder['sha256'] == 'bff717d885afdda0d82cd0ab05a0930a3e66b242c6200b1295f2173bb4cdc5d3'
nonce, parent = namespace.get('nonce'), namespace.get('host_parent')
bound = (isinstance(nonce, str) and len(nonce) == 32 and all(c in '0123456789abcdef' for c in nonce)
         and nonce != '63bdc7731c34491eb430ddb34b094d5b'
         and isinstance(parent, str) and Path(parent).is_absolute() and Path(parent).is_dir())
if bound:
    identity = namespace.get('host_identity')
    assert isinstance(identity, dict), 'root actual host identity required, not just chosen names'
    serial = str(Path(parent)/('attempt-'+nonce)/'serial.log')
else:
    nonce = '__ROOT_ACTUAL_NONCE_REQUIRED__'
    parent = '__ROOT_ACTUAL_HOST_PARENT_REQUIRED__'
    serial = None
source = substitute(base, 'NONCE', repr(nonce))
source = substitute(source, 'SERIAL', "Path("+repr(parent)+")/('attempt-'+NONCE)/'serial.log'")
source = substitute(source, 'DECODER', 'Path('+repr(decoder['path'])+')')
source = substitute(source, 'DECODER_SHA', repr(decoder['sha256']))
assert functions(source) == functions(base), 'accepted reader function bodies must stay exact'
target = D/('read_live_LONG_prefix.py' if bound else 'read_live_LONG_prefix.PENDING.template')
if target.exists():
    assert target.read_text() == source, 'existing reader differs; never mutate a potentially live reader'
else:
    with target.open('x') as stream:
        stream.write(source)
argv = ['/usr/bin/taskset', '-c', '0', '/usr/bin/prlimit', '--as=2147483648:2147483648',
        '--cpu=10:10', '--fsize=33554432:33554432', '--core=0:0', '--nofile=256:256', '--',
        '/home/holden/anaconda3/bin/python3', '-I', '-B', str(D/'read_live_LONG_prefix.py'), None, None]
operation = dict(scope=SCOPE, status='SOURCE_READY_PENDING_ACTUAL_OWNER_ANCHORS_AND_ROOT_READ_GRANT' if bound else 'PARAMETERS_PENDING_NO_RUNTIME_READER_MATERIALIZED',
    namespace_source=str(args.namespace), cohort_source=str(args.cohort), namespace_actual=bound,
    reader=pin(target), accepted_reader=pin(BASE), functions_AST_identical=True,
    literal_changes=['NONCE', 'SERIAL host parent', 'DECODER selected successor path'],
    decoder=decoder, nonce=namespace.get('nonce'), serial_path=serial,
    actual_owner_pid=None, actual_owner_start_ticks=None, outer_controller_anchor=None,
    command=dict(purpose=SCOPE+' One root-owned ordinary readonly observation; no acceptance.', argv=argv),
    descriptor_API='owned_capture(command_dictionary, fresh_capture_path, 20, limits); NEVER pass the argv list as the command argument',
    capture_source='/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py',
    capture_source_sha256='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8',
    capture_directory=str(D/'actual-read-1'),
    profile=dict(uid=1000, cpu=[0], AS=2*2**30, CPU=10, wall=20, grace=6, FSIZE=32*2**20, NOFILE=256, core=0, prefix_cap=8*2**20, line_cap=262144),
    interpreter=dict(path='/home/holden/anaconda3/bin/python3', required_version='3.9.12', resolved_path=str(Path('/home/holden/anaconda3/bin/python3').resolve()), qualification='Existing accepted3.9.12 ordinary consumer profile; no interpreter or product was executed for this preparation.'),
    first_read_timing='Root invokes existing ordinary capture about30-60seconds after authenticated actualnewowner launch; use CLOCK_BOOTTIME/SC_CLK_TCK for birth age, neverMONOTONIC.',
    required_substitutions=['Actual root-observed NEW nonce and HOST parent/identity, not63bd/l12s8e1; rematerialize this reader source before launch/read.',
        'Actual innerowner PID/start from genuine newstartedreceipt, replacing finaltwo argv None slots with decimal strings; neverreuse4007173/59944315.',
        'Root separately owns exact source/profile/grant and fresh capture directory; outercontroller anchor metadata authenticated ifused.'],
    fail_abort_coverage='Retain complete rawprefix/base64 and run the unchanged retained diagnostic interpreter. Report failure_records, abort_records, trace_errors, diagnostic_parse_errors, wire_error and bothanchors. Prefixcap8MiB; ifcapped_before_initial_EOF=true, absenceofFAIL/ABORT inprefix is NOT globalabsence. Incompletefinal line isexcluded, notaccepted. Owner/privateledger/terminalcontrol remainUNKNOWN.',
    root_read_grant=None, actual_read=None, product_imports=0, root=0, Docker=0, guest=0, runtime_observations=0,
    native_acceptance=False, application_acceptance=False, work_hour_credit=0)
(D/'READ-OPERATION.PENDING.json').write_text(json.dumps(operation, indent=2)+'\n')
print(json.dumps(dict(namespace_actual=bound, reader_source=str(target), runtime_observations=0,
      operation=str(D/'READ-OPERATION.PENDING.json')), sort_keys=True))
