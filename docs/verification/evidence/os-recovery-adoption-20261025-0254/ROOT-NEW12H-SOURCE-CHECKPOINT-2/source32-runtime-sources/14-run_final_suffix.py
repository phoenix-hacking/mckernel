#!/usr/bin/env python3
"""PRIVATE SOURCE PROPOSAL ONLY: final three mock invocations; no implicit run.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Requires separate source-owner, accounting, pinned-image and pids64 driver review.
"""
import argparse,hashlib,json,os,shutil,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parent.parent
def admit_precreated_output(out, binding, nonce):
    """Exact fresh nested bind target, supplied by actual Root-owned preparation."""
    import re,stat
    expected={'schema','path','nonce','device','inode','uid','gid','mode'}
    if set(binding)!=expected or binding['schema']!='mckernel.daemon-mock.precreated-output.v1':raise ValueError('exact precreated output binding fields')
    if not isinstance(nonce,str) or re.fullmatch('[0-9a-f]{32}',nonce) is None or binding['nonce']!=nonce:raise ValueError('output nonce differs')
    out=Path(out)
    if not out.is_absolute() or str(out)!=binding['path'] or out.is_symlink() or out.resolve(strict=True)!=out:raise ValueError('canonical output path differs')
    s=out.lstat()
    actual=dict(device=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,mode=stat.S_IMODE(s.st_mode))
    if not stat.S_ISDIR(s.st_mode) or any(type(binding[k]) is not int for k in actual) or actual!={k:binding[k] for k in actual}:raise ValueError('exact output directory identity differs')
    if actual['uid']!=1000 or actual['gid']!=1000 or actual['mode']!=0o700:raise ValueError('ordinary private output owner/mode required')
    if any(out.iterdir()):raise ValueError('precreated output is not empty')
    return out

def seed_output(out, retained):
    # Separate helper executable and capture directory names. Never precreate
    # ring-C, ring-Rust or oversize-Rust capture directories.
    for source,target in [('ring-C','ring-C-helper'),('ihkmond-Rust','ihkmond-Rust')]:
        shutil.copyfile(retained/source,out/target);os.chmod(out/target,0o700)
    shutil.copytree(retained/'kmsg-files',out/'kmsg-files')
    return out/'ring-C-helper',out/'ihkmond-Rust',out/'kmsg-files'

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execute',action='store_true');a=ap.parse_args()
    if not a.execute:
        print(json.dumps(dict(state='SOURCE_ONLY',compilers=0,new_daemon_cases=0,remaining_invocations=3,native_acceptance=False)));return 0
    # Python -I excludes the script directory. Root stages these exact pinned
    # modules in the readonly fixture directory; never search a mutable cwd.
    sys.path.insert(0,str(BASE/'fixture'))
    from pinned_helpers import helper
    from retained_current import validate
    out=BASE/'fixture-output';retained=Path('/retained-current')
    binding_path=Path(os.environ['IHKMOND_FIXTURE_OUTPUT_BINDING'])
    if str(binding_path)!='/preparation/OUTPUT-BINDING.ACTUAL.json':raise ValueError('exact container output binding path')
    admit_precreated_output(out,json.loads(binding_path.read_bytes()),os.environ['IHKMOND_FIXTURE_NONCE'])
    results=validate(retained,BASE/'fixture/cases.json',Path('/preparation/RETAINED-INPUTS.SOURCE-ONLY.json'))
    c_helper,r_binary,tmp=seed_output(out,retained)
    started=time.monotonic();sys.path.insert(0,str(BASE/'fixture'));from owned_process import Owner
    validate_join_audit=helper('audit').validate
    owner=Owner(out)
    def limit(seconds):
        left=90-(time.monotonic()-started)
        if left<=0:raise TimeoutError('90-second work deadline exhausted')
        return min(seconds,left)
    env={k:v for k,v in os.environ.items() if not k.startswith('IHKMOND_') and k not in ['LD_PRELOAD','LD_LIBRARY_PATH','POSIXLY_CORRECT']};env.update(LC_ALL='C',IHKMOND_TMP=str(tmp))
    invocation=out/'ihkmond'
    def execute(exe,label,args,mode,mon,kmsg,helper=False):
        if invocation.is_symlink():invocation.unlink()
        invocation.symlink_to(exe)
        trace=out/(label+'.trace');summary=out/(label+'.resources.json')
        child=dict(env,IHKMOND_SCENARIO=mode,IHKMOND_TRACE=str(trace),IHKMOND_SUMMARY=str(summary),IHKMOND_EXPECT_MON=str(mon),IHKMOND_EXPECT_KMSG=str(kmsg))
        audit=out/(label+'.joined-tasks.ndjson')
        if exe==r_binary:child['IHKMOND_JOIN_AUDIT']=str(audit)
        if helper:child['IHKMOND_HELPER']='ring'
        p=owner.run([str(invocation)]+args,child,BASE,limit(8),label)
        if not summary.is_file():
            (out/'first-failure.json').write_text(json.dumps(dict(name=label,reason='missing terminal resource receipt',Rust_status=p.returncode,joined_audit_retained=audit.is_file()),indent=2)+'\n')
            raise RuntimeError(label+' lacks terminal mock resource receipt')
        if exe==r_binary:
            capture=json.loads((out/label/'whole-join.json').read_bytes())
            try:proof=validate_join_audit(audit.read_bytes(),capture['pid'],capture['start'])
            except Exception as error:
                (out/'first-failure.json').write_text(json.dumps(dict(name=label,reason='joined-task observer refusal',error=type(error).__name__+': '+str(error),Rust_status=p.returncode,joined_audit_retained=audit.is_file()),indent=2)+'\n')
                raise
            (out/(label+'.joined-tasks.proof.json')).write_text(json.dumps(proof,indent=2)+'\n')
        return p,json.loads(summary.read_text()),trace.read_text().splitlines()
    def closed(m,leases=0):return m['open_fds']==0 and m['duplicate_close']==0 and m['leases']==leases and m['udev_ctx']==0 and m['udev_mon']==0 and m['udev_devices']==0 and m['threads']==1
    # Direct retained C kmsg helper parity, without executing its unsafe detached
    # thread cleanup. Keep each file image before another run truncates it.
    ring=[]
    for label,exe in [('C',c_helper),('Rust',r_binary)]:
        p,m,t=execute(exe,'ring-'+label,[],'ring',0,0,helper=(label=='Rust'))
        files={x.name:x.read_bytes().hex() for x in (tmp/'mcos0').glob('kmsg*')}
        (out/('ring-'+label+'.files.json')).write_text(json.dumps(files,indent=2)+'\n')
        ring.append({'status':p.returncode,'resources':m,'logs':[l for l in t if l.startswith('syslog ')],'files':files})
        if p.returncode!=0 or not closed(m):
            (out/'first-failure.json').write_text(json.dumps({'ring':label,'status':p.returncode,'resources':m},indent=2)+'\n')
            raise RuntimeError('ring-'+label+' failed; captures retained, no retry')
    # Prior lifecycle files can remain in the physical ring; only the current
    # kmsg0 bytes are the helper's written image. Inactive files are evidence.
    ring_equal=ring[0]['status']==ring[1]['status']==0 and ring[0]['logs']==ring[1]['logs'] and ring[0]['files'].get('kmsg0')==ring[1]['files'].get('kmsg0') and all(closed(r['resources']) for r in ring)
    if not ring_equal:
        (out/'first-failure.json').write_text(json.dumps({'ring_parity':False,'observed':ring},indent=2)+'\n')
        raise RuntimeError('C/Rust ring parity failed; captures retained, no retry')
    p,m,t=execute(r_binary,'oversize-Rust',[],'oversize',0,0,helper=True)
    oversize=p.returncode==0 and closed(m) and m['syslog_bytes']==(1<<20)+16
    summary=dict(status='PASS_RETAINED26_AND_FINAL_THREE_MOCK_ONLY' if ring_equal and oversize else 'FAIL',retained_daemon_cases=26,new_daemon_cases=0,compilers_executed=0,remaining_invocations_executed=3,normal_C_ring_parity=ring_equal,Rust_oversized_read_proposal=oversize,results=results,native_acceptance=False,provider_Rust_link_closure=False,M15_file_closure=False)
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k!='results'}));return 0 if summary['status'].startswith('PASS_') else 1
if __name__=='__main__':sys.exit(main())
