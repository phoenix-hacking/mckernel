#!/usr/bin/env python3
"""Prepared original-C/Rust ihkosctl host ABI-stub fixture; --execute needs grant.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
import argparse,json,os,shutil,sys,time
from pathlib import Path
BASE=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-12/m15-ihkosctl')
WRAPS=['open','close','ioctl','calloc','malloc','strdup','time','localtime','strftime']
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--execute',action='store_true')
    ap.add_argument('--profile',choices=['default','no-memdump','both'],default='default')
    ap.add_argument('--cc',default='/usr/bin/cc')
    ap.add_argument('--rustc',default='/home/holden/.rustup/toolchains/1.85.1-x86_64-unknown-linux-gnu/bin/rustc')
    a=ap.parse_args();cases=json.loads((BASE/'fixture/cases.json').read_text());contracts=json.loads((BASE/'fixture/defined-contracts.json').read_text())
    if not a.execute:
        print(json.dumps({'state':'PREPARED_ONLY','comparison_cases':len(cases),'separate_defined_contracts':len(contracts),'profile':a.profile,'compilers_or_CLI_executed':False}));return 0
    out=Path(__file__).resolve().parent/'fixture-output'
    if out.exists():raise SystemExit('Retain existing fixture-output; use reviewed successor, no overwrite')
    out.mkdir();start=time.monotonic();sys.path.insert(0,str(Path(__file__).resolve().parent));from owned_process import Owner
    owner=Owner(out)
    def remaining(limit):
        left=150-(time.monotonic()-start)
        if left<=0:raise TimeoutError('150-second work envelope exhausted')
        return min(limit,left)
    env={k:v for k,v in os.environ.items() if not k.startswith('IHKOS_') and k not in ['LD_PRELOAD','LD_LIBRARY_PATH','POSIXLY_CORRECT']}
    env.update(LC_ALL='C',TZ='UTC0',IHKOSCTL_BUILDID='fixture-build')
    cc=shutil.which(a.cc);rustc=shutil.which(a.rustc)
    if not cc or not rustc:raise SystemExit('Qualified host compilers missing')
    def build(argv,label):
        (out/(label+'.command.json')).write_text(json.dumps({'argv':argv,'IHKOSCTL_BUILDID':env['IHKOSCTL_BUILDID'],'LC_ALL':'C','TZ':'UTC0'},indent=2)+'\n')
        run=owner.run(argv,env,BASE,remaining(60),label)
        if run.returncode:raise RuntimeError(label+' failed; original capture retained, no automatic retry')
    profiles=['default','no-memdump'] if a.profile=='both' else [a.profile]
    summary={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','compiler_paths':{'cc':cc,'rustc':rustc},'profiles':[],'production_acceptance':False,'Rust_library_provider_parity_proven':False}
    for profile in profiles:
        d=out/profile;d.mkdir();obj=d/'ihkosctl.o';c_exe=d/'ihkosctl-c';r_exe=d/'ihkosctl-rust'
        cfg=['--cfg','ihkosctl_memdump'] if profile=='default' else []
        build([rustc,'--edition=2021','--crate-name','ihkosctl','--crate-type=lib','-C','panic=abort','-C','opt-level=2','-C','relocation-model=pic','--emit=obj='+str(obj)]+cfg+[str(BASE/'ihkosctl.rs')],profile+'-rust-object')
        cflags=['-DENABLE_MEMDUMP=1'] if profile=='default' else []
        common=[cc,'-std=gnu11','-O2','-fPIE','-pie','-I',str(BASE/'fixture/include')]+cflags
        wraps=['-Wl,--wrap='+name for name in WRAPS]
        helper=str(BASE/'reference/ihklib_helpers.c');stub=str(BASE/'fixture/abi_stub.c')
        build(common+[str(BASE/'reference/ihkosctl.c'),helper,stub]+wraps+['-o',str(c_exe)],profile+'-C-reference')
        build(common+[str(obj),helper,stub]+wraps+['-o',str(r_exe)],profile+'-Rust-link')
        results=[]
        for index,case in enumerate(cases):
            observed=[]
            for label,exe in [('C',c_exe),('Rust',r_exe)]:
                trace=d/('%03d-%s.trace'%(index,label));child=dict(env,**case['env'],IHKOS_FIXTURE_TRACE=str(trace))
                # Popen executable binding preserves equal argv[0] in both
                # getopt and usage diagnostics, with no path normalization.
                # Owner accepts the same argv; private symlink makes it equal.
                invocation=d/'ihkosctl'
                if invocation.is_symlink():invocation.unlink()
                invocation.symlink_to(exe)
                # Both actual executions receive the identical symlink path as
                # argv[0]; its basename is ihkosctl and raw diagnostics compare.
                run=owner.run([str(invocation)]+case['args'],child,BASE,remaining(2),profile+'-%03d-%s'%(index,label))
                raw=trace.read_bytes() if trace.exists() else b''
                normalized=raw
                correction=False
                if label=='Rust' and case['ikc_close_fix']:
                    if normalized.endswith(b'close 17\n'):
                        normalized=normalized[:-len(b'close 17\n')];correction=True
                observed.append((run.returncode,run.stdout,run.stderr,normalized,correction))
            equivalent=observed[0][:4]==observed[1][:4] and observed[0][0]>=0
            correction_ok=not case['ikc_close_fix'] or observed[1][4]
            results.append({'case':index,'args':case['args'],'env':case['env'],'defined_observables_equal':equivalent,'ikc_close_correction_observed':observed[1][4],'passed':equivalent and correction_ok,'C_status':observed[0][0],'Rust_status':observed[1][0]})
        defined=[]
        for index,case in enumerate(contracts):
            trace=d/('defined-%02d.trace'%index);child=dict(env,**case['env'],IHKOS_FIXTURE_TRACE=str(trace));invocation=d/'ihkosctl'
            if invocation.is_symlink():invocation.unlink()
            invocation.symlink_to(r_exe)
            run=owner.run([str(invocation)]+case['args'],child,BASE,remaining(2),profile+'-defined-%02d'%index)
            ok=(run.returncode,run.stdout,run.stderr)==(case['status'],case['stdout'].encode(),case['stderr'].encode())
            raw=trace.read_bytes() if trace.exists() else b''
            if case['name']=='ikc-first-allocation-failure-closes':ok=ok and raw.endswith(b'close 17\n')
            defined.append({'name':case['name'],'passed_proposed_contract':ok,'status':run.returncode,'classification':'Rust-only correctness proposal, C undefined path not executed'})
        (d/'comparison.json').write_text(json.dumps(results,indent=2)+'\n');(d/'defined-contracts.json').write_text(json.dumps(defined,indent=2)+'\n')
        summary['profiles'].append({'profile':profile,'comparison_cases':len(results),'failed':[x['case'] for x in results if not x['passed']],'defined_contracts':defined})
        if any(not x['passed'] for x in results) or any(not x['passed_proposed_contract'] for x in defined):break
    summary['elapsed_seconds']=round(time.monotonic()-start,3)
    summary['status']='PASS_DEFINED_CLI_OBSERVABLES_AND_PROPOSED_CORRECTIONS_HOST_STUB_ONLY' if all(not p['failed'] and all(x['passed_proposed_contract'] for x in p['defined_contracts']) for p in summary['profiles']) else 'FAIL'
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary));return 0 if summary['status'].startswith('PASS_') else 1
if __name__=='__main__':sys.exit(main())
