import datetime,hashlib,importlib.util,json,math,os,pathlib,select,signal,sys,time
HERE=pathlib.Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110/native-controller-normal-transition-proposal-publicabi-max-1/current-468d-generation-1/guardian-only-recovery-1/cgroup-closure-correction-1/ownership-reference-and-liveness-correction-1');ROOT=pathlib.Path('/home/holden/mckernel');STATE=ROOT/'.git/os-autopilot';OUT=HERE/'operation-output-1'
Q=json.loads((HERE/'REQUEST.PROPOSED.json').read_text())
OWN_RAW=pathlib.Path(Q['current_ownership']['path']).read_bytes()
if len(OWN_RAW)!=Q['current_ownership']['bytes'] or hashlib.sha256(OWN_RAW).hexdigest()!=Q['current_ownership']['sha256']:
 raise RuntimeError('request-bound original ownership record changed')
OWN=json.loads(OWN_RAW);R={x['role']:x for x in OWN['roles']}
def need(ok,msg):
 if not ok:raise RuntimeError(msg)
def digest(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def record(n,v):(OUT/n).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def proc(pid):
 p=pathlib.Path('/proc')/str(pid);b=(p/'stat').read_text().rsplit(')',1)[1].split();cg=next(x.split(':',2)[2] for x in (p/'cgroup').read_text().splitlines() if x.startswith('1:name=systemd:'));u=int(next(x.split()[1] for x in (p/'status').read_text().splitlines() if x.startswith('Uid:')))
 return dict(pid=pid,birth=b[19],state=b[0],ppid=int(b[1]),uid=u,systemd_cgroup=cg,cmdline_sha256=digest(p/'cmdline'))
def same(role):
 a=proc(R[role]['pid']);need(a['state'] not in ('Z','X') and all(a[k]==R[role][k] for k in ('pid','birth','ppid','uid','systemd_cgroup','cmdline_sha256')),role+' identity changed');return a
holdkeys=('service_hold','policy_hold','auth_hold','billing_hold','budget_hold','permission_hold','transport_uncertain','pending_request','credit_budget_error')
def engine_healthy():
 s=json.loads((STATE/'state.json').read_text());g=json.loads((STATE/'guardian.json').read_text());w=json.loads((STATE/'watcher.json').read_text())
 need(s['thread_id']==OWN['root'] and s['guardian_run_id']==w['guardian_run_id']==g['run_id']==OWN['guardian_run_id'],'Root/guardian run changed')
 need((w.get('watcher_pid'),w.get('watcher_start'))==(R['watcher']['pid'],R['watcher']['birth']),'current watcher record identity differs')
 at=w.get('at');need(type(at) in (int,float) and math.isfinite(at),'current watcher heartbeat malformed')
 age=time.time()-at;need(0<=age<=90,'current watcher heartbeat stale or future')
 need((s.get('worker_pid'),s.get('worker_start'))==(R['worker']['pid'],R['worker']['birth']),'current state worker identity differs')
 need((w.get('worker_pid'),w.get('worker_start'))==(R['worker']['pid'],R['worker']['birth']),'current watcher worker identity differs')
 need((s.get('server_pid'),s.get('server_start'))==(R['server']['pid'],R['server']['birth']),'current state server identity differs')
 need(s.get('stop_reason') is None and s.get('phase')=='running' and (s.get('goal') or {}).get('status')=='active' and not any(s.get(k) for k in holdkeys),'current stop or hold')
 need(not g.get('user_stop') and not g.get('checkpoint') and not g.get('launch'),'guardian stop/checkpoint/launch exists')
 need(not (STATE/'guardian-stop.json').exists(),'normal stop request appeared')
 need((s.get('credit_budget') or {}).get('id')=='7c6ef3604bfb4008a917bba8cfb6cfaa' and (s.get('credit_budget') or {}).get('budget')=='PRIVATE_FINITE_CREDIT_CAP_REDACTED','credit identity changed')
 for role in ('watcher','worker','server'):same(role)
 return s,g,w
need(os.geteuid()==1000 and pathlib.Path.cwd()==ROOT/'scripts','ordinary same-user canonical import context')
need(pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()==OWN['boot_id'],'boot changed')
for row in Q['execution_source_guards']:need(digest(row['path'])==row['sha256'],'source pin '+row['path'])
import watch_os_goal
need(pathlib.Path(watch_os_goal.__file__).resolve()==ROOT/'scripts/watch_os_goal.py','foreign watcher import')
afe=Q['ownership']['helper'];need(digest(afe['path'])==afe['sha256'],'Owner source changed');spec=importlib.util.spec_from_file_location('reviewed_guardian_systemctl_owner',afe['path']);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);owner=mod.Owner(OUT)
serial=0
def ctl(args,timeout=4):
 global serial
 serial+=1;label='systemctl-%02d'%serial;r=owner.run(['/usr/bin/systemctl','--user']+args,env=os.environ.copy(),cwd=str(ROOT),timeout=timeout,label=label);rec=owner.records[-1]
 need(r.returncode==0 and rec['status']==0 and rec['leader_parent_joined'] and rec['whole_descendants_joined'] and rec['streams_closed'] and not rec['timed_out'] and not rec['leader_group_signalled'] and not rec['adopted_reaps'] and not rec['adopted_kills'] and not rec['remaining_direct_children'] and rec['error'] is None,'systemctl exact family failed')
 return r.stdout.decode()
def show():
 txt=ctl(['show',Q['unit'],'--property=MainPID,ExecMainPID,ExecMainCode,ExecMainStatus,ExecMainStartTimestampMonotonic,ExecMainExitTimestampMonotonic,ActiveState,SubState,Result,InvocationID,NRestarts,ControlGroup']);v=dict(x.split('=',1) for x in txt.splitlines() if '=' in x);return v
fds=[];errors=[];primary=None;tb=None;report=dict(status='NOT_ATTEMPTED',signal_attempted=False,normal_start_issued=False,native_release=False,model_retirement=False)
try:
 s,g,w=engine_healthy();same('guardian');same('inhibitor_parent');u=show();record('UNIT-BEFORE.json',u)
 need(u['MainPID']==str(R['inhibitor_parent']['pid']) and u['ExecMainPID']==str(R['inhibitor_parent']['pid']) and u['ActiveState']=='active' and u.get('InvocationID'),'actual normal unit owner differs')
 need(u.get('ControlGroup')==R['guardian']['systemd_cgroup'],'actual unit cgroup changed')
 cgpath=pathlib.Path('/sys/fs/cgroup/systemd')/R['guardian']['systemd_cgroup'].lstrip('/')/'cgroup.procs'
 oldmembers=[int(x) for x in cgpath.read_text().split()];need(set(oldmembers)=={R['guardian']['pid'],R['inhibitor_parent']['pid']},'guardian unit has other current members; preserve/reconcile')
 record('CGROUP-BEFORE.json',dict(path=str(cgpath),members=oldmembers,unit=u['ControlGroup']))
 oldinv=u['InvocationID'];record('PRE-ACTION.json',dict(roles=[same(x) for x in R],unit=u,guardian=g,watcher=w,state_worker_server={k:s.get(k) for k in ('worker_pid','worker_start','server_pid','server_start')},last_instruction=s.get('last_instruction')))
 polls=[]
 for role in ('guardian','inhibitor_parent'):
  fd=watch_os_goal.pidfd_open(R[role]['pid']);fds.append((role,fd));same(role);p=select.poll();p.register(fd,select.POLLIN);need(not p.poll(0),'old owner already terminal');polls.append((role,p))
 engine_healthy();same('guardian');same('inhibitor_parent')
 report['signal_attempted']=True;record('ACTION-ATTEMPTED.json',dict(target=R['guardian'],signal='SIGKILL',scope='confirmed unsupported-helper guardian-only technical recovery',unit=Q['unit'],native_release=False,model_signal=False))
 watch_os_goal.pidfd_send_signal(fds[0][1],signal.SIGKILL)
 end=time.monotonic()+10
 while True:
  engine_healthy();events={role:p.poll(0) for role,p in polls}
  if all(events.values()):break
  need(time.monotonic()<end,'guardian/inhibitor terminal proof unavailable');time.sleep(.02)
 record('OLD-PIDFD-TERMINAL.json',dict(events=events,roles=[R['guardian'],R['inhibitor_parent']],direct_wait_claim=False,original_parent='inhibitor waits guardian; systemd user manager owns/reaps inhibitor'))
 # Capture the real manager's old invocation terminal record before its five-second auto-restart.
 u=show();record('OLD-UNIT-TERMINAL.json',u)
 need(u.get('InvocationID')==oldinv and u.get('ExecMainPID')==str(R['inhibitor_parent']['pid']) and u.get('MainPID')=='0' and u.get('ExecMainCode') in ('1','2','3') and int(u.get('ExecMainExitTimestampMonotonic','0'))>0,'original manager terminal record not captured; no inferred reap')
 # Positive cgroup closure joins actual kernel emptiness OR the original manager's
 # explicit empty ControlGroup after terminal old invocation. Missing alone never passes.
 try:
  members=[int(x) for x in cgpath.read_text().split()]
  need(not members,'old guardian cgroup still populated')
  cgproof=dict(path=str(cgpath),kernel_members=members,manager_ControlGroup=u.get('ControlGroup'),basis='actual empty kernel member record plus two terminal pidfds and original manager exit')
 except FileNotFoundError:
  need('ControlGroup' in u and u['ControlGroup']=='','missing cgroup without positive original manager disposition')
  cgproof=dict(path=str(cgpath),kernel_members=None,manager_ControlGroup=u['ControlGroup'],basis='explicit original manager ControlGroup cleared plus old invocation terminal/reaped and two terminal pidfds; no missing-only free inference')
 record('CGROUP-AND-ORIGINAL-FD-CLOSURE.json',dict(proof=cgproof,old_known_members=oldmembers,all_old_member_pidfds_terminal=True,guardian_lock_kernel_fd_closure='terminal process closes its own FD; actual new constructor must acquire same guardian FLOCK before publishing new identity',native_or_model_release=False))
 # Starting an already auto-restarted same unit is idempotent; never restart/stop it.
 engine_healthy();ctl(['start',Q['unit']],timeout=10);report['normal_start_issued']=True
 end=time.monotonic()+90;first=None;adopted=None
 while time.monotonic()<end:
  s,g,w=engine_healthy()
  if g.get('pid')!=R['guardian']['pid']:
   a=proc(g['pid']);need(a['birth']==g.get('start') and a['uid']==1000 and a['systemd_cgroup']==R['guardian']['systemd_cgroup'],'new guardian identity/namespace')
   if first is None:first=(g['pid'],g['start'],g.get('heartbeat_at'))
   if (g['pid'],g['start'])==first[:2] and g.get('heartbeat_at',0)>first[2] and g.get('phase')=='SUPERVISED' and g.get('reason') is None and 0<=time.time()-w['at']<=90:
    adopted=(s,g,w,a);break
  time.sleep(.25)
 need(adopted is not None,'new guardian active adoption not proved')
 s,g,w,a=adopted;u=show();record('UNIT-AFTER.json',u)
 need(u.get('ActiveState')=='active' and int(u.get('MainPID','0'))==a['ppid'] and u.get('InvocationID')!=oldinv,'new normal unit parent/invocation differs')
 need(digest(Q['unit_file']['path'])==Q['unit_file']['sha256'],'unit publication changed')
 for row in Q['execution_source_guards']:need(digest(row['path'])==row['sha256'],'source changed during cold load')
 report.update(status='PASS_GUARDIAN_ONLY_COMPATIBILITY_COLD_LOAD_PENDING_SAVED_REVIEW',old_unit_invocation=oldinv,new_unit=u,new_guardian=g,preserved_engine_roles=[same(x) for x in ('watcher','worker','server')],last_instruction=s.get('last_instruction'),guardian_run_id=g['run_id'],root_thread=s['thread_id'],credit_run_id=s['credit_budget']['id'],native_release=False,model_retirement=False)
except BaseException as exc:primary=exc;tb=exc.__traceback__;report['status']='FAILED_OR_UNKNOWN_PRESERVED_NO_UNCHANGED_RETRY';report['primary_type']=type(exc).__name__
finally:
 for role,fd in reversed(fds):
  try:os.close(fd)
  except BaseException as exc:errors.append((role,fd,exc))
 report['pidfd_close_errors']=[dict(role=r,fd=f,error_type=type(e).__name__) for r,f,e in errors];report['owned_systemctl_records']=owner.records
 try:record('RESULT.json',report)
 except BaseException as exc:errors.append(('result_write',None,exc))
 interruption=next((x for x in ([primary] if primary else [])+[e for _,_,e in errors] if isinstance(x,(KeyboardInterrupt,SystemExit))),None)
 if interruption is not None:
  interruption.guardian_primary=primary;interruption.guardian_secondary=errors;raise interruption
 if primary is not None:raise primary.with_traceback(tb)
 if errors:raise RuntimeError('guardian recovery cleanup UNKNOWN; records retained')
print(json.dumps(dict(status=report['status'],native_release=False,model_retirement=False,guardian_run_id=report['guardian_run_id'])))
