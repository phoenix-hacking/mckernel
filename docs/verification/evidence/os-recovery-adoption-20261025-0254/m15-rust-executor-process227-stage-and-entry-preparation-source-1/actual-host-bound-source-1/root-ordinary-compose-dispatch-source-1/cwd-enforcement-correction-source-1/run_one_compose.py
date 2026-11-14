"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One original46d compose under retained6e98 ordinary profile/grant/admission/capture.
No compiler, payload execution, staging/native, cleanup or automatic retry.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,resource,signal,time
D=Path(__file__).resolve().parent.parent
E=D.parents[2]
ORD=E/'ordinary-host-new12h-runner-source-1/run_new12h_host.py'
ORD_SHA='6e98a1fbcbce2e822a815a05516287e7122cbd8e06d43277134b27b70cf3ad34'
def need(v,m):
 if not v:raise ValueError(m)
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(Path(p).read_bytes())
def auth(r):need(ref(r['path'])==r,'exact sealed bytes');return Path(r['path'])
def load(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def write(p,v):
 with Path(p).open('x') as f:json.dump(v,f,indent=2);f.write('\n')
def main():
 a=argparse.ArgumentParser(description=__doc__)
 for k in ['profile','profile-sha256','grant','grant-sha256']:a.add_argument('--'+k,required=True)
 z=a.parse_args();need(ref(z.profile)['sha256']==z.profile_sha256 and ref(z.grant)['sha256']==z.grant_sha256,'actual profile/grant pins')
 p=read(z.profile);g=read(z.grant);need(ref(ORD)['sha256']==ORD_SHA,'retained ordinary runner')
 r=load(ORD,'retained6e98_profile_grant_limits');r.validate_profile(p);r.verify(p['inputs']+[x['plan'] for x in p['leaves']]);r.validate_grant(g,p,z.profile_sha256,ref(__file__)['sha256'],time.time())
 need(g['reserved_pids_ordinary']==p['ordinary_pid_reservation']==64 and g['runtime_native_authority'] is None,'same conservative64 task reservation; no native release')
 ledger=read(auth(g['current_nonce_ledger']));auth(g['current_native_free'])
 need(ledger['complete_within_declared_current_boundary'] is True and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True and g['nonce'] not in ledger['consumed_nonces']+ledger['reserved_abandoned_unconsumed_nonces'],'actual latest ledger/unused operation nonce')
 need(ledger['latest_accepted_free_boundary']==g['current_native_free'],'current accepted free boundary')
 os.sched_setaffinity(0,{6})
 need(ref(ORD.parent/'admission_new12h.py')['sha256']==r.ADMISSION_SHA and ref(r.CAPTURE)['sha256']==r.CAPTURE_SHA,'original admission/capture sources')
 admission=load(ORD.parent/'admission_new12h.py','existing_new12h_admission').admission
 capture=load(r.CAPTURE,'existing990_positive_whole_group_capture')
 def guard():
  r.verify(p['inputs']+[x['plan'] for x in p['leaves']]);need(ref(z.profile)['sha256']==z.profile_sha256 and ref(z.grant)['sha256']==z.grant_sha256,'unchanged profile/grant')
  need(time.time()<g['expires_wall'],'live original ordinary grant');return admission(p)
 initial=guard() # Included-first account/window/floor guard BEFORE output creation.
 out=Path(p['leaves'][0]['output']);cap=Path(p['capture_root']);need(not os.path.lexists(out) and not os.path.lexists(cap),'fresh disjoint output/capture parents')
 need(out.parent.is_dir() and cap.parent==D,'exact existing reviewed parents')
 out.mkdir(mode=0o700);cap.mkdir(mode=0o700)
 write(cap/'CONSUMED-GRANT.json',dict(nonce=g['nonce'],profile=ref(z.profile),grant=ref(z.grant),admission=initial,source=ref(__file__)))
 for sig in capture.STOP_SIGNALS:signal.signal(sig,capture.stop)
 os.environ.clear();os.environ.update(PATH='/usr/bin:/bin',LC_ALL='C',PYTHONDONTWRITEBYTECODE='1')
 command=p['commands'][0];step=cap/'step0';step.mkdir(mode=0o700);write(step/'command.json',command);write(step/'admission.json',guard())
 def limits():
  r.limits() # Original CPU6/AS2GiB/CPU60/CORE0; preserve stricter235 FSIZE32MiB.
  resource.setrlimit(resource.RLIMIT_FSIZE,(32*2**20,32*2**20))
 os.chdir(command['cwd'])
 joined=capture.owned_capture(command,step,90,limits);write(step/'whole-join.json',joined)
 write(cap/'RESULTS.json',dict(status='JOINED_COMPOSE_PENDING_RECEIPT_BINDING',results=[dict(index=0,leaf=command['leaf'],join=joined)],native_acceptance=False))
 need(joined['returncode']==0 and joined['direct_child_joined'] and joined['group_absent'] and joined['closed_streams'] and not joined['error'] and not joined['retirement_error'],'first compose failure; preserve no retry')
 raw=(step/'stdout').read_bytes();receipt=json.loads(raw);need(isinstance(receipt,dict) and isinstance(receipt['final_map'],dict),'complete original46d JSON/fullmap, not constant stdout oracle')
 need(not (step/'stderr').read_bytes(),'unchanged producer empty stderr')
 target=Path(p['actual_receipt_path']);need(target.parent==out and not target.exists(),'exact fresh binder receipt')
 with target.open('xb') as f:f.write(raw) # Preserve every actual stdout byte andLF.
 need(target.read_bytes()==raw and receipt['output_sha256']==ref(p['actual_overlay_path'])['sha256'],'actual complete receipt and overlay digest')
 write(cap/'ACTUAL-COMPOSE-RESULT.json',dict(scope=p['scope'],status='ACTUAL_ONE_46D_COMPOSE_ZERO_JOINED_FULL_RECEIPT_NOT_NATIVE',nonce=g['nonce'],profile=ref(z.profile),grant=ref(z.grant),join=ref(step/'whole-join.json'),receipt=ref(target),overlay=ref(p['actual_overlay_path']),complete_stdout=ref(step/'stdout'),stderr=ref(step/'stderr'),current_nonce_ledger=g['current_nonce_ledger'],current_native_free=g['current_native_free'],binder_has_not_run=True,native_acceptance=False))
 print(json.dumps(dict(status='ACTUAL_227_COMPOSE_ZERO_FULLMAP_PENDING_QUALIFIED_BINDER',result=ref(cap/'ACTUAL-COMPOSE-RESULT.json'))))
if __name__=='__main__':main()
