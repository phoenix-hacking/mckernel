#!/usr/bin/python3
"""One bounded actual caller regression; owned child + synthetic proc view.
Actual /proc child tuples prove S/R changes with same PID/start/flags. Old caller
and corrected caller both execute; impossible-to-force PID reuse/kernel changes
are explicit synthetic stat counterexamples through production reader/caller IO.
No root/whole-host census/archives/unchanged mount-suite replay.
"""
import argparse,ast,hashlib,importlib.util,json,os,signal,subprocess,sys,threading,time
from pathlib import Path
BASE=Path(__file__).resolve().parent

def load(path,name):
    sys.dont_write_bytecode=True
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def wait_state(m,pid,wanted,timeout=2):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        value=m.proc_identity(pid)
        if value[2]==wanted:return value
        time.sleep(.001)
    raise RuntimeError('owned child did not reach '+wanted)

def fixture(out,m,pid,control,kind,old=False):
    out.mkdir();proc=out/'proc';proc.mkdir();entry=proc/str(pid);entry.mkdir();task=entry/'task'/str(pid);task.mkdir(parents=True);(task/'ns').mkdir();(task/'fd').mkdir()
    oracle=json.loads((BASE/'all-retained-loop36-view-oracle.json').read_text())
    view=next(v for v in oracle['distinct_views'] if any(p['pid']==416 for p in v['PIDstart_members']))
    (task/'mountinfo').write_text('\n'.join(view['raw_loop36_rows'])+'\n');(task/'ns/mnt').symlink_to('SYNTHETIC_CANONICAL_NO_ALIAS_AUTHORITY')
    (task/'stat').symlink_to('/proc/%s/task/%s/stat'%(pid,pid))
    for n,p in [('cwd','/tmp'),('root','/'),('exe','/usr/bin/python3')]: (task/n).symlink_to(p)
    os.mkfifo(task/'maps')
    wait_state(m,pid,'S')
    synthetic=kind in ('changed-start','changed-PID-header','kernel-classification','nonclassification-flags','non-RS-state')
    if synthetic:(entry/'stat').write_bytes(Path('/proc',str(pid),'stat').read_bytes())
    before=m.proc_identity(pid)
    if kind=='R-to-S':
        os.write(control,b'R');before=wait_state(m,pid,'R')
    events={};thread_errors=[]
    def writer():
        try:
            with (task/'maps').open('w'):
                events['actual_before_event']=list(m.proc_identity(pid))
                if kind=='R-to-S':events['actual_after_event']=list(wait_state(m,pid,'S'))
                elif kind=='terminal-transition':
                    os.kill(pid,signal.SIGTERM);events['actual_after_event']=list(wait_state(m,pid,'Z'))
                else:
                    os.write(control,b'R');events['actual_after_event']=list(wait_state(m,pid,'R'))
                    if synthetic:
                        raw=(entry/'stat').read_bytes();left,sep,right=raw.rpartition(b') ');f=right.split();f[0]=b'R'
                        if kind=='changed-start':f[19]=str(int(f[19])+1).encode()
                        if kind=='changed-PID-header':left=str(pid+1).encode()+left[len(str(pid)):]
                        if kind=='kernel-classification':f[6]=str(int(f[6])^0x200000).encode()
                        if kind=='nonclassification-flags':f[6]=str(int(f[6])^0x40).encode()
                        if kind=='non-RS-state':f[0]=b'T'
                        (entry/'stat').write_bytes(left+sep+b' '.join(f)+b'\n')
                    if kind=='task-set-race':(entry/'task'/'999999999').mkdir()
                    if kind=='namespace-race':(task/'ns/mnt').unlink();(task/'ns/mnt').symlink_to('CHANGED_CANONICAL_NO_ALIAS_AUTHORITY')
                    if kind=='mountinfo-race':
                        raw=(task/'mountinfo').read_text();first,rest=raw.split(' ',1);(task/'mountinfo').write_text(str(int(first)+100000)+' '+rest)
        except BaseException as exc:thread_errors.append(repr(exc))
    thread=threading.Thread(target=writer,daemon=True);thread.start();error=None
    try:
        kwargs={'proc_root':proc}
        if synthetic:kwargs['identity_root']=proc
        value=m.process_census({'rows':[],'target_fds':[],'parent_fds':[]},**kwargs)
        assert len(value)==1
    except BaseException as exc:error=repr(exc)
    thread.join(timeout=3);assert not thread.is_alive() and not thread_errors,(thread.is_alive(),thread_errors)
    after=m.proc_identity(pid)
    expected={'changed-start':'PID/start identity changed','changed-PID-header':'PID/header mismatch','kernel-classification':'kernel classification changed','nonclassification-flags':'flags changed','non-RS-state':'scan/skip state changed','terminal-transition':'terminal classification changed','task-set-race':'task set raced','namespace-race':'namespace/mountinfo/start raced','mountinfo-race':'namespace/mountinfo/start raced'}.get(kind)
    if old:expected='process identity changed'
    ok=(error is None) if expected is None else error is not None and expected in error
    if kind in ('S-to-R','R-to-S'):
        assert before[0]==after[0] and before[1]==after[1]
        assert before[2]!=after[2] and {before[2],after[2]}=={'R','S'},(before,after)
    if not old and expected and kind in ('changed-start','changed-PID-header','kernel-classification','nonclassification-flags','non-RS-state','terminal-transition'):
        assert 'pid='+str(pid) in error,error
    result={'status':'PASS' if ok else 'FAIL','case':kind,'old_caller':old,'expected_refusal':expected,'error':error,'real_child_PID':pid,
            'actual_before_tuple':list(before),'actual_after_tuple':list(after),'events':events,'identity_stat_input':'synthetic counterexample' if synthetic else 'real kernel child stat',
            'production_caller':'process_census','proc_reader_or_stability_helper_mocks':False}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');assert ok,result
    if kind!='terminal-transition':wait_state(m,pid,'S')
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output);out.mkdir(exist_ok=False)
    oldpath=BASE/'source-f25-attempt4-identity-failure/exact120.py';old=load(oldpath,'oldf25');new=load(BASE/'exact120.py','corrected_identity')
    oldast=ast.parse(oldpath.read_text());newast=ast.parse((BASE/'exact120.py').read_text());names=('decode_mount','parse_mounts','canonical_path','mount_require','authenticated_mount_view','task_view')
    def functions(tree):return {n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,ast.FunctionDef)}
    before,after=functions(oldast),functions(newast);assert all(before[n]==after[n] for n in names),'mount code changed'
    r,w=os.pipe();actor="import os,time\nr="+str(r)+"\nwhile os.read(r,1):\n end=time.monotonic()+0.12\n while time.monotonic()<end:pass\n"
    child=subprocess.Popen(['/usr/bin/python3','-I','-c',actor],pass_fds=(r,),stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);os.close(r)
    results=[];result={}
    try:
        wait_state(new,child.pid,'S')
        results.append(fixture(out/'old-caller-S-to-R',old,child.pid,w,'S-to-R',old=True))
        for kind in ('S-to-R','R-to-S','changed-start','changed-PID-header','kernel-classification','nonclassification-flags','non-RS-state','task-set-race','namespace-race','mountinfo-race','terminal-transition'):
            results.append(fixture(out/('corrected-'+kind),new,child.pid,w,kind))
        result={'status':'PASS_ACTUAL_PROCESS_IDENTITY_CALLER_DEBUG','results':results,'source_sha256':hashlib.sha256((BASE/'exact120.py').read_bytes()).hexdigest(),
                'old_source_sha256':hashlib.sha256(oldpath.read_bytes()).hexdigest(),'mount_functions_unchanged':list(names),'interpreter':sys.executable,'version':sys.version,
                'actual_historical_failure_field_known':False,'limit':'Genuine owned-child R/S and zombie transitions observed. Changedstart/PIDheader/kernel/otherflag negatives use explicit synthetic stat counterexamples, not forced OS PIDreuse or kthread conversion.',
                'root_observer_replayed':False,'new_host_census':False,'unchanged_mount_suites_replayed':False}
    except BaseException as exc:
        result={'status':'FAIL_PRESERVED','results':results,'error':repr(exc)};raise
    finally:
        os.close(w)
        if child.poll() is None:child.terminate()
        code=child.wait(timeout=3);result['owned_child_joined']=True;result['owned_child_returncode']=code
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'cases':len(results),'mount_functions_unchanged':True,'owned_child_joined':True,'version':sys.version.split()[0]}))

if __name__=='__main__':main()
