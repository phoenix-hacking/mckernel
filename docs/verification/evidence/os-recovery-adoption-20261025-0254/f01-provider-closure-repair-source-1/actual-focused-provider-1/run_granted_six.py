"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Fresh Root-granted six-command bounded F01 HOST provider batch, not fullcrate retry.
"""
import contextlib,hashlib,importlib.util,json,os,pathlib,resource,signal,subprocess,sys,time
A=pathlib.Path(__file__).resolve().parent;P=A.parent;D=P.parent
G=D/'m14-f06-selected-residual-implementation-20261026-1/next-process-vm-selected-1/next-prctl-getter-selected-1/actual-host-getter-1/reviewed-account-supervisor-correction-1'
def ref(p):
 p=pathlib.Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def verify(rows):
 for row in rows:assert ref(row['path'])==row,'pin drift:'+row['path']
def module(name,p):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def main():
 os.sched_setaffinity(0,{6})
 for k,v in [(resource.RLIMIT_AS,2*2**30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,64*2**20),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
 assert ref(G/'run_sealed.py')['sha256']=='e8b84de39128433542b213fc3a374dd50d3e12f232bd397dddaa24859349a805';sys.path.insert(0,str(G));guard=module('f01_bounded_guard',G/'run_sealed.py')
 recipe=P/'EXACT-ROOT-PROPOSED-RECIPE.NOT-ADMITTED.json';assert ref(recipe)['sha256']=='6539ad566bb18fbbfc4963090640b7f80c5462ecf5389f4b79f4e4df251f54d7';assert ref(P/'PROVIDER-SOURCE-BINDING.json')['sha256']=='40184c5ad44dc6c8969c241a4edf11985edab6e916958bf20270b5c2730221da';plan=json.load(open(recipe));supplement=json.load(open(A/'SUPPLEMENTAL-HEADER-TOOLS.json'));static=module('f01_frozen_source_verifier',P/'verify_source.py')
 assert pathlib.Path(plan['output_directory'])==A;logs=A/'logs';logs.mkdir(mode=0o700)
 with (A/'STATIC-PREFLIGHT.stdout').open('x') as out,contextlib.redirect_stdout(out):static.main()
 verify(plan['inputs']+plan['tools']+supplement['headers']+supplement['tools']);initial=guard.admission();results=[];failure=None
 try:
  for index,command in enumerate(plan['commands']):
   verify(plan['inputs']+plan['tools']+supplement['headers']+supplement['tools']);assert ref(recipe)['sha256']=='6539ad566bb18fbbfc4963090640b7f80c5462ecf5389f4b79f4e4df251f54d7';assert ref(P/'PROVIDER-SOURCE-BINDING.json')['sha256']=='40184c5ad44dc6c8969c241a4edf11985edab6e916958bf20270b5c2730221da'
   admission=guard.admission();wall=time.time();start=time.monotonic();stdoutfile=pathlib.Path(command['stdout']) if 'stdout'in command else logs/(str(index)+'.stdout')
   with stdoutfile.open('xb') as out,(logs/(str(index)+'.stderr')).open('xb') as err:
    child=subprocess.Popen(command['argv'],cwd=plan['cwd'],env=plan['environment'],stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True,close_fds=True)
    while True:
     pid,status,u=os.wait4(child.pid,os.WNOHANG)
     if pid:break
     if time.monotonic()-start>=90:os.killpg(child.pid,signal.SIGKILL);pid,status,u=os.wait4(child.pid,0);break
     time.sleep(.01)
    child.returncode=os.waitstatus_to_exitcode(status)
   try:os.killpg(child.pid,0);absent=False
   except ProcessLookupError:absent=True
   row=dict(index=index,argv=command['argv'],purpose=command['purpose'],pid=child.pid,started_wall=wall,elapsed=time.monotonic()-start,returncode=child.returncode,CPU_user=u.ru_utime,CPU_system=u.ru_stime,max_RSS_KiB=u.ru_maxrss,direct_wait=True,group_absent=absent,closed_streams=True,admission=admission,stdout=ref(stdoutfile),stderr=ref(logs/(str(index)+'.stderr')));results.append(row);(A/'RESULTS.json').write_text(json.dumps(dict(status='RUNNING',results=results),indent=2)+'\n')
   if child.returncode or not absent:raise RuntimeError('firstfailure index'+str(index))
   if index==2:
    origins=json.load(open(A/'EXACT-TESTED-PROVIDER-ORIGINS.json'));assert origins['status']=='PASS_ALL_77_TESTED_EXTERNS_FROM_EXACT_RUST_PROVIDER' and len(origins['functions'])==77
 except BaseException as exc:failure=repr(exc)
 final=dict(scope=__doc__.strip(),status='FAIL_BOUNDED_PROVIDER_FIRST_FAILURE_STOPPED' if failure else 'PASS_BOUNDED_PROVIDER_ORIGINAL_F01_COMPARATOR_AND_ALL77_ORIGINS',recipe=ref(recipe),binding=ref(P/'PROVIDER-SOURCE-BINDING.json'),initial_admission=initial,results=results,failure=failure,first_compiler_timestamp=results[0]['started_wall'] if results else None,fixture_executions=sum(x['index']in (3,4) and x['returncode']==0 for x in results),exact77origins_pass=any(x['index']==2 and x['returncode']==0 for x in results),exact_stdout_diff_pass=any(x['index']==5 and x['returncode']==0 for x in results),no_seven_prefix_recompile=True,production_object_mutated=False,native_runs=0,whole_file_acceptance=False)
 (A/'RESULTS.json').write_text(json.dumps(final,indent=2)+'\n');print(json.dumps(dict(status=final['status'],commands=len(results),failure=failure,all_joined=all(x['direct_wait'] and x['group_absent'] for x in results))))
 if failure:sys.exit(1)
if __name__=='__main__':main()
