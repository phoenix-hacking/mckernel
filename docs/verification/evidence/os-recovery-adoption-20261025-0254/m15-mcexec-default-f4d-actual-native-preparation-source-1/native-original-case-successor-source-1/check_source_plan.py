"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure exact-case/source checks. No compose, guest, resource or account operation.
"""
import ast,copy,hashlib,importlib.util,json,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
from bind_composed_case import PLAN,PLAN_SHA,ref,bound,module

def main():
    start=time.monotonic();p=json.loads(PLAN.read_bytes());assert ref(PLAN)['sha256']==PLAN_SHA;loader=bound(p['installed_loader_acceptance']);assert loader['actual_executor_sha256']==p['selected_executor']['sha256'];checks=['actual_installed_loader_acceptance8417_exact_subject']
    original=json.loads((HERE.parent/'SOURCE-BOUND-NATIVE-CONTRACT.json').read_bytes());nd=module('pure_original_case_bound_evaluator',p['diagnostic'])
    for key,case in p['cases'].items():
        m=case['manifest_proposal'];old=original['cases'][case['case_id']];assert m['payload']['argv']==old['argv'] and m['payload']['oracle']==old['oracle'] and m['payload']['cwd']==old['cwd'] and m['payload']['env']==old['environment'];assert m['artifacts']['payload']['sha256']==old['payload']['sha256'];assert m['artifacts']['mcexec']==p['selected_executor'];nd._validate_payload_argv(m['payload']['argv']);nd._validate_cleanup_profile(m['cleanup_profile'],m['modules']);assert nd._begin_process_case(m)==(key=='strict235');assert m['staging']['derived_initramfs'] is None;assert not Path(case['expected_output']).exists();checks.append(key+'_original_oracle_payload_argv_exact_current_BEGIN_profile_accepted')
        assert case['overlay_command']['argv'][6]==p['selected_executor']['path']
    assert '' in p['cases']['startup']['manifest_proposal']['payload']['argv'];checks.append('startup_empty_argument_preserved')
    assert len(bytes.fromhex(p['cases']['strict235']['manifest_proposal']['payload']['oracle']['stdout_hex']))==235;checks.append('strict_original235_bytes_preserved')
    f05=bound(p['frozen_F05_manifest']);assert f05['artifacts']['mcexec']['sha256']==original['f05_current_frozen_launcher'];assert f05['case_id']=='M14-05-05-owned-processvm-v2-204B';checks.append('foreground_F05_case_and_C_launcher_untouched')
    assert p['compose_profile_proposal']['aggregate_memory_ceiling_bytes']==23259332608;checks.append('actual_current_aggregate_cap')
    ast.parse((HERE/'bind_composed_case.py').read_bytes());checks.append('future_binder_AST_valid_no_stage_calls')
    result=dict(status='PASS_PURE_ORIGINAL_CASE_SUCCESSOR_SOURCE_BINDINGS',scope=p['scope'],checks=checks,seconds=time.monotonic()-start,actual_compose_native_resources_ledger=False,execution_authority=False);(HERE/'PURE-TEST-RESULT.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
