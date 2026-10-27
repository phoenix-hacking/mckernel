"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure namespace resolution and unchanged host vendor-validator source checks.
No Docker, compiler, capture helper main, native/query or account guard.
"""
import ast,json,time
from pathlib import Path
import execution_contract as c
import run_mcexec_current as wrapper
import audit_container_closure as audit
def reject(fn):
    try:fn()
    except ValueError:return
    raise AssertionError('negative mount control accepted')
def main():
    begin=time.monotonic();o=c.owner();p=o.LIBRARY_PREPARATION;co=o.PREPARATION.parent;failed=co/'workspace/native-running-modules-owner-ea96c79fb14fa362522b690615e25f4f/owner-receipt.json';request=json.loads(failed.read_bytes())['request'];old=o.mounts(request);extra=wrapper.authority_mount(o);new=wrapper.extend_mounts(old,extra);checks=[]
    assert audit.resolve(extra[1],old) is None;checks.append('actual_missing_authority_reproduced_in_old_mount_table')
    assert new[:-1]==old and len(new)==len(old)+1 and audit.resolve(extra[1],new)==dict(host=extra[0],readonly=True,mount_destination=extra[1]);checks.append('exact_samepath_authority_only_readonly_mount_added')
    assert wrapper.extend_mounts(new,extra)==new;checks.append('identical_authority_mount_deduplicated')
    reject(lambda:wrapper.extend_mounts(old,(extra[0],extra[1],False)));checks.append('writable_authority_rejected')
    reject(lambda:wrapper.extend_mounts(old,(extra[0],'/different',True)));checks.append('alias_rewrite_rejected')
    reject(lambda:wrapper.extend_mounts(old+[('/different',extra[1],True)],extra));checks.append('conflicting_authority_target_rejected')
    vendor=p['libdwarf_vendor'];validated=o.validate_libdwarf_vendor(vendor,p['runtime']['vendor_source'],host_identity=True);assert validated['verified_vendor_files']==412;checks.append('unchanged_exact_vendor_authority_commit_and_all412_file_validator_pass')
    root=Path(p['runtime']['source_root']);target=root/Path(vendor['container_root']).relative_to('/src');assert target.is_dir() and not target.is_symlink();checks.append('previous_empty_mountpoint_shape_repair_still_present')
    for row in p['retained_prefix_files']:
        resolved=audit.resolve(str(Path('/retained-f4d')/row['relative']),new);assert resolved['readonly'] and resolved['host']==str(Path(p['runtime']['retained_prefix_root'])/row['relative'])
    checks.append('all10_retained_prefix_inputs_resolve_readonly')
    for row in p['closure']:assert audit.resolve(row['path'],new)['readonly']
    checks.append('all27_driver_support_inputs_resolve_readonly')
    alias='/src/executer/user/lib/libdwarf/libdwarf/libdwarf/config.h.in.cmake';resolved=audit.resolve(alias,new);assert resolved['host']==str(Path(p['runtime']['vendor_source'])/'libdwarf/config.h.in.cmake');checks.append('longest_nested_vendor_mount_resolves_before_parent_source')
    source=Path(o.DRIVER).read_bytes();tree=ast.parse(source);assert next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='validate_libdwarf_vendor');checks.append('driver_and_all_stable_FD_vendor_validators_unchanged')
    result=dict(status='PASS_EXPERT_INPUT_CLOSURE_CONTROLS',scope=c.pins()['scope'],checks=checks,seconds=time.monotonic()-begin,original_runtime19=c.pins()['source_sha256'],actual_container_workload=False,actual_guard_or_resource_query=False,source_root_mutation=False,execution_authority=False)
    (c.HERE/'PURE-TEST-RESULT.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps(dict(status=result['status'],checks=len(checks),seconds=result['seconds'],actual_container=False)))
if __name__=='__main__':main()
