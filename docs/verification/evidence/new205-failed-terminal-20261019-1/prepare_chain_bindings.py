"""Finite failure-only command DATA; no operation executed and no release issued."""
from pathlib import Path
import ast
import hashlib
import json

F = Path(__file__).resolve().parent
A = F.parent
OLD_A = Path('/home/holden/mckernel-work/host-preparation/future-four-callback-compiler-preparation-20261019-1')
OLD = OLD_A / 'terminal-preparation-1/failure-preparation-1'

def ref(path):
    path = Path(path)
    return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(), bytes=path.stat().st_size)

def put(name, value):
    with (F / name).open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')

def global_value(text, name):
    node = next(n for n in ast.parse(text).body if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id == name)
    if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == 'Path':
        return Path(ast.literal_eval(node.value.args[0]))
    return ast.literal_eval(node.value)

def main():
    retention = (F / 'retain_failed_logs.py').read_text()
    payload = dict(schema='mckernel.rust-image.finite-retention-release.v1', status='NOT_RELEASED_SOURCE_AND_EXECUTION_REVIEW_PENDING', author='/root/clone_thread_affinity_rust_repair', boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(), observer={k:v for k,v in ref(F / 'retain_failed_logs.py').items() if k != 'bytes'}, engine={k:v for k,v in ref(global_value(retention, 'ENGINE')).items() if k != 'bytes'}, join={k:v for k,v in ref(global_value(retention, 'JOIN')).items() if k != 'bytes'}, output=str(F / 'retained-production-objects'), resource_profile=global_value(retention, 'PROFILE'), physical_join=global_value(retention, 'PHYSICAL_JOIN'), artifacts=json.loads((F / 'failed-log-original-authorities.json').read_bytes()), failed_operation_sources=ref(F / 'failed-operation-source-references.json'), source_review=None, acceptance=dict(production_image=False, native=False, physical_release=False, cleanup=False))
    put('failed-retention-release-payload-DRAFT.json', payload)
    old = json.loads((OLD / 'failure-terminal-command-set-v2.json').read_bytes())
    oldpins = json.loads((OLD / 'failure-helper-source-pins.json').read_bytes())
    hashes = {}
    for name, row in oldpins.items():
        hashes[row['sha256']] = ref(F / name)['sha256'] if (F / name).exists() else 'PENDING_GENERATION_FROM_GENUINE_RETAINED_PAIR_MAP'
    def bind(value):
        if isinstance(value, dict):
            return {key:bind(item) for key,item in value.items()}
        if isinstance(value, list):
            return [bind(item) for item in value]
        if isinstance(value, str):
            return hashes.get(value, value.replace(str(OLD), str(F)).replace(str(OLD_A), str(A)).replace('future-four-callback-failed-observation-1', 'new205-failed-observation-1'))
        return value
    stages = bind(old['ordered_stages'])
    # No old authority or publication identity is allowed to look actual here.
    for stage in stages:
        argv = stage['argv']
        for flag, marker in [('--failed-authority-sha256','PENDING_INDEPENDENT_ACTUAL_FAILURE_AUTHORITY_SHA256'), ('--git-commit','PENDING_EXACT_FETCHED_SOURCE_COMMIT'), ('--git-tree','PENDING_EXACT_FETCHED_SOURCE_TREE'), ('--release-sha256','PENDING_INDEPENDENT_STAGE_RELEASE_SHA256')]:
            if flag in argv:
                argv[argv.index(flag)+1] = marker
        stage['execution_authorized'] = False
    stages[-1]['expected_FD_cardinality'] = 24
    retention_command = ['/usr/bin/taskset','-c','6','/usr/bin/prlimit','--cpu=30','--as=1073741824','--fsize=33554432','--core=0','--nofile=256','/usr/bin/timeout','--signal=TERM','--kill-after=2s','35s','/home/holden/anaconda3/bin/python3','-I','-B',str(F / 'retain_failed_logs.py'),'--release',str(F / 'retention-execution-release.json'),'--release-sha256','PENDING_INDEPENDENT_RETENTION_RELEASE_SHA256']
    chain = dict(schema='mckernel.new205.failed-terminal-finite-chain-data.v1', status='NOT_RELEASED_DATA_ONLY', implementation_author='/root/clone_thread_affinity_rust_repair', execution_authorized=False, retention=dict(argv=retention_command, payload=ref(F / 'failed-retention-release-payload-DRAFT.json'), capture=str(F / 'actual-retention-run-1'), profile=payload['resource_profile']), post_retention_source_generation=[dict(argv=['/home/holden/anaconda3/bin/python3','-I','-B',str(F / 'finalize_failed_terminal.py')], requires='genuine12pair map; source-only, no root/observer', outputs=['cleanup_failed.py','observe_failed_retirement.py','readback_observer.py','read_original_five_metadata.py','export_raw_five.py','postjoin_readback.py','failure-helper-source-pins.json']), dict(argv=['/home/holden/anaconda3/bin/python3','-I','-B',str(F / 'prepare_failure_authority_data.py'),'--retention-status',str(F / 'actual-retention-run-1/status.json'),'--retention-release',str(F / 'retention-execution-release.json'),'--retention-review','PENDING_GENUINE_INDEPENDENT_RETENTION_REVIEW_PATH'], requires='actualretention direct0, release and independent actual review', outputs=['FAILED-BUILD-PRESERVATION-AUTHORITY-DRAFT.json'])], authority='independent reviewer must bind genuine authority; author DATA stays NOT_RELEASED', publication='exact helper/dependency/authority sources must be published and fetched byte-exact before observer release', ordered_stages=stages, original_five_status='DECLARED_NOT_OBSERVED', raw_five_gate='actual original-five FDs + distinct actual observer/summary + metadata/fullhash joins required before typed raw5 release', cleanup_gate='separate actual raw5 and physical cleanup review; canonical cleanup release NO LF; current locked checks remain mandatory', preservation=dict(log_pairs=12, object_metadata_rows=24, entire_failed_host_case_unchanged=True, in_place=[str(A / 'owner-work/output/build'),str(A / 'owner-work/evidence')]), original_dispatcher_success_postjoin_absent=True, genuine_failure_mutex=json.loads((F / 'FAILED-CASE-INPUTS.json').read_bytes())['postjoin_mutex_record'], acceptance=False)
    put('FAILURE-TERMINAL-CHAIN-DRAFT.json', chain)
    print('PREPARED_FINITE_FAILURE_CHAIN_DATA retention=1 sourcegen=2 readonly=4 critical=2 execution=0')

if __name__ == '__main__':
    main()
