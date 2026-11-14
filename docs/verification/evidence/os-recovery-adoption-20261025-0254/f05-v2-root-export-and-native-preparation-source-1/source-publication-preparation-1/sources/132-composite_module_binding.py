"""Exact composite64 binding. No old-module fallback or inferred acceptance."""
from pathlib import Path
import hashlib,json,stat
D=Path(__file__).resolve().parent
NAMES=('ihk.ko','ihk-smp-x86_64.ko','mcctrl.ko')
IMAGE='ff4fca457e9ffe50dc4eca930c5f91faf317eeee15bf0c2907067cffa77b23bb'
def exact(r):
    p=Path(r['path']);s=p.stat();data=p.read_bytes()
    if set(r)!={'path','sha256','size','mode'} or not stat.S_ISREG(s.st_mode) or s.st_size!=r['size'] or s.st_mode!=r['mode'] or hashlib.sha256(data).hexdigest()!=r['sha256']:raise ValueError('exact composite descriptor drift')
    return data
def validate_module_binding(base):
    b=json.loads((D/'COMPOSITE-MODULE-BINDING.json').read_bytes())
    if b['status']!='ACTUAL_ACCEPTED_EXACT_COMPOSITE64':raise ValueError('composite acceptance pending')
    if base['artifacts']['mckernel_image']['sha256']!=IMAGE:raise ValueError('accepted205 image identity')
    if tuple(Path(r['path']).name for r in base['modules'])!=NAMES or base['modules']!=b['modules']:raise ValueError('exact composite three-module tuple')
    for r in b['modules']:exact(r)
    artifact=json.loads(exact(b['actual_artifact_review']));physical=json.loads(exact(b['actual_physical_review']))
    # Filled only from the genuine independently accepted composite64 reports.
    # A source proposal intentionally cannot fabricate their contract.
    validate_actual_reviews(b,artifact,physical)
def validate_actual_reviews(binding,artifact,physical):
    def need(ok,why):
        if not ok:raise ValueError(why)
    def read(r):
        p=Path(r['path']);raw=p.read_bytes()
        need(len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256'],'complete authoritative descriptor drift')
        return json.loads(raw)
    need(artifact['schema']=='mckernel.current-v6-composite-sdk.actual-module-source-abi-link-review.v1' and artifact['status']=='PASS','exact composite artifact kind')
    need(artifact['decision']=='ACCEPT_EXACT_CORRECTED_COMPOSITE64_CURRENT_SDK_THREE_MODULE_SOURCE_FFI_COMPILE_LINK_AND_MM_PROVIDER_CONTRACT','exact composite artifact decision')
    need(physical['schema']=='mckernel.current-v6-composite-sdk.actual-physical-retirement-review.v1' and physical['status']=='PASS' and physical['decision']=='PASS_PHYSICAL_RETIREMENT_ALLOCATOR_CORRECTION1_COMPOSITE64','exact SDK physical kind')
    for key in ('build_artifact_acceptance','current_SDK_FFI_compile_and_link_contract_acceptance','actual_MM_provider_link_acceptance'):need(artifact[key] is True,'actual SDK acceptance '+key)
    for key in ('module_load_acceptance','native_acceptance','production_default_activation_acceptance','ACK_acceptance'):need(artifact[key] is False,'do not upgrade build acceptance '+key)
    for key in ('physical_release','outer_direct_joined','outer_group_absent','all_owned_groups_empty','current_owned_records_absent','root_development_lock_reacquired_before_owner_return'):need(physical[key] is True,'actual physical retirement '+key)
    need(physical['outer_returncode']==0 and physical['container_absent'] is True,'closed genuine SDK owner')
    need(artifact['physical_review']=={'path':binding['actual_physical_review']['path'],'sha256':binding['actual_physical_review']['sha256'],'bytes':binding['actual_physical_review']['size']},'full physical review join')
    need(artifact['request']==physical['request']==binding['request'],'same exact SDK request')
    receipt=read(binding['driver_receipt']);request=read(binding['request'])
    need(artifact['driver_receipt']==binding['driver_receipt'] and receipt['status']=='BUILD_ARTIFACT_CHECKS_PASS' and receipt['make_returncode']==0,'actual compiler receipt')
    need(receipt['source_candidate_sha']==artifact['source_candidate_sha']==binding['source_candidate_sha'] and receipt['artifacts']==artifact['artifacts'],'actual source/artifact receipt join')
    for r in binding['modules']:
        name=Path(r['path']).stem;row=artifact['artifacts'][name]
        need(Path(r['path'])==Path(request['candidate_root'])/'modules'/(name+'.ko') and row['sha256']==r['sha256'] and row['bytes']==r['size'],'actual exact module path/hash/size')
        need(row['modinfo']['vermagic']=='6.12.0-211.44.1.el10_2.mckernel1.x86_64 SMP preempt mod_unload ','accepted Linux SDK release')
    prior=json.loads(exact(binding['prior_abi_review']))
    for name,sha in binding['unchanged_public_abi'].items():need(prior['public_source_ABI_unchanged'][name]==artifact['source_sha256'][name]==sha,'unchanged ordinary public ABI '+name)
    ad=binding['additive_application_abi'];old=exact(ad['old']);new=exact(ad['new']);pos=ad['offset']
    need(new==old[:pos]+bytes.fromhex(ad['extension_hex'])+old[pos:] and ad['old']['sha256']==prior['public_source_ABI_unchanged']['abi/application.rs'] and ad['new']['sha256']==artifact['source_sha256']['abi/application.rs'],'additive preparation-only application ABI source')
