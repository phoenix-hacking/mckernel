"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bind actual accepted BEGIN SDK and two actual snapshot receipts to fixed M05 source/data.
No stage/archive/runtime action; no first-restoration or batch acceptance is invented.
"""
from pathlib import Path
import ast,copy,hashlib,json,os
F=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/begin-cleanup-native-successor-2')
J=F/'restoration-batch-readiness-1';S=J/'stage-binding'
def load(p):return json.loads(p.read_text())
def ref(p):b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),size=len(b),mode=p.stat().st_mode)
def save(p,d):
 with p.open('x')as f:json.dump(d,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def main():
 producer=load(F/'PRODUCER-TWO-MODULES.ACTUAL.json');aref=producer['sdk_independent_artifact_acceptance'];apath=Path(aref['path']);assert hashlib.sha256(apath.read_bytes()).hexdigest()==aref['sha256'];accepted=load(apath)
 assert accepted['status']=='PASS'and accepted['implementation_ownership']is False and accepted['physical_acceptance']is True and accepted['native_acceptance']is False and accepted['source_identity']==producer['source_identity']=='db7f2ac4ddc023874ddf6b2b8de2c86c41bbf6efb601f33d4d0f501aa1957598'
 patchedpath=F/'TWO-RECORD-BASE-PATCH-INPUTS.ACTUAL.json';patched=load(patchedpath);members=['modules/ihk-smp-x86_64.ko','modules/mcctrl.ko']
 assert patched['changed_record_allowlist']==members and set(patched['new_runtime_tuple'])==set(members)and patched['matched_artifact_acceptance']['sdk']==aref
 binding=load(S/'BINDING.CARRIER-PENDING.json');binding['authority']['current_SDK_acceptance']=ref(apath);binding['authority']['begin_snapshot_binding']=ref(patchedpath)
 for member in members:
  row=patched['new_runtime_tuple'][member];expected=producer['actual_observed_tuple'][member];assert row['sha256']==expected['sha256']and row['size']==expected['size']and row['mode']==33188;binding['replacements'][member]=row
 for member,row in binding['replacements'].items():
  if member.startswith('modules/'):
   actual=accepted['artifacts'][Path(member).name];assert row['sha256']==actual['sha256']and row['size']==actual['bytes']
 assert binding['replacements']['modules/ihk.ko']==producer['expected_unchanged_ihk']
 assert binding['cleanup_profile']['modules']is None;binding['cleanup_profile']['modules']=[copy.deepcopy(binding['replacements']['modules/'+name])for name in ['ihk.ko','ihk-smp-x86_64.ko','mcctrl.ko']];save(S/'BINDING.json',binding)
 values={'BINDING_SHA256':ref(S/'BINDING.json')['sha256'],'SDK_SUCCESSOR_PATH':str(apath),'SDK_SUCCESSOR_SHA':aref['sha256'],'SDK_SUCCESSOR_DECISION':accepted['decision'],'SNAPSHOT_BINDING_PATH':str(patchedpath),'SNAPSHOT_BINDING_SHA':ref(patchedpath)['sha256']}
 template=(S/'stage_m05_two_generation.CARRIER-TEMPLATE.py').read_text();lines=template.splitlines(True)
 for node in sorted([n for n in ast.parse(template).body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id in values for t in n.targets)],key=lambda n:n.lineno,reverse=True):lines[node.lineno-1:node.end_lineno]=[node.targets[0].id+' = '+repr(values[node.targets[0].id])+'\n']
 source=''.join(lines);ast.parse(source);(S/'stage_m05_two_generation.py').write_text(source)
 save(S/'READY-ACTUAL-P05-STAGE-ARGV.json',load(S/'READY-ACTUAL-P05-STAGE-ARGV.PENDING.json'))
 (S/'run_actual_current68_m05_stage_once.py').write_bytes((S/'run_actual_current68_m05_stage_once.PREDECESSOR.py').read_bytes())
 deriver=(J/'derive_fixed_batch.TEMPLATE.py').read_text();assert deriver.count('SDK=None\nSDK_SHA=None')==1;deriver=deriver.replace('SDK=None\nSDK_SHA=None','SDK=Path('+repr(str(apath))+')\nSDK_SHA='+repr(aref['sha256']));ast.parse(deriver);(J/'derive_fixed_batch.py').write_text(deriver)
 result=dict(scope=__doc__.splitlines()[0],status='ACTUAL_ACCEPTED_BEGIN_TWO_SNAPSHOT_RESTORATION_SOURCE_BOUND_NO_STAGE',binding=ref(S/'BINDING.json'),stager=ref(S/'stage_m05_two_generation.py'),stage_argv=load(S/'READY-ACTUAL-P05-STAGE-ARGV.json'),caller=ref(S/'run_actual_current68_m05_stage_once.py'),batch_deriver=ref(J/'derive_fixed_batch.py'),first_actual_stage=None,first_restoration=None,ten_cycle_release=None,native_runs=0)
 save(J/'ACTUAL-TWO-MEMBER-SOURCE-BINDING.json',result);print(json.dumps(result))
if __name__=='__main__':main()
