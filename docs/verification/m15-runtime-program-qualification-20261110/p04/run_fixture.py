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
    results=[];owner=None
    state={'phase':'owner-setup','label':None,'argv':None,'case':None}
    def checked_run(argv,env,cwd,limit,label):
        state.update(phase='child:'+label,label=label,argv=list(argv))
        previous=len(owner.records)
        completed=owner.run(argv,env,cwd,bounded(limit),label)
        if len(owner.records)!=previous+1:
            raise RuntimeError(label+' must return exactly one new ownership record')
        record=owner.records[-1]
        state.update(leader=record.get('leader'),leader_birth=record.get('leader_birth'))
        required={'label':label,'status':completed.returncode,'leader_parent_joined':True,
                  'whole_descendants_joined':True,'streams_closed':True,'error':None,
                  'timed_out':False,'leader_group_signalled':False,'adopted_reaps':[],
                  'adopted_kills':[],'remaining_direct_children':[]}
        bad=[key for key,value in required.items() if key not in record or record[key]!=value]
        if type(record.get('leader')) is not int or record['leader']<=0:bad.append('leader')
        birth=record.get('leader_birth')
        if not isinstance(birth,str) or not birth.isdigit() or int(birth)<=0:bad.append('leader_birth')
        if type(record.get('status')) is not int or type(completed.returncode) is not int:bad.append('status_type')
        if completed.args!=argv:bad.append('returned_argv')
        if bad:raise RuntimeError(label+' ownership-success facts failed: '+','.join(bad))
        return completed
    try:
        sys.path.insert(0,str(BASE/'fixture'));from owned_process import Owner
        owner=Owner(out)
        def bounded(limit):
            left=150-(time.monotonic()-started)
            if left<=0:raise TimeoutError('150-second work envelope exhausted')
            return min(limit,left)
        state['phase']='tool-setup'
        tools=out/'tools';tools.mkdir()
        for name,source in [('crash',BASE/'fixture/crash_stub.py'),('uname',BASE/'fixture/uname_stub.py')]:
            (tools/name).write_bytes(source.read_bytes());(tools/name).chmod(0o755)
        prefix=out/'prefix';prefix.mkdir()
        env={k:v for k,v in os.environ.items() if not k.startswith('VM_FIXTURE_') and k not in ['LD_PRELOAD','LD_LIBRARY_PATH','BASH_ENV','ENV','SHELLOPTS','BASHOPTS']}
        env.update(LC_ALL='C',PATH=str(tools)+':'+env.get('PATH','/usr/bin:/bin'),VMCORE_INSTALLDIR=str(prefix),VMCORE_ARCH='x86_64',VMCORE_CRASH=str(tools/'crash'),VMCORE_PROMPT_TIMEOUT_MS='1000')
        state.update(phase='compiler-binding',argv=[a.rustc],label=None,case=None)
        rustc=shutil.which(a.rustc)
        if not rustc:raise SystemExit('Qualified host rustc absent')
        binary=out/'vmcore2mckdump-rust'
        command=[rustc,'--edition=2021','-C','opt-level=2','-C','debuginfo=1',str(BASE/'vmcore2mckdump.rs'),'-o',str(binary)]
        state.update(phase='compile-command',argv=list(command),label='rust-build')
        (out/'compile-command.json').write_text(json.dumps({'argv':command,'config':{k:env[k] for k in ['VMCORE_INSTALLDIR','VMCORE_ARCH','VMCORE_CRASH','VMCORE_PROMPT_TIMEOUT_MS']}},indent=2)+'\n')
        built=checked_run(command,env,BASE,60,'rust-build')
        state['phase']='compiler-status'
        if built.returncode:raise RuntimeError('Rust compile failed; source remains unqualified, no retry')
        state['phase']='reference-setup'
        template=(BASE/'reference/vmcore2mckdump.in').read_text().replace('@prefix@',str(prefix)).replace('@ARCH@','x86_64')
        reference=out/'vmcore2mckdump-reference';reference.write_text(template);reference.chmod(0o755)
        protocol_reference=out/'vmcore2mckdump-reference-private-crash-binding'
        if a.with_reference_protocol:
            # Retain exact original separately. These are only declared fixture
            # literal bindings, not a reconstructed Tcl or dump-format parser.
            protocol_reference.write_text(template.replace('/usr/bin/crash',str(tools/'crash')).replace('set timeout 300','set timeout 1'))
            protocol_reference.chmod(0o755)
        for index,case in enumerate(cases):
            state.clear();state.update(phase='case-setup',label=None,argv=None,case=case['name'],case_index=index,case_directory=str(out/('%02d-%s'%(index,case['name']))))
            d=out/('%02d-%s'%(index,case['name']));d.mkdir();infile=d/'vmcore';infile.write_bytes(b'synthetic input gate only\n')
            (d/'input-directory').mkdir();outfile=d/'mckdump'
            state.update(input=str(infile),output=str(outfile))
            if case.get('old'):outfile.write_bytes(OLD)
            bindings={'{in}':str(infile),'{out}':str(outfile),'{missing}':str(d/'absent'),'{indir}':str(d/'input-directory'),'{no_parent}':str(d/'no-parent')}
            args=[bindings.get(x,x) if x!='{no_parent}/out' else str(d/'no-parent/out') for x in case.get('args',['{in}','{out}'])]
            child_env=dict(env,VM_FIXTURE_TRACE=str(d/'rust-crash.json'),VM_FIXTURE_UNAME_TRACE=str(d/'rust-uname.json'),VM_FIXTURE_MODE=case.get('mode','success'),VM_FIXTURE_BYTES=base64.b64encode(BYTES).decode(),VM_FIXTURE_UNAME_STATUS=str(case.get('uname_status',0)))
            run=checked_run([str(binary)]+args,child_env,BASE,8,'%02d-rust'%index)
            state['phase']='output-contract'
            output=outfile.read_bytes() if outfile.is_file() else None
            expected=BYTES if case['status']==0 else OLD if case.get('old') else None
            ok=run.returncode==case['status'] and output==expected
            state['phase']='crash-trace'
            trace=json.loads((d/'rust-crash.json').read_text()) if (d/'rust-crash.json').exists() else None
            state['phase']='uname-trace'
            uname=json.loads((d/'rust-uname.json').read_text())
            state['phase']='trace-contract'
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
                ref=checked_run([str(reference)]+args,ref_env,BASE,5,'%02d-cli-reference'%index)
                ok=ok and (run.returncode,run.stdout,run.stderr)==(ref.returncode,ref.stdout,ref.stderr)
                reference_result={'classification':'original CLI parity before Expect','status':ref.returncode}
            elif a.with_reference_protocol:
                # Independent reference path, so observed legacy truncation/false
                # success cannot overwrite Rust's intended-behavior evidence.
                refout=d/'legacy-output'
                if case.get('old'):refout.write_bytes(OLD)
                refargs=[str(refout) if x==str(outfile) else x for x in args]
                ref_env=dict(child_env,OUTFILE=str(refout),VM_FIXTURE_TRACE=str(d/'reference-crash.json'),VM_FIXTURE_UNAME_TRACE=str(d/'reference-uname.json'))
                ref=checked_run([str(protocol_reference)]+refargs,ref_env,BASE,8,'%02d-protocol-reference'%index)
                reference_result={'classification':'original Expect driver observation, separate from intended behavior','status':ref.returncode,'output_hex':refout.read_bytes().hex() if refout.is_file() else None}
            state['phase']='case-contract'
            results.append({'name':case['name'],'passed_intended_contract':bool(ok),'rust_status':run.returncode,'reference':reference_result,'payload_format':'synthetic bytes only','retained_staging':[str(x) for x in d.glob('.vmcore2mckdump-*.tmp')]})
            if not ok:break  # Retain first failed candidate; no unchanged follow-on cases.
        if len(results)==len(cases) and all(x['passed_intended_contract'] for x in results):
            state.clear();state.update(phase='final-ownership',label=None,argv=None,case=None)
            if len(owner.records)!=30:raise RuntimeError('Successful22case run requires exactly30 ownership records, got '+str(len(owner.records)))
        observation={'classification':'real Expect present; reference protocol requires the explicit private-crash-binding option' if Path('/usr/bin/expect').is_file() else 'real Expect prerequisite absent; no protocol parity claimed'}
        summary={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PASS_CLI_AND_RUST_PTY_STUB_CONTRACT_ONLY' if len(results)==len(cases) and all(x['passed_intended_contract'] for x in results) else 'FAIL','cases':len(results),'expected_cases':len(cases),'ownership_records':len(owner.records),'partial':len(results)!=len(cases),'active':dict(state),'failed':[x['name'] for x in results if not x['passed_intended_contract']],'results':results,'legacy_observation':observation,'reference_protocol_executed':a.with_reference_protocol,'converter_patch_executed':False,'real_dump_format_validated':False,'production_acceptance':False,'elapsed_seconds':round(time.monotonic()-started,3)}
        (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k!='results'}));return 0 if summary['status'].startswith('PASS_') else 1
    except BaseException as primary:
        # Owner.run completes its own retirement before raising. Receipt writing
        # adds no process action and must never replace that primary failure.
        try:
            label=state.get('label')
            failure={'phase':state.get('phase'),'label':label,'argv':state.get('argv'),
                     'case':state.get('case'),'error':type(primary).__name__+': '+str(primary)}
            partial={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
                     'status':'FAIL','partial':True,'cases':len(results),'expected_cases':len(cases),
                     'results':results,'failure':failure,'active':dict(state),
                     'source':{'path':str(BASE/'vmcore2mckdump.rs'),'sha256':'44329596ff8fcb1f197878664bf4999407648f056f81280008d885802f6e5427'},
                     'case_input':str(BASE/'fixture/cases.json'),
                     'ownership_path':str(out/'ownership.json'),
                     'ownership_records':len(owner.records) if owner is not None else 0,
                     'capture_paths':[str(out/(label+suffix)) for suffix in ['.stdout','.stderr']] if label else [],
                     'reference_protocol_executed':a.with_reference_protocol,
                     'converter_patch_executed':False,'real_dump_format_validated':False,
                     'production_acceptance':False,'elapsed_seconds':round(time.monotonic()-started,3)}
            (out/'summary.json').write_text(json.dumps(partial,indent=2)+'\n')
        except BaseException as receipt_error:
            try:sys.stderr.write('Best-effort partial receipt failed: '+type(receipt_error).__name__+': '+str(receipt_error)+'\n')
            except BaseException:pass
        raise
if __name__=='__main__':sys.exit(main())
