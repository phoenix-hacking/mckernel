"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual full retained capsule/selected ELF transformation and negative final-map checks.
"""
from pathlib import Path
import copy,importlib.util,json
D=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('actual_stage',D/'stage_long_session.py');st=importlib.util.module_from_spec(s);s.loader.exec_module(st)
b=json.loads((D/'ACTUAL-STAGE-BINDING.json').read_text())
st.exact(b['overlay_source']);ov=st.load('unchanged_capsule_parser',b['overlay_source']['path'])
st.exact(b['member_transformer']);helper=st.load('unchanged_member_transform',b['member_transformer']['path'])
old_om=json.loads(st.exact(b['baseline_overlay_manifest']));old=old_om['final_map']
selected={**b['SDK5_replacements'],'init':b['producer_artifact'],**b['application_replacements']}
data={name:st.exact(row) for name,row in selected.items()}
compressed=st.exact(b['baseline_capsule']);raw=ov._inflate(compressed,b['max_inflated_bytes']);del compressed
before=ov._manifest(ov._replay_records(ov.parse_newc(raw)[0]));assert before==old and len(before)==62
helper.MEMBERS=set(data);patched=helper.rewrite_last_records(raw,data,ov)
final=ov._manifest(ov._replay_records(ov.parse_newc(patched)[0]));st.verify_final_map(old,final,data,selected)
assert len(final)==62 and {name for name in old if old[name]!=final[name]}==set(selected)
new_end=st.shifted_base_end(raw,old_om['base_cpio_size'],data,ov)
assert ov.parse_newc(patched[:new_end])[0] and ov.parse_newc(patched[new_end:])[0]
negatives=0
for kind in ('missing','extra','mode','init-hash','app-hash','unchanged-libc'):
 bad=copy.deepcopy(final)
 if kind=='missing':del bad['init']
 elif kind=='extra':bad['new-member']=dict(bad['init'])
 elif kind=='mode':bad['init']['mode']^=1
 elif kind=='init-hash':bad['init']['sha256']='0'*64
 elif kind=='app-hash':bad['apps/app0']['sha256']='0'*64
 else:
  name=next(n for n in old if n not in selected and n.endswith('libc.so.6'));bad[name]['sha256']='0'*64
 try:st.verify_final_map(old,bad,data,selected)
 except ValueError:negatives+=1
 else:raise AssertionError('accepted '+kind)
# Pending binding must refuse before any output/transform, not fill reserves.
bad=dict(b);bad['status']='PENDING_CANDIDATE3_AND_LONG_PAYLOAD_AND_INDEPENDENT_STAGE_PROFILE'
try:st.stage(bad)
except ValueError:negatives+=1
else:raise AssertionError('pending binding staged')
assert not (D/'actual-stage-1').exists()
result={'scope':__doc__,'status':'PASS_ACTUAL_COMPLETE_62_MEMBER_TRANSFORM_AND_7_NEGATIVES','old_raw_bytes':len(raw),'new_raw_bytes':len(patched),'old_base_end':old_om['base_cpio_size'],'new_base_end':new_end,'changed_members':sorted(selected),'unchanged_members':62-len(selected),'negative_count':negatives,'expected_final_map':final,'runtime_or_native_acceptance':False}
(D/'FIXTURE-RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='expected_final_map'}))
