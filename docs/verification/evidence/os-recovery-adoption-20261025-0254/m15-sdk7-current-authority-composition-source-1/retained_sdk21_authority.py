"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure retained-evidence validation; no imports from any runtime owner.
"""
from pathlib import Path
import hashlib
import json


def bound(ref):
    raw = Path(ref['path']).read_bytes()
    if len(raw) != ref['bytes'] or hashlib.sha256(raw).hexdigest() != ref['sha256']:
        raise ValueError('retained evidence changed: ' + ref['path'])
    return json.loads(raw)


def validate_current(physical, artifact):
    if physical['schema'] != 'mckernel.bfd-sdk-a482.new18h.independent-current-physical-acceptance.v1':
        raise ValueError('current new18h schema required')
    if physical['status'] != 'PASS_ACTUAL_CURRENT_PHYSICAL_AND_POSTJOIN_NORMAL_RETIREMENT':
        raise ValueError('current physical acceptance required')
    for key in ('physical_acceptance', 'current_postjoin_acceptance', 'publishers_empty',
                'all_containers_exited', 'owned_CID_name_nonce_absent',
                'retained_inventories_exact', 'three_owned_records_absent',
                'three_raw_archives_exact'):
        if physical[key] is not True:
            raise ValueError('current acceptance missing: ' + key)
    if physical['implementation_ownership'] is not False or physical['heavy_execution_released'] is not False:
        raise ValueError('independent current evidence cannot grant execution')
    if physical['additional_observer_or_cleanup_required'] is not False:
        raise ValueError('unresolved physical observation')
    mutex = physical['permanent_mutex']
    if mutex != dict(device=27, inode=4, unchanged=True, free_before=True, free_after=True, flock_operations=0):
        raise ValueError('permanent mutex evidence differs')
    direct = physical['direct_child']
    if direct['returncode'] != 0 or any(direct[k] is not True for k in ('direct_child_joined', 'group_absent', 'closed_streams', 'stderr_empty')):
        raise ValueError('current observer join incomplete')
    if direct['error'] is not None or direct['retirement_error'] is not None:
        raise ValueError('observer retirement error')
    if artifact['decision'] != 'PASS_SDK_SUPPORTED_TOOLS_ARTIFACTS_ONLY' or artifact['contract'] != 'm15.bfd.supported-tools':
        raise ValueError('SDK21 artifact scope differs')
    if artifact['implementation_ownership'] is not False or artifact['logical_commands'] != 21:
        raise ValueError('SDK21 independent evidence differs')
    if artifact['normal_retirement_acceptance_sha256'] != physical['normal_retirement_acceptance_sha256']:
        raise ValueError('artifact and physical evidence have different retirement')
    if artifact['full_installation_default_native_whole_file_C_retirement_acceptance'] is not False:
        raise ValueError('artifact scope must remain narrow')
    # Original owner failure is preserved even though later artifact checking passed.
    if physical['original_owner_workload_status'] != 'FAIL: BFD qualification artifact missing':
        raise ValueError('original owner failure must remain preserved')
    return True
