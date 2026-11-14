"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only explicit successor authority. No stage/archive/runtime operation.
"""
from pathlib import Path
import ast,copy,difflib,hashlib,json
D=Path(__file__).resolve().parent;A=Path('/home/holden/mckernel-work/host-preparation/native235-zombie-sdk-successor-20261023-1/restoration-batch-preparation');S=A/'stage-binding';S.mkdir(mode=0o700)
OLD=Path('/home/holden/mckernel-work/host-preparation/p-m05-v3-matched-first-restoration-binding-20261023-1/full-tuple-binding-1')
Z=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/zombie-sdk-native-successor-1')
def j(p):return json.loads(p.read_text())
def ref(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),size=len(b),mode=p.stat().st_mode)
def write(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
b=j(OLD/'BINDING.json');patch=j(Z/'ONE-RECORD-BASE-PATCH-INPUTS.ACTUAL.json');sdk=Path(patch['matched_artifact_acceptance']['sdk']['path']);sdkref=ref(sdk);assert sdkref['sha256']==patch['matched_artifact_acceptance']['sdk']['sha256']
b['authority_profile']='current68-zombie-reaper-build-link-physical';b['authority']['current_SDK_acceptance']=sdkref;b['authority']['zombie_snapshot_binding']=ref(Z/'ONE-RECORD-BASE-PATCH-INPUTS.ACTUAL.json');b['replacements']['modules/mcctrl.ko']=patch['new_runtime_tuple']['modules/mcctrl.ko'];b['output']=str(S/'actual-stage-1')
assert b['replacements']['images/mckernel.img']['sha256']==patch['unchanged_image_sha256'];assert b['replacements']['bin/mcexec']['sha256']==patch['unchanged_launcher_sha256']
write(S/'BINDING.json',b);bh=hashlib.sha256((S/'BINDING.json').read_bytes()).hexdigest();a=(OLD/'stage_m05_two_generation.py').read_text();new=a
branch="""    elif profile == 'current68-zombie-reaper-build-link-physical':
        need(binding['authority']['current_SDK_acceptance']['path'] == SDK_SUCCESSOR_PATH
             and binding['authority']['current_SDK_acceptance']['sha256'] == SDK_SUCCESSOR_SHA
             and sdk['status'] == 'PASS' and sdk['implementation_ownership'] is False
             and sdk['decision'] == 'ACCEPT_ACTUAL_SDK_SUCCESSOR_ARTIFACTS_AND_HOST_PHYSICAL_RETIREMENT'
             and sdk['physical_acceptance'] is True and sdk['native_acceptance'] is False
             and sdk['source_identity'] == '15334501928a36becca541c8cd8beeead3da0acd8737f955abaf98f34cece515',
             'exact independent zombie-reaper SDK authority')
        patched = docs['zombie_snapshot_binding']
        need(binding['authority']['zombie_snapshot_binding']['path'] == SNAPSHOT_BINDING_PATH
             and binding['authority']['zombie_snapshot_binding']['sha256'] == SNAPSHOT_BINDING_SHA
             and patched['matched_artifact_acceptance']['sdk']['sha256'] == SDK_SUCCESSOR_SHA
             and patched['changed_record_allowlist'] == ['modules/mcctrl.ko']
             and patched['new_runtime_tuple']['modules/mcctrl.ko'] == binding['replacements']['modules/mcctrl.ko'],
             'exact accepted changed mcctrl snapshot join')
        receipt = docs['v3_snapshot_receipt']
        need(binding['authority']['v3_snapshot_receipt']['sha256'] == '7eaaffb59663f27943c2f766ff4d737d790ade99349574349ba9453afa5cd33d'
             and receipt['status'] == 'PASS_THREE_ACTUAL_EXCLUSIVE_MODULE_RUNTIME_SNAPSHOTS',
             'unchanged accepted ihk snapshots')
        for row in receipt['modules']:
            if row['name'] != 'mcctrl.ko':
                need(row['name'] in ('ihk.ko', 'ihk-smp-x86_64.ko')
                     and row['copied'] == binding['replacements']['modules/' + row['name']],
                     'exact unchanged SDK module snapshot')
"""
needle="    else:\n        need(False, 'unknown SDK authority profile')";assert a.count(needle)==1;new=new.replace(needle,branch+needle)
oldcheck="need(sdk['artifacts'][member.split('/')[-1]] ==\n                 {'bytes': row['size'], 'sha256': row['sha256']}, 'SDK module descriptor join')"
newcheck="need(({k: sdk['artifacts'][member.split('/')[-1]][k] for k in ('bytes', 'sha256')}\n                  if profile == 'current68-zombie-reaper-build-link-physical' else sdk['artifacts'][member.split('/')[-1]]) ==\n                 {'bytes': row['size'], 'sha256': row['sha256']}, 'SDK module descriptor join')"
assert oldcheck in new;new=new.replace(oldcheck,newcheck)
new=new.replace("if binding.get('authority_profile') == 'current68-v3-build-link-physical':","if binding.get('authority_profile') in ('current68-v3-build-link-physical', 'current68-zombie-reaper-build-link-physical'):")
oldpin="BINDING_SHA256 = '2bf6b9819f9fad2b293cd968884017d630e2e2825fe171771376daf1c802c321'";assert oldpin in new
constants=oldpin.replace('2bf6b9819f9fad2b293cd968884017d630e2e2825fe171771376daf1c802c321',bh)+'\nSDK_SUCCESSOR_PATH = '+repr(str(sdk))+'\nSDK_SUCCESSOR_SHA = '+repr(sdkref['sha256'])+'\nSNAPSHOT_BINDING_PATH = '+repr(str(Z/'ONE-RECORD-BASE-PATCH-INPUTS.ACTUAL.json'))+'\nSNAPSHOT_BINDING_SHA = '+repr(ref(Z/'ONE-RECORD-BASE-PATCH-INPUTS.ACTUAL.json')['sha256'])
new=new.replace(oldpin,constants);ast.parse(new);(S/'stage_m05_two_generation.py').write_text(new)
(D/'EXPLICIT-SDK-AUTHORITY-SUCCESSOR.diff').write_text(''.join(difflib.unified_diff(a.splitlines(True),new.splitlines(True),fromfile=str(OLD/'stage_m05_two_generation.py'),tofile=str(S/'stage_m05_two_generation.py'))))
argv=j(OLD/'READY-ACTUAL-P05-STAGE-ARGV.json');argv[-2]=str(S/'stage_m05_two_generation.py');argv[2]='7';write(S/'READY-ACTUAL-P05-STAGE-ARGV.json',argv)
caller=(OLD/'run_actual_current68_m05_stage_once.py').read_text();(S/'run_actual_current68_m05_stage_once.py').write_text(caller)
write(D/'SOURCE-READY-NEXT-COMMAND.json',dict(scope=__doc__.splitlines()[0],status='MINIMAL_EXPLICIT_SDK_AUTHORITY_SUCCESSOR_SOURCE_READY_TEST_AND_STAGE_NOT_RUN',new_binding=ref(S/'BINDING.json'),new_stager=ref(S/'stage_m05_two_generation.py'),ordinary_stage_argv=argv,stage_requires_fresh_ordinary_dispatch_grant=True,cheap_test_argv=['/usr/bin/taskset','-c','7','/usr/bin/prlimit','--as=536870912:536870912','--cpu=20:20','--core=0:0','--','/usr/bin/python3','-I','-B',str(S/'check_authority_only.py')],changed_artifact_members_vs_previous_accepted_stage=['modules/mcctrl.ko'],unchanged_previous_stage_members=61,original_baseline_namespace=62,baseline_tuple_members=5,unchanged_original_baseline_members=57,first_restoration=None,batch_release=None,CPU7_tests=0,root_Docker_compiler_guest_operations=0))
print(json.dumps(dict(source=ref(S/'stage_m05_two_generation.py'),binding=ref(S/'BINDING.json'),stage_argv=argv)))
