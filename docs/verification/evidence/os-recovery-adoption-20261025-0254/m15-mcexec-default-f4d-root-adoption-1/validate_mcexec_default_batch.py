"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure, one-cohort default-executor context/receipt validators. No runner or controller.
"""
import hashlib
import json
import re
from pathlib import Path

SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
BUILD='/work/output/m15-executor-sdk-default-1/build'
RUST_OBJECT=BUILD+'/executer/user/rust/mcexec_helpers.o'
ASM_ARCHIVE=BUILD+'/executer/user/libmcexec.a'
EXECUTABLE=BUILD+'/executer/user/mcexec'
SOURCE='/src/executer/user/rust/mcexec_helpers.rs'
CONTEXT_FIELDS=('runtime_sources','rust_command','rust_cwd','generated_BUILDID_rs',
                'top_config_h','ihk_config_h','BUILDID','tool_hashes','image_id',
                'selected_sdk_identity','platform_ABI_prefix','rust_cfg_profile',
                'ASM_source','ASM_flags','ASM_compile_command','ASM_archive_command')

def need(ok,why):
    if not ok:raise ValueError(why)
def canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def bound(reference,document=True):
    raw=Path(reference['path']).read_bytes()
    need(len(raw)==reference['bytes'] and hashlib.sha256(raw).hexdigest()==reference['sha256'],'changed exact input '+reference['path'])
    return json.loads(raw) if document else raw

def decide_prefix(retained,current):
    """Only exact real producer equality can permit object reuse; no path normalization."""
    missing=[key for key in CONTEXT_FIELDS if key not in current or current[key] is None]
    if missing:return dict(decision='HOLD_INCOMPLETE_PRODUCER_CONTEXT',missing=missing,reuse_Rust_object=False,reuse_ASM_archive=False,execution_authority=False)
    changed=[key for key in CONTEXT_FIELDS if retained[key]!=current[key]]
    if changed:
        return dict(decision='CURRENT_COMPILE_REVIEW_REQUIRED',changed_inputs=changed,
                    required_Rust_compile=any(k not in ('ASM_source','ASM_flags','ASM_compile_command','ASM_archive_command') for k in changed),
                    required_ASM_compile=any(k in ('ASM_source','ASM_flags','ASM_compile_command','ASM_archive_command','tool_hashes','image_id','selected_sdk_identity') for k in changed),
                    reuse_Rust_object=False,reuse_ASM_archive=False,execution_authority=False)
    need(current['BUILDID']=='3114d9e','exact retained BUILDID context')
    object_matches=current.get('available_Rust_object')==retained['available_Rust_object']
    archive_matches=current.get('available_ASM_archive')==retained['available_ASM_archive']
    if not object_matches or not archive_matches:
        return dict(decision='MATCHING_PREFIX_INPUTS_REQUIRED',reuse_Rust_object=False,reuse_ASM_archive=False,
                    missing_Rust_object=not object_matches,missing_ASM_archive=not archive_matches,execution_authority=False)
    return dict(decision='REUSE_EXACT_F4D_OBJECT_AND_ASM_ARCHIVE',reuse_Rust_object=True,reuse_ASM_archive=True,
                preserved_producer_context_sha256=hashlib.sha256(canonical({k:current[k] for k in CONTEXT_FIELDS})).hexdigest(),
                Make_target_only_allowed=current.get('all_actual_Make_prerequisites_not_newer') is True,
                link_only_if_metadata_mtime_stale=current.get('all_actual_Make_prerequisites_not_newer') is not True,
                execution_authority=False)

def validate_preconfigure_compute(before):
    # The exact accepted cache seed contains FORCE for this value. Detect a
    # different actual compute binding before configure can change anything.
    need(before.get('RUSTC')=='/nightly/bin/rustc',
         'qualified seed would change compute RUSTC; Root must bind a coherent current seed first')
    return True

def validate_config(snapshot):
    validate_preconfigure_compute(dict(RUSTC=snapshot['compute_RUSTC_before']))
    values=snapshot['cache_values']
    expected=dict(ENABLE_RUST_USER_TOOLS='ON',MCEXEC_ALLOW_C_REFERENCE='OFF',MCEXEC_USER_RUSTC='/nightly/bin/rustc',
                  IHK_USER_RUSTC='/nightly/bin/rustc',IHK_ENABLE_RUST_WHOLE_LIBRARY='ON',IHKLIB_USE_QUALIFIED_EXTERNAL_ARCHIVE='OFF',
                  ENABLE_QLMPI='OFF',ENABLE_TOFU='OFF',ENABLE_UTI='OFF',ENABLE_KMSG_REDIRECT='OFF')
    need(all(values.get(k)==v for k,v in expected.items()),'actual supported default cache/compiler tuple')
    need(snapshot['compute_RUSTC_before']==snapshot['compute_RUSTC_after'],'compute RUSTC changed')
    need(snapshot['source_CMake_sha256']=='1208a097f57f5b9d3deee4d23fc55c7c598d8a88aab9002d4c65ae13a36cea57'
         and snapshot['IHK_user_CMake_sha256']=='a21e1cfbb064a03458201bfbea520d2f04e87ea287f58451d65031e74d728369','source-reviewed composed selectors')
    need(snapshot['selected_mcexec_source_list']==[RUST_OBJECT] and snapshot['ASM_archive_only'] is True,'no project C object in selected target')
    need(snapshot['generated_config_path']==BUILD+'/config.h'
         and snapshot['generated_IHK_config_path']==BUILD+'/ihk/config.h'
         and snapshot['generated_BUILDID_path']==BUILD+'/executer/user/rust/mcexec_buildid_generated.rs','exact actual generated-config paths')
    need(snapshot['top_BUILDID']==snapshot['IHK_BUILDID']==snapshot['Rust_BUILDID'],'generated BUILDID values disagree')
    return True

def validate_link(snapshot):
    need(snapshot['current_generated_link_command']==snapshot['actual_link_command'],'actual selected link argv differs')
    need(snapshot['linked_objects']==[RUST_OBJECT,ASM_ARCHIVE] and snapshot['project_C_objects']==[],'Rust plus reviewed ASM only')
    need(snapshot['Rust_main_unique'] is True and snapshot['ELF64_x86_64_PIE'] is True
         and snapshot['BUILDID_in_ELF']==snapshot['generated_BUILDID'],'actual main/ELF/BUILDID link proof')
    need(snapshot['DT_NEEDED']==snapshot['qualified_DT_NEEDED']
         and snapshot['PT_INTERP']==snapshot['qualified_PT_INTERP']
         and snapshot['dynamic_imports']==snapshot['qualified_dynamic_imports'],'unchanged named import/provider tuple')
    return True

def positive(result):
    return (result['returncode']==0 and all(result[k] is True for k in ('direct_child_joined','group_absent','closed_streams'))
            and result['error'] is None and result['retirement_error'] is None and result['timed_out'] is False)

def validate_batch_receipt(receipt,request,prepared,load=bound):
    need(receipt['schema']=='mckernel.mcexec-default-target-link-install.v1'
         and receipt['status']=='PASS_MCEXEC_DEFAULT_TARGET_LINK_INSTALL_ONLY'
         and receipt['scope']==SCOPE and receipt['nonce']==request['nonce']
         and re.fullmatch('[0-9a-f]{32}',receipt['nonce']) is not None,'one exact default-executor receipt')
    need(receipt['preparation_sha256']==prepared['sha256'] and receipt['request']==request['reference'],'actual request/preparation binding')
    need(all(receipt[k] is False for k in ('native_acceptance','whole_M15','all349_provider_parity','all51_data_ABI','allocation_proof','application_main_executed')),'receipt scope inflation')
    config=load(receipt['actual_config']);validate_config(config)
    prefix=decide_prefix(load(prepared['retained_context']),load(receipt['actual_producer_context']))
    need(receipt['prefix_decision']==prefix,'exact object-reuse or changed-compile decision')
    rows=receipt['commands'];labels=[r['label'] for r in rows]
    wanted=['current-configure','producer-context','current-link','current-ELF-imports','current-install','installed-ELF']
    if prefix['decision']=='REUSE_EXACT_F4D_OBJECT_AND_ASM_ARCHIVE':
        need(not any(label in labels for label in ('current-Rust-compile','current-ASM-compile')),'unchanged successful compiler prefix replayed')
    elif prefix['decision']=='CURRENT_COMPILE_REVIEW_REQUIRED':
        need(receipt['exact_changed_compile_release'] is not None,'changed source/compiler context has no exact release')
        release=load(receipt['exact_changed_compile_release'])
        need(release['status']=='PASS_EXECUTION_RELEASE' and release['nonce']==request['nonce']
             and release['request']=={k:request['reference'][k] for k in ('path','sha256')},'existing exact Root release does not bind changed compile')
        if prefix['required_Rust_compile']:wanted.insert(2,'current-Rust-compile')
        if prefix['required_ASM_compile']:wanted.insert(2,'current-ASM-compile')
    else:raise ValueError('missing actual same-context prefix; retain hold')
    need(labels==wanted and all(positive(row['result']) for row in rows),'exact positive owned commands')
    for row in rows:
        for stream in ('stdout','stderr'):
            capture=row['result']['captures'][stream]
            load(dict(path=capture['path'],bytes=capture['size'],sha256=capture['sha256']),False)
    validate_link(load(receipt['actual_link_proof']))
    installed=load(receipt['actual_install_proof'])
    need(installed['selected_component']=='mcexec_runtime' and installed['installed_path']==prepared['stage']+'/usr/local/bin/mcexec'
         and installed['current_build_ELF']==receipt['current_build_ELF']
         and installed['actual_installed_ELF']==receipt['actual_installed_ELF']
         and installed['only_actual_CMake_install_changes'] is True,'actual selected install artifact')
    return dict(status='VALIDATED_MCEXEC_DEFAULT_TARGET_LINK_INSTALL_ONLY',native_acceptance=False,whole_M15=False)
