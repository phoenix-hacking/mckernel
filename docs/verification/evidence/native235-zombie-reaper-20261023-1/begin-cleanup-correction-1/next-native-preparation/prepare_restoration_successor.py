"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite BEGIN two-member restoration source/template derivative; no archive/stage/native.
"""
from pathlib import Path
import ast,copy,difflib,hashlib,json
E=Path(__file__).resolve().parent
F=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/begin-cleanup-native-successor-2')
OLD=Path('/home/holden/mckernel-work/host-preparation/native235-zombie-sdk-successor-20261023-1/restoration-batch-preparation')
J=F/'restoration-batch-readiness-1';S=J/'stage-binding';S.mkdir(mode=0o700,parents=True,exist_ok=False)
PROFILE='current68-begin-cleanup-build-link-physical'
PROFILE_ID='current68-begin-db7f-image10972-launcherdca0-p05-short32'
MEMBERS=['modules/ihk-smp-x86_64.ko','modules/mcctrl.ko']
def load(p):return json.loads(p.read_text())
def ref(p):b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),size=len(b),mode=p.stat().st_mode)
def save(p,d):
 with p.open('x')as f:json.dump(d,f,sort_keys=True,indent=2);f.write('\n')
def source(p,s):ast.parse(s);p.write_text(s)
oldsource=OLD/'stage-binding/stage_m05_two_generation.py';assert ref(oldsource)['sha256']=='2b4bbfdf23e6ad58f9693fd0fc5c2ea7e8472f829ee9a347d1de00044acf635d'
binding=load(OLD/'stage-binding/BINDING.json');assert ref(OLD/'stage-binding/BINDING.json')['sha256']=='cd417a65ed6dc110796478e8e31a0511f4b8388c6686e1c57209b728b470e085'
binding['authority_profile']=PROFILE
binding['authority']['current_SDK_acceptance']=dict(path=None,sha256=None,size=None,mode=None)
binding['authority'].pop('zombie_snapshot_binding')
binding['authority']['begin_snapshot_binding']=dict(path=str(F/'TWO-RECORD-BASE-PATCH-INPUTS.ACTUAL.json'),sha256=None,size=None,mode=None)
for member in MEMBERS:binding['replacements'][member]=dict(path=str(F/'runtime-inputs'/Path(member).name),sha256=None,size=None,mode=33188)
binding['output']=str(S/'actual-stage-1');save(S/'BINDING.PENDING.json',binding)
s=oldsource.read_text();begin=s.index("    elif profile == 'current68-zombie-reaper-build-link-physical':");end=s.index("    else:\n        need(False, 'unknown SDK authority profile')",begin)
branch="""    elif profile == 'current68-begin-cleanup-build-link-physical':
        need(binding['authority']['current_SDK_acceptance']['path'] == SDK_SUCCESSOR_PATH
             and binding['authority']['current_SDK_acceptance']['sha256'] == SDK_SUCCESSOR_SHA
             and sdk['status'] == 'PASS' and sdk['implementation_ownership'] is False
             and sdk['decision'] == SDK_SUCCESSOR_DECISION
             and sdk['physical_acceptance'] is True and sdk['native_acceptance'] is False
             and sdk['source_identity'] == 'db7f2ac4ddc023874ddf6b2b8de2c86c41bbf6efb601f33d4d0f501aa1957598',
             'exact independent BEGIN SDK authority')
        patched = docs['begin_snapshot_binding']
        members = ['modules/ihk-smp-x86_64.ko', 'modules/mcctrl.ko']
        need(binding['authority']['begin_snapshot_binding']['path'] == SNAPSHOT_BINDING_PATH
             and binding['authority']['begin_snapshot_binding']['sha256'] == SNAPSHOT_BINDING_SHA
             and patched['matched_artifact_acceptance']['sdk']['path'] == SDK_SUCCESSOR_PATH
             and patched['matched_artifact_acceptance']['sdk']['sha256'] == SDK_SUCCESSOR_SHA
             and patched['changed_record_allowlist'] == members
             and set(patched['new_runtime_tuple']) == set(members)
             and all(patched['new_runtime_tuple'][member] == binding['replacements'][member]
                     for member in members), 'exact accepted SMP+mcctrl snapshot join')
        receipt = docs['v3_snapshot_receipt']
        need(binding['authority']['v3_snapshot_receipt']['sha256'] == '7eaaffb59663f27943c2f766ff4d737d790ade99349574349ba9453afa5cd33d'
             and receipt['status'] == 'PASS_THREE_ACTUAL_EXCLUSIVE_MODULE_RUNTIME_SNAPSHOTS'
             and [row['name'] for row in receipt['modules']] == ['ihk.ko','ihk-smp-x86_64.ko','mcctrl.ko'],
             'unchanged accepted IHK snapshot receipt')
        row = next(row for row in receipt['modules'] if row['name'] == 'ihk.ko')
        need(row['copied'] == binding['replacements']['modules/ihk.ko'],
             'exact unchanged IHK descriptor')
"""
new=s[:begin]+branch+s[end:]
new=new.replace("profile == 'current68-zombie-reaper-build-link-physical'","profile == 'current68-begin-cleanup-build-link-physical'")
new=new.replace("'current68-v3-build-link-physical', 'current68-zombie-reaper-build-link-physical'","'current68-v3-build-link-physical', 'current68-begin-cleanup-build-link-physical'")
tree=ast.parse(new);lines=new.splitlines(True)
values={'BINDING_SHA256':None,'SDK_SUCCESSOR_PATH':None,'SDK_SUCCESSOR_SHA':None,'SNAPSHOT_BINDING_PATH':str(F/'TWO-RECORD-BASE-PATCH-INPUTS.ACTUAL.json'),'SNAPSHOT_BINDING_SHA':None}
for node in sorted([n for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id in values for t in n.targets)],key=lambda n:n.lineno,reverse=True):lines[node.lineno-1:node.end_lineno]=[node.targets[0].id+' = '+repr(values[node.targets[0].id])+'\n']
new=''.join(lines).replace('MEMBERS = {','SDK_SUCCESSOR_DECISION = None\nMEMBERS = {',1)
source(S/'stage_m05_two_generation.TEMPLATE.py',new)
(E/'BEGIN-RESTORATION-AUTHORITY-DELTA.patch').write_text(''.join(difflib.unified_diff(s.splitlines(True),new.splitlines(True),fromfile=str(oldsource),tofile=str(S/'stage_m05_two_generation.TEMPLATE.py'))))
argv=load(OLD/'stage-binding/READY-ACTUAL-P05-STAGE-ARGV.json');assert argv[2]=='7';argv[-2]=str(S/'stage_m05_two_generation.py');save(S/'READY-ACTUAL-P05-STAGE-ARGV.PENDING.json',argv)
for name in ['run_actual_current68_m05_stage_once.py','check_authority_only.py']:(S/(name.replace('.py','.PREDECESSOR.py'))).write_bytes((OLD/'stage-binding'/name).read_bytes())
for name in ['join_restoration_batch_receipts.py','run_ten_cycles.py']:(J/name).write_bytes((OLD/name).read_bytes())
deriver=(OLD/'derive_fixed_batch.py').read_text();deriver=deriver.replace("PROFILE_ID='current68-zombie-d8d8-image10972-launcherdca0-p05-short32'",'PROFILE_ID='+repr(PROFILE_ID))
oldline="SDK=Path('/home/holden/mckernel/docs/verification/evidence/native235-zombie-reaper-20261023-1/sdk-build-release/INDEPENDENT-ACTUAL-SDK-ARTIFACT-AND-PHYSICAL-ACCEPTANCE.json')"
assert oldline in deriver;deriver=deriver.replace(oldline,'SDK=None\nSDK_SHA=None');deriver=deriver.replace("manifest=bound(profile['manifest']);sdk=json.loads(SDK.read_text())","manifest=bound(profile['manifest']);need(SDK is not None and digest(SDK.read_bytes())==SDK_SHA,'exact accepted BEGIN SDK authority');sdk=json.loads(SDK.read_text())")
source(J/'derive_fixed_batch.TEMPLATE.py',deriver)
ready={'scope':__doc__.splitlines()[0],'status':'FINITE_BEGIN_TWO_RECORD_SOURCE_TEMPLATES_ONLY_NO_STAGE_NATIVE_RELEASE','private_root':str(J),'first_stage_binding':ref(S/'BINDING.PENDING.json'),'first_stager_template':ref(S/'stage_m05_two_generation.TEMPLATE.py'),'focused_authority_delta':ref(E/'BEGIN-RESTORATION-AUTHORITY-DELTA.patch'),'source_profile':PROFILE,'batch_profile_id':PROFILE_ID,'changed_SDK_snapshot_members':MEMBERS,'expected_unchanged_IHK':load(F/'PRODUCER-TWO-MODULES.PENDING.json')['expected_unchanged_ihk'],'actual_SDK_acceptance':None,'actual_snapshot_binding':None,'actual235':None,'actual227':None,'first_complete_restoration':None,'batch_profile':None,'ten_cycle_release':None,'prior_cycle_credit':0,'fixed_count':10,'batch_deriver_template':ref(J/'derive_fixed_batch.TEMPLATE.py'),'receipt_join':ref(J/'join_restoration_batch_receipts.py'),'ten_cycle_caller':ref(J/'run_ten_cycles.py'),'stage_argv_pending':argv,'ordinary_source_profile':load(E/'NEXT-NATIVE-READY.PENDING.json')['ordinary_profile'],'stage_interpreter':'/home/holden/anaconda3/bin/python3','source_invariants':['62-member namespace; exact original five image/launcher/SDK replacement members;57original members byteidentical','SMP+mcctrl new vs previousV3; IHK originalsnapshot unchanged;60previousstage members unchanged','f043collector +40Bsignal-mask stdout/empty stderr/exit0','4312firstboot/1a7secondboot; fresh epochs[[0,1,1],[0,2,2]]','ten-cycle parent changes onlyPROFILE_ID/MANIFEST_SHA/AUTHORITY_SHA after actualfirstreview+innerresultSHA+initrdjoin','Hooks separately requires actualexact profile/tuple SDK+launcher+firstrestoration wrappers and ordered10operationnonces'],'actual_commands_require':['actual acceptedSDK56d2 with independentphysical closure','both actualstableSMP/mcctrl snapshots, rootordinarygrant','positive235+227 outcomes and physicalretirement before firstrestoration release','actualfirstrestoration independent literalcomplete+physicalreview before ten-cycle derivation/release'],'geometry_activation':'Preserve110;142templates are failclosed/preobservation and not active until independent actualgrowthacceptance+rootcoherent source/tuple/currentidentity binding.','effects':dict(cpio_transformations=0,stages=0,root=0,Docker=0,compilers=0,guests=0)}
save(E/'BEGIN-RESTORATION-JOINT-READINESS.PENDING.json',ready)
print(json.dumps(dict(status=ready['status'],private_root=str(J),source_template=ready['first_stager_template'],ready=ref(E/'BEGIN-RESTORATION-JOINT-READINESS.PENDING.json'))))
