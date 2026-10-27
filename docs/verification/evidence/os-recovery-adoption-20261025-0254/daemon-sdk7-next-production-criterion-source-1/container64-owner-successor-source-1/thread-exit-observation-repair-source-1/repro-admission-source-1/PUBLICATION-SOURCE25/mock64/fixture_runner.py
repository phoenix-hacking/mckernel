#!/usr/bin/env python3
"""Prepared ihkmond C/Rust mock contract fixture; no daemon run before a grant.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
import argparse,json,os,shutil,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parent.parent
WRAPS=['daemon','eventfd','signalfd','epoll_create','epoll_ctl','epoll_wait','open','close','read','write','stat','ioctl','geteuid']
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

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execute',action='store_true');ap.add_argument('--cc',default='/usr/bin/cc');ap.add_argument('--rustc',default='/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc')
    a=ap.parse_args();cases=json.loads((BASE/'fixture/cases.json').read_text())
    if not a.execute:print(json.dumps({'state':'PREPARED_ONLY','daemon_cases':len(cases),'reference_defined_cases':sum(c['reference_defined_compare'] for c in cases),'extra_ring_cases':2,'compilers_or_daemons_run':False}));return 0
    out=BASE/'fixture-output'
    binding_path=Path(os.environ['IHKMOND_FIXTURE_OUTPUT_BINDING'])
    if str(binding_path)!='/preparation/OUTPUT-BINDING.ACTUAL.json':raise ValueError('exact container output binding path')
    admit_precreated_output(out,json.loads(binding_path.read_bytes()),os.environ['IHKMOND_FIXTURE_NONCE'])
    started=time.monotonic();sys.path.insert(0,str(BASE/'fixture'));from owned_process import Owner
    owner=Owner(out)
    def limit(seconds):
        left=90-(time.monotonic()-started)
        if left<=0:raise TimeoutError('90-second work deadline exhausted')
        return min(seconds,left)
    env={k:v for k,v in os.environ.items() if not k.startswith('IHKMOND_') and k not in ['LD_PRELOAD','LD_LIBRARY_PATH','POSIXLY_CORRECT']};env.update(LC_ALL='C')
    cc=shutil.which(a.cc);rustc=shutil.which(a.rustc)
    if not cc or not rustc:raise SystemExit('Qualified compilers absent')
    tmp=out/'kmsg-files';env['IHKMOND_TMP']=str(tmp)
    assert len(str(tmp)+'/mcos0/kmsg63')<256
    original=(BASE/'reference/ihkmond.c').read_text()
    assert original.count('"/tmp/ihkmond"')==1
    bound=out/'ihkmond.fixture.c';bound.write_text(original.replace('"/tmp/ihkmond"','"'+str(tmp)+'"'))
    helper=out/'reference_helpers.c';helper.write_bytes((BASE/'fixture/reference_helpers.c.in').read_bytes())
    def build(argv,label):
        (out/(label+'.command.json')).write_text(json.dumps({'argv':argv,'IHKMOND_TMP':str(tmp),'LC_ALL':'C'},indent=2)+'\n')
        p=owner.run(argv,env,BASE,limit(60),label)
        if p.returncode:raise RuntimeError(label+' failed; capture retained, no retry')
    includes=['-I',str(BASE.parent/'host-libudev-header-1'),'-I',str(BASE/'fixture/include'),'-I',str(out)];mock=out/'mock.o'
    build([cc,'-std=gnu11','-O2','-fPIC','-pthread']+includes+['-c',str(BASE/'fixture/mock.c'),'-o',str(mock)],'mock-build')
    flags=['-Wl,--wrap='+s for s in WRAPS]
    c_binary=out/'ihkmond-C';r_binary=out/'ihkmond-Rust';c_helper=out/'ring-C'
    build([cc,'-std=gnu11','-O2','-pthread']+includes+[str(bound),str(mock)]+flags+['-o',str(c_binary)],'C-reference-build')
    build([cc,'-std=gnu11','-O2','-pthread']+includes+[str(helper),str(mock)]+flags+['-o',str(c_helper)],'C-helper-build')
    rust=[rustc,'--edition=2021','--cfg','ihkmond_fixture','-C','opt-level=2','-C','codegen-units=1',str(BASE/'ihkmond.rs'),'-C','link-arg='+str(mock)]
    for flag in flags:rust+=['-C','link-arg='+flag]
    rust+=['-o',str(r_binary)];build(rust,'Rust-daemon-build')
    invocation=out/'ihkmond'
    def execute(exe,label,args,mode,mon,kmsg,helper=False):
        if invocation.is_symlink():invocation.unlink()
        invocation.symlink_to(exe)
        trace=out/(label+'.trace');summary=out/(label+'.resources.json')
        child=dict(env,IHKMOND_SCENARIO=mode,IHKMOND_TRACE=str(trace),IHKMOND_SUMMARY=str(summary),IHKMOND_EXPECT_MON=str(mon),IHKMOND_EXPECT_KMSG=str(kmsg))
        if helper:child['IHKMOND_HELPER']='ring'
        p=owner.run([str(invocation)]+args,child,BASE,limit(8),label)
        if not summary.is_file():raise RuntimeError(label+' lacks terminal mock resource receipt')
        return p,json.loads(summary.read_text()),trace.read_text().splitlines()
    def closed(m,leases=0):return m['open_fds']==0 and m['duplicate_close']==0 and m['leases']==leases and m['udev_ctx']==0 and m['udev_mon']==0 and m['udev_devices']==0 and m['threads']==1
    results=[]
    for i,case in enumerate(cases):
        p,m,trace=execute(r_binary,'%02d-Rust'%i,case['args'],case['mode'],case['expect_mon'],case['expect_kmsg'])
        ok=p.returncode==case['status'] and closed(m,case['expected_unreleased_leases'])
        if 'expected_gets'in case:ok=ok and m['get']==case['expected_gets']
        if 'expected_syslog_messages'in case:ok=ok and m['syslog_messages']==case['expected_syslog_messages']
        if case['status']==0 and case['expect_mon']:ok=ok and m['detect']>=1
        if case['name']=='release-failure-not-claimed-restored':ok=ok and m['release_attempts']==1 and m['released']==0
        if case['name']=='configured-facility':ok=ok and any('facility=144'in line for line in trace)
        if 'expected_event_read_fault' in case:
            ok=ok and any(('injected '+case['expected_event_read_fault']) in line for line in trace)
        reference=None
        if case['reference_defined_compare']:
            c,cm,ct=execute(c_binary,'%02d-C'%i,case['args'],case['mode'],0,0)
            same=(c.returncode,c.stdout,c.stderr)==(p.returncode,p.stdout,p.stderr)
            cmsg=[line for line in ct if line.startswith('kprint ')];rmsg=[line for line in trace if line.startswith('kprint ')]
            same=same and cmsg==rmsg;ok=ok and same
            reference={'defined_output_status_diagnostic_equal':same,'observed_resources':cm,'resource_defects_are_not_an_oracle':True}
        results.append({'name':case['name'],'passed_contract':bool(ok),'Rust_status':p.returncode,'Rust_resources':m,'reference':reference,'restoration_claim':False if case['expected_unreleased_leases'] else 'host mock only, no native credit'})
        if not ok:
            (out/'first-failure.json').write_text(json.dumps(results[-1],indent=2)+'\n')
            raise RuntimeError(case['name']+' oracle failed; captures retained, no later cases or retry')
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
    summary={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PASS_DEFINED_REFERENCE_AND_RUST_LIFECYCLE_MOCK_ONLY' if all(x['passed_contract'] for x in results) and ring_equal and oversize else 'FAIL','daemon_cases':len(results),'failed':[r['name'] for r in results if not r['passed_contract']],'normal_C_ring_parity':ring_equal,'Rust_oversized_read_proposal':oversize,'results':results,'production_daemon_fork_executed':False,'real_udev_or_devices_executed':False,'native_acceptance':False,'provider_Rust_link_closure':False,'elapsed_seconds':round(time.monotonic()-started,3)}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k!='results'}));return 0 if summary['status'].startswith('PASS_')else 1
if __name__=='__main__':sys.exit(main())
