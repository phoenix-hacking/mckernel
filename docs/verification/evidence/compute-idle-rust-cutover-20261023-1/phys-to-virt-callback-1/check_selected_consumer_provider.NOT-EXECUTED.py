"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
PREPARED ONLY: exact ordinary compile grant required. No Docker/root/guest.
Actual complete selected memory.c + Rustmodule callback ownership/ABI/partiallink.
"""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys,time
D=Path(__file__).resolve().parent
NAME='x86_clear_phys_to_virt_bridge'
def main():
    assert sys.argv[1:]==['--ordinary-compile-granted'],'dispatcher compile grant required'
    assert os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={0}
    bindings=json.loads((D/'SOURCE-BINDINGS.json').read_text())
    for row in bindings['candidate'].values():
        assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['sha256'],'candidate drift'
    commands=json.loads((D/'PREPARED-COMMANDS.NOT-EXECUTED.json').read_text())
    out=Path(commands['output']);out.mkdir(mode=0o700)
    report=dict(scope=__doc__.splitlines()[0],status='FAIL_FIRST_COMMAND_RETAINED',commands=[],root=0,Docker=0,guest=0,native=False,fullcrate=False,image_link=False)
    start=time.monotonic()
    def run(label):
        argv=commands[label];(out/(label+'.argv.json')).write_text(json.dumps(argv,indent=2)+'\n')
        p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=dict(os.environ,RUST_MIN_STACK='2097152'),timeout=35)
        (out/(label+'.stdout')).write_bytes(p.stdout);(out/(label+'.stderr')).write_bytes(p.stderr)
        report['commands'].append(dict(label=label,returncode=p.returncode,direct_child_joined=True))
        if p.returncode:raise RuntimeError('first failed command: '+label)
        return p.stdout.decode()
    def count(text,kind):return sum(len(x.split())>=2 and x.split()[-1]==NAME and x.split()[-2]==kind for x in text.splitlines())
    try:
        pp=run('preprocess')
        assert 'extern void *'+NAME+'(unsigned long phys);' in pp
        assert not re.search(r'\b'+NAME+r'\s*\([^;{}]*\)\s*\{',pp,re.S),'selected C body remains'
        run('whole_C_TU');assert count(run('nm_imports'),'U')==1
        c_symbols=run('nm_C');assert count(c_symbols,'t')==0 and count(c_symbols,'T')==0
        assert NAME in run('relocations'),'actual selected consumer relocation absent'
        run('whole_Rust_module');assert count(run('nm_Rust'),'T')==1,'Rust provider must be unique'
        run('partial_link');joined=run('nm_partial')
        assert count(joined,'T')==1 and count(joined,'U')==0,'callback unresolved/duplicate after partial link'
        report.update(status='PASS_SELECTED_WHOLE_C_TU_RUST_PROVIDER_ABI_PARTIAL_LINK_ONLY',callback_unique=True,callback_resolved=True)
    except BaseException as exc:report['error']=repr(exc)
    report['seconds']=time.monotonic()-start
    (out/'RESULT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
    return 0 if report['status'].startswith('PASS') else 1
if __name__=='__main__':raise SystemExit(main())
