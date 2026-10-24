#!/usr/bin/env python3
"""Prepared source-only vmcore wrapper fixture, not a real dump-conversion gate.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
import argparse,base64,json,os,shutil,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parent.parent
BYTES=b'synthetic dump payload; not a real dump format\n'
OLD=b'pre-existing output must survive failure\n'
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--execute',action='store_true')
    ap.add_argument('--with-reference-protocol',action='store_true')
    ap.add_argument('--rustc',default='/home/holden/.rustup/toolchains/1.85.1-x86_64-unknown-linux-gnu/bin/rustc')
    a=ap.parse_args();cases=json.loads((BASE/'fixture/cases.json').read_text())
    if not a.execute:
        print(json.dumps({'state':'PREPARED_ONLY','cases':len(cases),'source_only':True,'original_expect_available':Path('/usr/bin/expect').is_file()}));return 0
    out=BASE/'fixture-output'
    if out.exists():raise SystemExit('Retain fixture-output; use a separately reviewed successor, no overwrite')
    if a.with_reference_protocol and not Path('/usr/bin/expect').is_file():raise SystemExit('Real platform Expect is required; no fake Tcl parser substitutes')
    out.mkdir();started=time.monotonic()
    sys.path.insert(0,str(BASE/'fixture'));from owned_process import Owner
    owner=Owner(out)
    def bounded(limit):
        left=150-(time.monotonic()-started)
        if left<=0:raise TimeoutError('150-second work envelope exhausted')
        return min(limit,left)
    tools=out/'tools';tools.mkdir()
    for name,source in [('crash',BASE/'fixture/crash_stub.py'),('uname',BASE/'fixture/uname_stub.py')]:
        (tools/name).write_bytes(source.read_bytes());(tools/name).chmod(0o755)
    prefix=out/'prefix';prefix.mkdir()
    env={k:v for k,v in os.environ.items() if not k.startswith('VM_FIXTURE_') and k not in ['LD_PRELOAD','LD_LIBRARY_PATH','BASH_ENV','ENV','SHELLOPTS','BASHOPTS']}
    env.update(LC_ALL='C',PATH=str(tools)+':'+env.get('PATH','/usr/bin:/bin'),VMCORE_INSTALLDIR=str(prefix),VMCORE_ARCH='x86_64',VMCORE_CRASH=str(tools/'crash'),VMCORE_PROMPT_TIMEOUT_MS='1000')
    rustc=shutil.which(a.rustc)
    if not rustc:raise SystemExit('Qualified host rustc absent')
    binary=out/'vmcore2mckdump-rust'
    command=[rustc,'--edition=2021','-C','opt-level=2',str(BASE/'vmcore2mckdump.rs'),'-o',str(binary)]
    (out/'compile-command.json').write_text(json.dumps({'argv':command,'config':{k:env[k] for k in ['VMCORE_INSTALLDIR','VMCORE_ARCH','VMCORE_CRASH','VMCORE_PROMPT_TIMEOUT_MS']}},indent=2)+'\n')
    built=owner.run(command,env,BASE,bounded(60),'rust-build')
    if built.returncode:raise RuntimeError('Rust compile failed; source remains unqualified, no retry')
    template=(BASE/'reference/vmcore2mckdump.in').read_text().replace('@prefix@',str(prefix)).replace('@ARCH@','x86_64')
    reference=out/'vmcore2mckdump-reference';reference.write_text(template);reference.chmod(0o755)
    protocol_reference=out/'vmcore2mckdump-reference-private-crash-binding'
    if a.with_reference_protocol:
        # Retain exact original separately. These are only declared fixture
        # literal bindings, not a reconstructed Tcl or dump-format parser.
        protocol_reference.write_text(template.replace('/usr/bin/crash',str(tools/'crash')).replace('set timeout 300','set timeout 1'))
        protocol_reference.chmod(0o755)
    results=[]
    for index,case in enumerate(cases):
        d=out/('%02d-%s'%(index,case['name']));d.mkdir();infile=d/'vmcore';infile.write_bytes(b'synthetic input gate only\n')
        (d/'input-directory').mkdir();outfile=d/'mckdump'
        if case.get('old'):outfile.write_bytes(OLD)
        bindings={'{in}':str(infile),'{out}':str(outfile),'{missing}':str(d/'absent'),'{indir}':str(d/'input-directory'),'{no_parent}':str(d/'no-parent')}
        args=[bindings.get(x,x) if x!='{no_parent}/out' else str(d/'no-parent/out') for x in case.get('args',['{in}','{out}'])]
        child_env=dict(env,VM_FIXTURE_TRACE=str(d/'rust-crash.json'),VM_FIXTURE_UNAME_TRACE=str(d/'rust-uname.json'),VM_FIXTURE_MODE=case.get('mode','success'),VM_FIXTURE_BYTES=base64.b64encode(BYTES).decode(),VM_FIXTURE_UNAME_STATUS=str(case.get('uname_status',0)))
        run=owner.run([str(binary)]+args,child_env,BASE,bounded(8),'%02d-rust'%index)
        output=outfile.read_bytes() if outfile.is_file() else None
        expected=BYTES if case['status']==0 else OLD if case.get('old') else None
        ok=run.returncode==case['status'] and output==expected
        trace=json.loads((d/'rust-crash.json').read_text()) if (d/'rust-crash.json').exists() else None
        uname=json.loads((d/'rust-uname.json').read_text())
        ok=ok and uname['argv'][1:]==['-r']
        if trace:
            ok=ok and trace['argv'][1:]==['/usr/lib/debug/lib/modules/fixture-linux/vmlinux',str(infile)]
            if case['status']==0:
                expected_commands=['mod -s ihk_smp_x86 '+str(prefix)+'/kmod/ihk-smp-x86.ko','extend '+str(prefix)+'/lib/ldump2mcdump.so','ldump2mcdump 0 -o '+trace['staging_output'],'extend -u '+str(prefix)+'/lib/ldump2mcdump.so','quit']
                ok=ok and trace['commands']==expected_commands
                ok=ok and trace['env']=={'VMLINUX':'/usr/lib/debug/lib/modules/fixture-linux/vmlinux','INSTALLDIR':str(prefix),'INFILE':str(infile),'OUTFILE':str(outfile)}
        if case['status']==0:ok=ok and run.stdout.endswith(('mcdump: '+str(outfile)+' is extracted.\n').encode())
        reference_result=None
        if case.get('cli_parity'):
            ref_env=dict(child_env,VM_FIXTURE_TRACE=str(d/'reference-crash.json'),VM_FIXTURE_UNAME_TRACE=str(d/'reference-uname.json'))
            ref=owner.run([str(reference)]+args,ref_env,BASE,bounded(5),'%02d-cli-reference'%index)
            ok=ok and (run.returncode,run.stdout,run.stderr)==(ref.returncode,ref.stdout,ref.stderr)
            reference_result={'classification':'original CLI parity before Expect','status':ref.returncode}
        elif a.with_reference_protocol:
            # Independent reference path, so observed legacy truncation/false
            # success cannot overwrite Rust's intended-behavior evidence.
            refout=d/'legacy-output'
            if case.get('old'):refout.write_bytes(OLD)
            refargs=[str(refout) if x==str(outfile) else x for x in args]
            ref_env=dict(child_env,OUTFILE=str(refout),VM_FIXTURE_TRACE=str(d/'reference-crash.json'),VM_FIXTURE_UNAME_TRACE=str(d/'reference-uname.json'))
            ref=owner.run([str(protocol_reference)]+refargs,ref_env,BASE,bounded(8),'%02d-protocol-reference'%index)
            reference_result={'classification':'original Expect driver observation, separate from intended behavior','status':ref.returncode,'output_hex':refout.read_bytes().hex() if refout.is_file() else None}
        results.append({'name':case['name'],'passed_intended_contract':bool(ok),'rust_status':run.returncode,'reference':reference_result,'payload_format':'synthetic bytes only','retained_staging':[str(x) for x in d.glob('.vmcore2mckdump-*.tmp')]})
    observation={'classification':'real Expect present; reference protocol requires the explicit private-crash-binding option' if Path('/usr/bin/expect').is_file() else 'real Expect prerequisite absent; no protocol parity claimed'}
    if not Path('/usr/bin/expect').is_file():
        d=out/'legacy-false-success-observation';d.mkdir();infile=d/'vmcore';infile.write_bytes(b'synthetic input\n');outfile=d/'existing';outfile.write_bytes(OLD)
        obs_env=dict(env,VM_FIXTURE_UNAME_TRACE=str(d/'uname.json'))
        ref=owner.run([str(reference),str(infile),str(outfile)],obs_env,BASE,bounded(5),'legacy-false-success')
        observation.update(reference_status=ref.returncode,old_bytes_preserved=outfile.read_bytes()==OLD,observed_stdout_hex=ref.stdout.hex(),observed_stderr_hex=ref.stderr.hex(),intended_acceptance=False)
    summary={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PASS_CLI_AND_RUST_PTY_STUB_CONTRACT_ONLY' if all(x['passed_intended_contract'] for x in results) else 'FAIL','cases':len(results),'failed':[x['name'] for x in results if not x['passed_intended_contract']],'results':results,'legacy_observation':observation,'reference_protocol_executed':a.with_reference_protocol,'converter_patch_executed':False,'real_dump_format_validated':False,'production_acceptance':False,'elapsed_seconds':round(time.monotonic()-started,3)}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k!='results'}));return 0 if summary['status'].startswith('PASS_') else 1
if __name__=='__main__':sys.exit(main())
