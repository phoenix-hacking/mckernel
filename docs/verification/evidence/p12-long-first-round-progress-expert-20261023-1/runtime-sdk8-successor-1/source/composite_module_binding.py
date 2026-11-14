"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private SDK8 successor for the stale composite64 module authority boundary.
Genuine accepted artifact/source/physical receipts are mandatory; snapshot paths
may differ only when their actual bytes match that exact accepted three-tuple.
"""
from pathlib import Path
import importlib.util
D=Path(__file__).resolve().parent
NAMES=('ihk.ko','ihk-smp-x86_64.ko','mcctrl.ko')
def authority():
    spec=importlib.util.spec_from_file_location('private_current68_source_authority',D/'repaired_image_authority.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def validate_module_binding(base):
    a=authority();value=a.links()
    a.need(value['SDK8_source_identity']=='48bbad0aa65de4ad0e96a9cf1c1b96201cf42dbb0d944d6bf91d36d60067414d','exact selected SDK8 source identity')
    source=a.read(value['proofs']['SDK8_source_preparation'])
    a.need(source['status']=='ACTUAL_SDK8_SOURCE_PREPARATION_PASS_NO_STAGE_OR_BUILD' and source['source_identity']==value['SDK8_source_identity'] and source['source_files']==68 and source['changed_rows']==7 and source['unchanged_rows']==61,'actual SDK8 exact seven-source closure')
    review=a.read(value['proofs']['SDK8_source_and_fixture_review'])
    gate=a.read(source['source_acceptance'])
    a.need(review['decision']=='PASS_SOURCE_AND_FOCUSED_ACTUAL_FIXTURE' and review['source_verdict']=='PASS_SOURCE' and review['source_reviewer'] and review['other_six_changes_preserved'] is True,'genuine corrected source review')
    a.need(review['candidate_sha256_by_relative']=={name:row['sha256'] for name,row in gate['candidates'].items()} and len(gate['candidates'])==7 and sorted(gate['candidates'])==gate['changed_relative_rows'],'exact accepted seven-source candidate map')
    tests=a.read(value['proofs']['SDK8_actual_fixture'])
    a.need(review['fixture']==gate['actual_tests']=={key:value['proofs']['SDK8_actual_fixture'][key] for key in ('path','sha256')} and tests['first_original_corrected_pairs']==20 and tests['finite_actual_source_callers']==11 and tests['existing_errors_claims_quarantine_and_calls_unchanged'] is True,'actual corrected caller fixture join')
    a.need(value['proofs']['SDK8_acceptance'] is not None,'genuine actual SDK8 artifact/physical acceptance missing')
    sdk=a.read(value['proofs']['SDK8_acceptance'])
    a.need(sdk['status']=='PASS' and sdk['decision']=='PASS_ACTUAL_SDK8_ARTIFACT_AND_PHYSICAL_ACCEPTANCE' and sdk['physical_acceptance'] is True and sdk['native_acceptance'] is False,'genuine SDK8 artifact/physical acceptance')
    a.need(sdk['source_identity']==value['SDK8_source_identity'] and sdk['observed']['required_exports_vermagic_MM_unique_linkage'] is True,'genuine SDK8 source/export/MM join')
    actual=a.read(sdk['actual_reads']);owner=a.read(sdk['owner_receipt'])
    a.need(actual['source_identity']==sdk['source_identity'] and actual['nonce']==sdk['nonce']==owner['owner_nonce'] and actual['artifacts']==sdk['artifacts'],'SDK8 actual read/source/owner/artifact join')
    a.need(owner['status']=='PASS' and owner['build_status']=='PASS' and owner['cleanup_status']=='PASS_OWNED_REMOVAL_AND_RECORD_RELEASE' and owner['retired'] is True and owner['wait_exit_code']==0,'SDK8 actual owner/compiler/retirement join')
    driver=owner['driver_receipt']
    a.need(driver['status']=='BUILD_ARTIFACT_CHECKS_PASS' and driver['make_returncode']==0 and driver['source_candidate_sha']==sdk['source_identity'],'SDK8 actual compiler source receipt')
    modules=base['modules']
    a.need(type(modules) is list and len(modules)==3 and tuple(Path(r['path']).name for r in modules)==NAMES and set(sdk['artifacts'])==set(NAMES),'exact ordered SDK8 three-module inventory')
    for name,reference in zip(NAMES,modules):
        accepted=sdk['artifacts'][name];produced=driver['artifacts'][Path(name).stem]
        a.need(produced['sha256']==accepted['sha256'] and produced['bytes']==accepted['bytes'],'actual SDK8 produced artifact join')
        a.need(produced['modinfo']['vermagic']=='6.12.0-211.44.1.el10_2.mckernel1.x86_64 SMP preempt mod_unload ','actual SDK8 Linux ABI')
        a.artifact(reference,accepted)
    launcher=a.read(value['proofs']['launcher_build_acceptance']);receipt=a.read(launcher['receipt'])
    a.need(launcher['decision']=='PASS_ACTUAL_M06_LAUNCHER_PRODUCTION_ARTIFACT_ONLY' and launcher['native_acceptance'] is False and receipt['status']=='PASS' and receipt['launcher_source_sha256']==launcher['launcher_source_sha256'],'actual current launcher source/production receipt')
    a.artifact(base['artifacts']['mcexec'],launcher['elf'])

def validate_launcher_member(base,row):
    # This single extra changed-member path is bound to the genuine accepted
    # current launcher. _staging still checks source identity, exact actual
    # file bytes/mode and final-map member correspondence before reaching here.
    a=authority();value=a.links();accepted=a.read(value['proofs']['launcher_build_acceptance'])
    a.need(accepted['decision']=='PASS_ACTUAL_M06_LAUNCHER_PRODUCTION_ARTIFACT_ONLY' and accepted['native_acceptance'] is False,'genuine changed launcher authority')
    expected=accepted['elf'];a.artifact(base['artifacts']['mcexec'],expected)
    a.need(row['sha256']==expected['sha256'] and row['size']==expected['bytes'] and row['mode']==base['artifacts']['mcexec']['mode']==0o100755,'exact accepted changed launcher final member')
