"""One fixed actual Linux C body/strict Python evaluator check; no native work."""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,os,resource,signal,sys,time
N=Path(__file__).resolve().parent
START=time.monotonic();WORK=N/'ordinary-check-1'
def need(value,message):
 if not value:raise AssertionError(message)
def ref(p):
 p=Path(p);raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def load(p,name):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def dump(p,value):
 with p.open('x') as f:json.dump(value,f,sort_keys=True);f.write('\n')
pins=json.loads((N/'CHECK-INPUT-PINS.json').read_bytes())
for pin in pins:need(ref(pin['path'])==pin,'frozen input '+pin['path'])
need(os.sched_getaffinity(0)=={6},'exact CPU6')
need(resource.getrlimit(resource.RLIMIT_AS)[0]<=1<<30 and resource.getrlimit(resource.RLIMIT_CPU)[0]<=30 and resource.getrlimit(resource.RLIMIT_FSIZE)[0]<=32<<20,'actual caps')
need(not WORK.exists(),'fresh whole workspace');WORK.mkdir(mode=0o700)
profile=json.loads((N/'COMMAND-SET.json').read_bytes())
need(profile['scope']=='OFFLINE_FIXED_TWO_ROUNDS_ONLY','fixed scope')
executor=load(Path(profile['capture_executor']['path']),'accepted_owned_capture')
for sig in executor.STOP_SIGNALS:signal.signal(sig,executor.stop)
rows=[]
def run(name,argv):
 remain=28-(time.monotonic()-START);need(remain>0,'shared28second work budget')
 p=WORK/name;p.mkdir(mode=0o700);dump(p/'command.json',{'argv':argv})
 row=executor.owned_capture({'argv':argv},p,remain,lambda:None);row['argv']=argv;executor.write(p/'status.json',row);rows.append({'name':name,**row})
 need(row['returncode']==0 and row['direct_child_joined'] and row['group_absent'] and row['closed_streams'] and not row['error'] and not row['retirement_error'],'clean direct capture '+name)
 need(row['captures']['stderr']['size']==0,'empty stderr '+name)
 return (p/'stdout').read_text()
flags=['/usr/bin/gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-static','-fno-pie','-no-pie','-Wl,-z,noexecstack','-DND_CORE_THREADS']
run('compile-default',flags+[str(N/'candidate/pair_collector.c'),'-o',str(WORK/'collector-one-pair')])
run('compile-two-rounds',flags+['-DND_PAIR_TWO_ROUNDS',str(N/'candidate/pair_collector.c'),'-o',str(WORK/'collector-two-rounds')])
run('compile-actual-body',flags+[str(N/'fixtures/actual_two_round_body.c'),'-o',str(WORK/'actual-body')])
checks=[];positive=None
expect={0:(0,1,1,2,4),1:(-1,1,0,1,2),2:(-1,1,0,1,2),3:(-1,0,0,1,0),4:(-1,1,0,1,2),5:(-1,1,0,2,4),6:(-1,1,0,2,4),7:(-1,1,0,2,2),8:(-1,1,0,2,4),9:(-1,1,0,1,2)}
names=['two-round-success','first-byte-oracle-stops-second','first-startup-CPU-stops-second','unsafe-worker-stops-second','procfs-not-empty-stops-second','cross-round-PID-reuse','cross-round-token-reuse','workspace-not-empty','second-byte-oracle','same-round-token-reuse']
for scenario in range(10):
 cwd=WORK/('workspace-'+str(scenario));cwd.mkdir(mode=0o700)
 serial=run('actual-body-'+str(scenario),[str(WORK/'actual-body'),str(scenario),str(cwd)])
 record=json.loads(next(x.partition(' ')[2] for x in serial.splitlines() if x.startswith('FIXTURE_RESULT ')))
 need(tuple(record[k] for k in ('result','safe','empty','runs','launches'))==expect[scenario],names[scenario])
 emitted=serial.count('ND_PAIR_ROUNDS_COMPLETE ')
 need(emitted==(scenario==0),'no success on failure')
 need(len(list((cwd/'case/evidence').glob('round*/round.json')))==(2 if scenario==0 else (1 if scenario in (5,6,7,8) else 0)),'per-round retained evidence')
 checks.append(names[scenario])
 if scenario==0:positive=serial
# Genuine saved successful thread trace exercises the same production C gate.
saved=(N/'fixtures/actual-saved-klog.txt').read_text()
child=next(line for line in saved.splitlines() if 'application procfs published os=0 generation=1 pid=257 tid=' in line and not line.endswith('tid=257'))
leader=next(line for line in saved.splitlines() if 'application procfs published os=0 generation=1 pid=257 tid=257' in line)
trace_cases=[('actual-saved-child-TIDs-positive',saved,0),('invalid-child-tid',saved.replace(child,child.rsplit('tid=',1)[0]+'tid=0',1),-1),('wrong-child-generation',saved.replace(child,child.replace('generation=1','generation=2'),1),-1),('unknown-child-procfs-op',saved.replace(child,child.replace('procfs published','procfs unknown'),1),-1),('duplicate-leader-publication',saved.replace(leader,leader+'\n'+leader,1),-1)]
for index,(name,serial,expected) in enumerate(trace_cases):
 path=WORK/('saved-trace-'+str(index));path.write_text(serial)
 cwd=WORK/('saved-workspace-'+str(index));cwd.mkdir(mode=0o700)
 text=run(name,[str(WORK/'actual-body'),'10',str(cwd),str(path)])
 need(text.strip()=='SAVED_GATE_RESULT '+str(expected),name);checks.append(name)
oracle=json.loads((N/'FROZEN-ROUND-ORACLE.json').read_bytes())
m=load(N/'candidate/native_diagnostic.py','actual_strict_two_round_evaluator')
manifest={'case_id':'fixed-two-round-offline','pair':{'apps':oracle['apps']},'pair_rounds':2}
observation={'serial':positive,'debugcon':'','qmp':{'status':'shutdown'},'teardown':True,'started_at':1,'finished_at':2,'deadline':3,'process_identity':{'pid':101,'pgid':101,'sid':101,'starttime_ticks':1}}
result=m.evaluate(manifest,observation)
need(result['pair_metrics']['completed_apps']==4 and result['pair_metrics']['completed_rounds']==2 and not result['application_acceptance'] and not result['mckernel_application_executed'],'actual complete evaluator path')
checks.append('actual-complete-evaluate-positive')
# Preserve the exact original one-pair validation body, not a weakened parallel checker.
original=ast.parse((N/'original/native_diagnostic.py').read_text());candidate=ast.parse((N/'candidate/native_diagnostic.py').read_text())
for name in ('_pair_body','_pair_trace'):
 a=next(x for x in original.body if isinstance(x,ast.FunctionDef) and x.name==name);b=next(x for x in candidate.body if isinstance(x,ast.FunctionDef) and x.name==name)
 need(ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False),'unchanged original '+name)
checks.append('original-one-pair-checkers-AST-identical')
negatives=[]
def refuse(name,serial,manifest_value=None):
 try:m.evaluate(manifest_value or manifest,dict(observation,serial=serial))
 except (ValueError,AssertionError,KeyError,TypeError) as e:negatives.append({'name':name,'reason':str(e)});return
 raise AssertionError('accepted '+name)
def mutate(prefix,index,fn):
 lines=positive.splitlines();seen=0
 for j,line in enumerate(lines):
  if line.startswith(prefix+' '):
   if seen==index:
    row=json.loads(line.partition(' ')[2]);fn(row);lines[j]=prefix+' '+json.dumps(row,separators=(',',':'));return '\n'.join(lines)+'\n'
   seen+=1
 raise AssertionError('unreachable mutation')
refuse('missing-second-round',positive.replace(next(x for x in positive.splitlines(keepends=True) if x.startswith('ND_PAIR_ROUND_END ') and '"round":1' in x),''))
refuse('duplicate-round',positive.replace('ND_PAIR_ROUNDS_COMPLETE ',next(x for x in positive.splitlines() if x.startswith('ND_PAIR_ROUND_END '))+'\nND_PAIR_ROUNDS_COMPLETE '))
refuse('cross-round-duplicate-PID',mutate('ND_PAIR',1,lambda r:r['apps'][0].update(pid=1001)))
refuse('handoff-before-first-reap',mutate('ND_PAIR_ROUND_START',1,lambda r:r.update(time_ns=1)))
refuse('wrong-round-index',mutate('ND_PAIR_ROUND_END',1,lambda r:r.update(round=0)))
refuse('false-procfs-handoff',mutate('ND_PAIR_ROUND_START',1,lambda r:r.update(procfs_empty=False)))
refuse('wrong-second-oracle',mutate('ND_PAIR',1,lambda r:r['apps'][0]['streams']['stdout'].update(hex='00'+r['apps'][0]['streams']['stdout']['hex'][2:])))
refuse('missing-second-EOF',mutate('ND_PAIR',1,lambda r:r['apps'][1]['streams']['stderr'].update(eof=False)))
refuse('wrong-second-startup-CPU',positive.replace('pid=1003 worker=6003 delivery=1 cpu=0 number=157','pid=1003 worker=6003 delivery=1 cpu=1 number=157'))
refuse('cross-round-token-reuse',positive.replace('pid=1003 token=10031','pid=1003 token=10011'))
refuse('foreign-application',positive+'application SCHEDULE os=0 generation=1 pid=9999 cpu=0\n')
refuse('unknown-round-marker',positive+'ND_PAIR_ROUND_BOGUS {}\n')
refuse('two-boots',positive+'NATIVE_PAIR_CPU os=0 generation=1 assigned_host=1,2 logical=0,1 default_ikc_linux=0\n')
refuse('round-count-not-a-duration-knob',positive,dict(manifest,pair_rounds=50))
report={'status':'PASS_ACTUAL_BODY_TWO_ROUND_OFFLINE_ONLY','checks':checks,'actual_C_scenarios':15,'Python_refusals':negatives,'actual_compiler_captures':len(rows),'elapsed_seconds':time.monotonic()-START,'native_guests':0,'actual_application_launches':0,'repeatability_quotas':'UNRUN','production_pair_run_and_klog_and_procfs':'EXPLICIT_TEST_BOUNDARIES','actual_evaluator_result':result,'commands':[{'name':r['name'],'argv':r.get('argv'),'returncode':r['returncode']} for r in rows]}
dump(WORK/'result.json',report)
print(json.dumps({'status':report['status'],'actual_C_scenarios':15,'Python_refusals':len(negatives),'compile_commands':3,'actual_body_checks':len(checks)}))
