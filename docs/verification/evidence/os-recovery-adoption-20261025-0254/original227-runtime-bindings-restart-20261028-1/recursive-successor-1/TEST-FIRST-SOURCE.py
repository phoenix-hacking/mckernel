"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Genuine retained ownership predicates plus synthetic controls; no live observation.
"""
from pathlib import Path
import ast
import copy
import importlib.util
import json
import stat
import types
import prepare_recursive_successor as p

D=p.HERE/'SYNTHETIC-CONTROLS-TEST-1'


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m


def write(path,value):
    p.create(path,value);return p.ref(path)


def main():
    layout=p.prepare(D)
    commonpath=layout['common']/'observe_root59_configured.py'
    source60=layout['current60']/'observe_current60_postjoin.py'
    source61=layout['current61']/'observe_current61_original227.py'
    entry=layout['entry']
    write(D/'SYNTHETIC-ONLY-NOT-RUNTIME-AUTHORITY.json',dict(synthetic_fixture=True,
         no_runtime_release=True, purpose='Pure interface and retained predicate regression only'))
    stub=D/'SYNTHETIC-CONTROL-STUB.py'
    p.source(stub,"""# SYNTHETIC TEST CONTROL ONLY; NEVER AN ACTUAL ACCOUNT OR GUARDIAN CHECK.
from pathlib import Path
import hashlib,json
OPERATION='original227'
BOOT='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
LIMITS=[1793253600,1035704.5689393478,1051042.6959879305]
def configure(row):
 raw=Path(row['path']).read_bytes()
 assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
def guard():return [value-600 for value in LIMITS]
def current_cutoffs():return LIMITS
""")
    guardref=p.ref(stub)
    # The real adapter and real new shared guard are configured only through their
    # pure APIs, using an explicitly synthetic operation/review fixture.
    oldop=p.read(p.E/'new-window-resume-20261028-1/ORIGINAL227-SEALING-OPERATION-1/EXPLICIT-OPERATION-SUCCESSOR.json')
    op=copy.deepcopy(oldop);op.update(operation_cutoffs=p.LIMITS,
        guardian=dict(source=p.ref(p.GUARDIAN),entrypoint='guard'),
        subjects=dict(test_source=p.ref(source61)),source_owners=['/root','/root/original227'])
    opref=write(D/'SYNTHETIC-OPERATION.json',op)
    reviewref=write(D/'SYNTHETIC-OPERATION-REVIEW.json',dict(
        schema='mckernel.independent-operation-window-review.v1',decision='PASS_EXPLICIT_OPERATION_WINDOW_SUCCESSOR',
        independent=True,reviewer='/root/SYNTHETIC_ONLY',operation='original227',successor=op))
    configref=write(D/'SYNTHETIC-GUARD-CONFIG.json',dict(
        schema='mckernel.sealed-operation-guard-adapter-config.v1',operation='original227',
        shared_guard=p.ref(p.SHARED),successor=opref,review=reviewref,subjects=op['subjects']))
    physicalref=p.ref(p.E/'new-window-physical-history-successor-source-20261028-1/physical_history_successor.py')
    physical=load(physicalref['path'],'pure_physical_chain_template')
    historysources=physical.source_chain()
    pr=write(D/'SYNTHETIC-PHYSICAL-REVIEW.json',dict(
        independent=True,implementation_ownership=False,decision='PASS_EXACT_NEW_WINDOW_PHYSICAL_HISTORY_SUCCESSOR',
        successor_source=physicalref,historical_sources=historysources,guard_adapter=guardref,guard_config=configref))
    pc=write(D/'SYNTHETIC-PHYSICAL-CONFIG.json',dict(author='/root',successor_source=physicalref,
        historical_sources=historysources,guard_adapter=guardref,guard_config=configref,independent_review=pr,runtime_authority=None))
    deps=p.read(layout['common']/'ROOT-ACTUAL-RUNTIME-DEPENDENCIES.TEMPLATE.NOT-AUTHORITY.json')
    deps.update(author='/root',account_window_guard=guardref,account_window_guard_configuration=configref,
                physical_history_observer=physicalref,physical_history_configuration=pc)
    cr=dict(independent=True,implementation_ownership=False,
            decision='PASS_EXACT_ROOT59_CONFIGURED_NEW_WINDOW_OBSERVER_DEPENDENCIES',reviewed_observer=p.ref(commonpath))
    for key in ['account_window_guard','account_window_guard_configuration','physical_history_observer','physical_history_configuration']:
        cr['reviewed_'+key]=deps[key]
    deps['independent_dependency_review']=write(D/'SYNTHETIC-COMMON-REVIEW.json',cr)
    commondeps=write(layout['common']/'ROOT-ACTUAL-RUNTIME-DEPENDENCIES.json',deps)
    rd=p.read(layout['current61']/'ROOT61-RUNTIME-DEPENDENCIES.TEMPLATE.NOT-AUTHORITY.json')
    rd.update(author='/root',guard_adapter=guardref,guard_configuration=configref)
    rd['independent_review']=write(D/'SYNTHETIC-ROOT61-REVIEW.json',dict(
        independent=True,implementation_ownership=False,decision='PASS_EXACT_ROOT61_ORIGINAL227_OBSERVER_DEPENDENCIES',
        observer=p.ref(source61),guard_adapter=guardref,guard_configuration=configref))
    root61deps=write(layout['current61']/'ROOT61-RUNTIME-DEPENDENCIES.json',rd)
    facade=p.read(entry/'ROOT-ACTUAL-OPERATION-GUARD-BINDING.TEMPLATE.NOT-AUTHORITY.json')
    facade.update(author='/root',configuration=configref)
    facade['independent_review']=write(D/'SYNTHETIC-FACADE-REVIEW.json',dict(
        independent=True,implementation_ownership=False,decision='PASS_EXACT_ORIGINAL227_GUARD_CONFIGURATION_BINDING',
        runtime_facade=facade['runtime_facade'],adapter=facade['adapter'],configuration=configref))
    facadebinding=write(entry/'ROOT-ACTUAL-OPERATION-GUARD-BINDING.json',facade)
    stage=p.ref(p.E/'new-window-observer-guard-independent-review-20261028-1/ORIGINAL227-ROOT61-REVIEW-1/ACTUAL-STAGE-REVIEW-1/INDEPENDENT-ACTUAL-STAGE-ACCEPTANCE.json')
    retained=p.read(p.OLDF/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json')
    q=dict(author='/root',decision='COMPOSE_RESTART_ORIGINAL227_SOURCE_ONLY',runtime_authority=None,
           synthetic_fixture_not_authority=True,preserve_reserved_nonce_without_replaying_nonce_binding=True,
           source_delta_manifest=p.ref(D/'EXACT-SOURCE-DELTAS.json'),common_dependencies=commondeps,
           root61_dependencies=root61deps,facade_binding=facadebinding,
           current_observer_source_review=rd['independent_review'],source_authority=retained['source_authority'],
           case_capability=retained['case_capability'],stage_map_acceptance=stage)
    inputpath=D/'SYNTHETIC-COMPOSE-INPUT.json';write(inputpath,q)
    composed=p.compose(inputpath,D)
    # Real facade/config APIs only; configured/current_cutoffs have no actual guard call.
    facade_module=load(entry/'runtime_guard.py','synthetic_facade_pure_configuration')
    assert list(facade_module.current_cutoffs())==p.LIMITS
    root=load(source61,'synthetic_root61_retained_data')
    ledger,free,ext,actors=root.validate_current(root.CURRENT)
    assert len(ledger['consumed_nonces'])==70 and free['current_free'] is True
    # Use exact retained bytes as the independent leaf oracle. The only substituted
    # external effects are fake controls, procfs reads and exact command replies.
    capture=p.read(p.OLD60/'ACTUAL-POSTJOIN-OBSERVATION-2-CPU0.json')
    history=capture['historical_Root59_native_and_physical']
    leaf=history['historical_physical_reobservation']
    queries={tuple(row['argv']):row for row in history['current115_exact_CID_queries']+history['native_exact_CID_queries']+capture['queries']}
    calls=[]
    def run(argv,**kwargs):
        row=queries[tuple(argv)];calls.append(list(argv))
        return types.SimpleNamespace(returncode=row['returncode'],stdout=row['stdout'],stderr=row['stderr'])
    class ProcPath:
        def __init__(self,path):self.path=path
        def exists(self):return False
        def read_text(self):
            assert self.path in ['/proc/locks','/proc/net/unix']
            return '' if self.path=='/proc/locks' else 'Num RefCount Protocol Flags Type St Inode Path\n'
        def stat(self):
            assert self.path=='/run/lock/mckernel-development.lock'
            return types.SimpleNamespace(st_mode=stat.S_IFREG|0o600,st_dev=27,st_ino=4)
    def path_factory(*parts):
        path=str(Path(*parts))
        return ProcPath(path) if path.startswith('/proc/') or path=='/run/lock/mckernel-development.lock' else Path(*parts)
    def patched(module):
        if module.__file__ in [str(commonpath),str(source60),str(source61)]:
            module.Path=path_factory
            if hasattr(module,'subprocess'):module.subprocess=types.SimpleNamespace(run=run)
            original=module.load
            def wrapped(row,name):return patched(original(row,name))
            module.load=wrapped
        elif module.__file__==physicalref['path']:
            original=module.configure
            def configure(row):
                original(row)  # Full actual physical config/source/review authentication.
                module.observe=lambda:copy.deepcopy(leaf)
            module.configure=configure
        return module
    patched(root)
    result=root.observe()
    assert result['Root61']==root.CURRENT['ledger']
    assert result['actual_latest_operation_postjoin_acceptance']==root.CURRENT['latest_free']
    assert result['no_existing_heavy'] and result['pids_current']==0
    assert result['fixed_cutoffs']==p.LIMITS
    assert len(result['closed_exclusive_probes'])==2 and not result['group_membership_observation']['errors']
    # The existing binder accepts the complete Root61 output/resource shape unchanged.
    binder=load(entry/'bind_startup_resource.py','pure_original227_resource_binder')
    static=p.read(composed['static']['path'])
    resource=dict(actual_latest_operation_postjoin_acceptance=root.CURRENT['latest_free'],
                  boot_id=result['boot_id'],no_existing_heavy=True,pids_current=0,
                  root_ledger35=root.CURRENT['ledger'],fixed_cutoffs=p.LIMITS)
    pending=binder.packet_for(static,composed['static'],resource,dict(path='SYNTHETIC_ONLY'),dict(path='SYNTHETIC_ONLY'))
    assert pending['capture_sources']==static['capture_sources'] and pending['fixed_cutoffs']==p.LIMITS
    helper=ast.parse((entry/'run_native_startup_capture.py').read_bytes())
    nodes=[n for n in helper.body if isinstance(n,ast.FunctionDef) and n.name in ['cutoff_triplet','entry_clamps'] or
           isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='AUTHORIZED_FIXED_LIMITS' for t in n.targets)]
    import math
    ns=dict(math=math);exec(compile(ast.Module(body=nodes,type_ignores=[]),'PURE_CLAMPS_ONLY','exec'),ns)
    now=[x-600 for x in p.LIMITS]
    assert ns['entry_clamps'](now,now,p.LIMITS,p.LIMITS,p.LIMITS)['effectiveCutoffs']==p.LIMITS
    bad=copy.deepcopy(resource);bad['root_ledger35']=dict(root.CURRENT['ledger'],sha256='0'*64)
    try:binder.packet_for(static,composed['static'],bad,{}, {})
    except AssertionError:pass
    else:raise AssertionError('wrong ledger accepted')
    summary=dict(decision='PASS_RECURSIVE_RETAINED_PREDICATES_AND_SYNTHETIC_CONTROL_CHAIN_SOURCE_ONLY',
        retained_consumed_nonces=70,retained_actor_rows=len(actors),synthetic_query_replies=len(calls),
        groups=['narrow_source_delta','real_new_adapter_pure_configuration','genuine_Root61_free_history',
                'full_recursive_observer_with_synthetic_effects','unchanged_resource_packet_consumer',
                'strict_clamps_and_wrong_ledger_negative'],actual_guard_calls=0,actual_observations=0,
        actual_subprocesses=0,nonce_calls=0,native_calls=0,runtime_authority=None,composed_synthetic_sources=composed)
    write(p.HERE/'PURE-RECURSIVE-REGRESSION.json',summary)
    print(json.dumps(summary))


if __name__=='__main__':main()
