"""M14 source-only exact compile-argv DATA checks; never execution authority.

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
The inherited-channel owner must separately authenticate actual observations,
headers, source closure, process identity and the original389 oracle. This
module neither executes commands nor accepts a generated JSON record as proof.
"""
import json
import hashlib
from pathlib import Path

HERE=Path(__file__).parent
ORIGIN_GUARD='-DMCKERNEL_M14_F06_ORIGIN_GUARD'
PERF_WITNESS='-DMCKERNEL_F03_PERF_ENTRY_ABI_WITNESS'
WITNESS_OBJECT='/work/output/witness/perf-entry-abi.o'
WITNESS_DEPFILE='/work/output/witness/perf-entry-abi.d'
DATA_STATUS='UNAUTHENTICATED_ARGV_DATA_ONLY'
COMMANDS_SHA256='82ae9b201c56d7f4a3d1d6f142222a34d16b1e0d56c1d90d103d7ad85c1f5572'


def _need(ok, why):
    if not ok:
        raise ValueError(why)


def _argv(value):
    _need(type(value) is list and value and all(type(x) is str and x and '\0' not in x for x in value),'argv shape')
    return value


def _single_remove(argv, token):
    _need(argv.count(token)==1,'missing or duplicate '+token)
    return [x for x in argv if x!=token]


def _replace_output(argv, flag, expected, replacement):
    _need(argv.count(flag)==1, 'ambiguous '+flag)
    i=argv.index(flag)
    _need(i+1<len(argv) and argv[i+1]==expected, 'wrong '+flag+' output')
    result=list(argv); result[i+1]=replacement
    return result


def historical_baseline():
    """Historical source-only input, not a live observation or admission."""
    raw=(HERE/'COMMANDS.SOURCE-ONLY.json').read_bytes()
    _need(hashlib.sha256(raw).hexdigest()==COMMANDS_SHA256,'command proposal changed')
    doc=json.loads(raw)
    _need(doc.get('authority') is None and doc.get('actual_argv') is None,'unexpected command authority')
    cmds=doc['historical_sdk_command_profile']['commands']
    _need(type(cmds) is list and [c['stage'] for c in cmds]==[
        'Rust object plus depinfo','GCC14 generic C object plus depfile',
        'GCC14 architecture C object plus depfile','GNU ld 2.41 raw eleven-input image'], 'baseline shape')
    for c in cmds:
        _need(c.get('actual') is None and c.get('cwd')=='/work/output/build/kernel','baseline cwd or actual')
        _argv(c['argv'])
    return cmds


def witness_template(generic):
    """Separate C object; never overwrite the production C object/depfile."""
    result=_replace_output(generic,'-o','CMakeFiles/mckernel.img.dir/syscall.c.o',WITNESS_OBJECT)
    result=_replace_output(result,'-MF','CMakeFiles/mckernel.img.dir/syscall.c.o.d',WITNESS_DEPFILE)
    _need(PERF_WITNESS not in result,'witness already in base')
    _need(result[-1]=='/src/kernel/syscall.c','generic source differs')
    result.insert(len(result)-1,PERF_WITNESS)
    return result


def check_argv_data(rust_argv,generic_argv,arch_argv,witness_argv):
    """Exact comparisons only; arguments are unauthenticated input DATA.

    Current profile intentionally refuses operation. The separate observer must
    bind these arrays to actual emitted/executed commands, executable identity,
    include/macro closure, output path and a live source/custody session. Even a
    successful return here is not source selection, build or original389 proof.
    """
    base=historical_baseline(); rust,generic,arch=(_argv(x) for x in (rust_argv,generic_argv,arch_argv))
    witness=_argv(witness_argv)
    _need(rust==base[0]['argv'],'Rust command differs from exact source-only selector proposal')
    _need(generic==base[1]['argv'],'generic command differs from exact source-only selector proposal')
    _need(ORIGIN_GUARD not in base[2]['argv'],'guard unexpectedly present in historical baseline')
    _need(_single_remove(arch,ORIGIN_GUARD)==base[2]['argv'],'architecture command differs or guard absent')
    _need(witness==witness_template(generic),'separate perf ABI witness command differs')
    return {'status':DATA_STATUS,'authority':None,'original389':None,'effective_view':None,
            'source_and_include_closure':None,'executed_command_identity':None,'selected_artifact':None}


def accept_actual_compiler_result(*_args,**_kwargs):
    raise ValueError('SOURCE_ONLY: authenticated actual compiler observation and original389 remain unbound')
