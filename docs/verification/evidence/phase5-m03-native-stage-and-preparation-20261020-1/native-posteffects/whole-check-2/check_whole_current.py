from pathlib import Path
import copy,hashlib,importlib.util,json
D=Path(__file__).resolve().parent;P=D.parent
s=importlib.util.spec_from_file_location('current_posteffects',P/'posteffects_physical_projection_corrected.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
r=dict(path='/home/holden/mckernel-work/host-preparation/phase5-opt-in-production-link-image-independent-review-20261020-1/ACTUAL-CURRENT-PASS-POST-EFFECTS-QUARANTINE-RECOVERY-PHYSICAL-REVIEW.json',sha256='0e99ddd8790ccf02c4ba191383c3274f661fc2a5dd7774776727013ef4727437',bytes=17901)
t=m.checked(r);projection=m.project(t,r)
roles=m.checked(m.PRODUCER_BINDINGS);before=m.checked(roles['post_effects_state_before_retirement']);release=m.checked(roles['cleanup_release']);request=m.checked(release['observation']['request'],64<<20)
results=[dict(case='whole_genuine_current_report',status='PASS')]
def refuses(name,fn,reason):
 try:fn()
 except ValueError as e:
  assert str(e)==reason,(name,str(e));results.append(dict(case=name,status='PASS',refusal=str(e)));return
 raise AssertionError(name+' accepted')
bad=copy.deepcopy(t);bad['scope']='CURRENT_IMAGE_PRECOMMON_QUARANTINE_RECOVERY_ONLY';refuses('wrong_scope',lambda:m.kind(bad),'exact explicit POSTEFFECTS recovery kind; no completed or PRECOMMON substitution')
badrelease=copy.deepcopy(release);badrelease['observation']['target']['owner_nonce']='0'*32;refuses('changed_owner_identity',lambda:m.state_join(before,badrelease,request),'internal complete release noLF hash distinct from external file hash')
badstate=copy.deepcopy(before);badstate['files']['plan']['fd']['inode']+=1;refuses('changed_plan_fd_identity',lambda:m.state_join(badstate,release,request),'exact original incomplete journal chain')
result=dict(status='PASS_ACTUAL_WHOLE_POSTEFFECTS_CONSUMER_AND_THREE_REFUSALS',scope='Functional OS/apps plus Rust cutover; physical predecessor decoder only, no native/root/guest',actual_physical=r,actual_projection=projection,cases=results,actual_case_count=len(results))
with (D/'RESULT.json').open('x') as out:json.dump(result,out,sort_keys=True,indent=2);out.write('\n')
print(json.dumps(dict(status=result['status'],cases=len(results))))
