from pathlib import Path
import ast,json,hashlib
E=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254');A=E/'restart-adoption-20261029T0234';D=A/'M14-WEEKLY-OPERATION-CONSUMER-SOURCE-1/actual-weekly-binding-source-1';D.mkdir(exist_ok=True);W=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1');old=A/'M14-PIPELINE-CONTROL-BINDING-PREPARATION-1/new-guardian-source-1/guardian_guard.py'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
arm=json.loads((W/'ACTUAL-CONTROLS-ARMED.json').read_bytes());config=json.loads((W/'armed-controller/CONFIG.json').read_bytes());window=json.loads((W/'ACTUAL-WINDOW.json').read_bytes());s=old.read_text()
vals={'BASE':"Path("+repr(str(W))+")",'CONTROL':'BASE','ARM_RECEIPT_REF':repr(ref(W/'ACTUAL-CONTROLS-ARMED.json')),'CONFIG_SHA':repr(ref(W/'armed-controller/CONFIG.json')['sha256']),'PACKET_SHA':repr(arm['guardian_packet_sha256']),'WINDOW_SHA':repr(ref(W/'ACTUAL-WINDOW.json')['sha256']),'DEADLINE':'1793774133','WINDOW_BOOT_CAP':repr(window['boot_deadline']),'JOURNAL_BOOT_CAP':repr(arm['caps']['boot_deadline']),'BOOT_CAP':repr(arm['caps']['boot_deadline']),'MONO_CAP':repr(arm['caps']['monotonic_deadline']),'INITIAL':repr({k:(v['pid'],v['start'])for k,v in arm['actors'].items()if k in ['watcher','worker','server']}),'GUARDIAN_LAUNCH_PPID':'1311','EXPECTED_ACTORS':repr({k:(v['pid'],v['start'])for k,v in arm['actors'].items()}),'AUX_RECORDED_PPIDS':repr({k:1311 for k in ['guardian','monitor','phone']})}
tree=ast.parse(s);lines=s.splitlines(True)
for node in tree.body:
 if isinstance(node,ast.Assign)and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
  key=node.targets[0].id
  if key in vals:lines[node.lineno-1]=key+' = '+vals[key]+'\n'
s=''.join(lines).replace('import time\n','import time\nimport os\n')
s=s.replace("    need(window.get('monotonic_deadline') == 1035706.5689547858, 'actual monotonic window')","    need(window.get('monotonic_deadline') == "+repr(window['monotonic_deadline'])+", 'actual monotonic window')")
s=s.replace("    need(window.get('credit_run_id') == RUN and Decimal(window['credit_ceiling']) == CEILING, 'window credit identity')","    need(window.get('billing_mode') == 'included_only' and window.get('allow_prepaid_fallback') is False and window.get('weekly_limit_identity') == WEEKLY_IDENTITY, 'actual weekly-only window')")
s=s.replace("    need(journal.get('credit_run_id') == RUN, 'guardian credit identity')\n    need(journal.get('original_finite') is True and journal.get('initial_prepaid_guard') is True\n         and journal.get('credit_started') is True, 'actual finite prepaid guardian')","    need(journal.get('original_finite') is True and not journal.get('initial_prepaid_guard') and not journal.get('credit_started'), 'actual included-only finite guardian')")
s=s.replace("'WAIT_EXISTING_CREDIT_WATCHER'","'WAIT_RESIDENT_UNCHANGED'")
a=s.index("    credit = state.get('credit_budget') or {}; billing =");b=s.index('    return [wall, mono, boot]',a)
s=s[:a]+"    validate_weekly_account(state, wall)\n"+s[b:]
a=s.index('def validate_control_config(config):');b=s.index('\n\ndef validate_arm_reference',a)
s=s[:a]+'''def validate_control_config(config):
    need(config.get('expected_thread') == THREAD and config.get('billing_mode') == 'included_only'
         and config.get('allow_prepaid_fallback') is False and config.get('initial_credit_budget') is None
         and config.get('automatic_credit_purchase') is False and config.get('api_key_billing') is False,
         'actual weekly included-only controller configuration')
    clock=config['initial_watch_clock']
    need(clock['boot_id']==BOOT_ID and clock['watcher_pid']==INITIAL['watcher'][0]
         and clock['watcher_start']==INITIAL['watcher'][1] and clock['deadline']==DEADLINE
         and finite(clock['boot_deadline']) and 0<clock['boot_deadline']<=BOOT_CAP
         and finite(clock['watcher_cutoff_lower']) and 0<clock['watcher_cutoff_lower']<=MONO_CAP,
         'actual weekly finite watcher clamp')
    return config
'''+s[b:]
a=s.index('def validate_armed(armed, observe):');b=s.index('    supervisor = observe(1311)',a)
s=s[:a]+'''def validate_armed_metadata(armed):
    need(armed.get('status')=='LIVE_WEEKLY_ONLY_SAME_ROOT_CONTROLS' and armed.get('thread_id')==THREAD
         and armed.get('native_release')is False and armed.get('guardian_packet_sha256')==PACKET_SHA,
         'actual weekly parent control receipt')
    caps=armed['caps']
    need(caps['boot_id']==BOOT_ID and (caps['deadline'],caps['monotonic_deadline'],caps['boot_deadline'])==(DEADLINE,MONO_CAP,BOOT_CAP),'actual weekly earliest finite caps')
    billing=armed['billing']
    need(billing['mode']=='included_only' and billing['credit_budget']is None and billing['automatic_credit_purchase']is False and billing['api_key_billing']is False and billing['account_wide_balance_guard']is False,'actual weekly receipt has no prepaid guard')
    row=armed['weekly_usage']
    need(row['windowDurationMins']==10080 and row['resetsAt']==RESET and finite(row['usedPercent']) and 0<=row['usedPercent']<100,'actual receipt same unexhausted weekly allowance')
    need(armed['monitor_arm_sha256']==MONITOR_ARM_SHA and armed['phone_packet_sha256']==PHONE_PACKET_SHA,'actual weekly auxiliary publications')
    return armed


def validate_armed(armed, observe):
    validate_armed_metadata(armed)
'''+s[b:]
# Remove active prepaid constants entirely; retained ledger is never read as authority.
s='\n'.join(line for line in s.splitlines()if not line.startswith(('RUN =','CEILING =','SPENT_FLOOR =','from decimal import Decimal')))+'\n'
policy=(W/'weekly_policy.py').read_text();pt=ast.parse(policy);pl=policy.splitlines(True)
parts=[''.join(pl[n.lineno-1:n.end_lineno])for n in pt.body if isinstance(n,(ast.ClassDef,ast.FunctionDef))and n.name in ['WeeklyWindowChanged','weekly_row']]
extra="\nRESET=1793774133\nWEEKLY_IDENTITY=dict(limit_id='codex',window_duration_mins=10080,resets_at=RESET)\nMONITOR_ARM_SHA="+repr(arm['monitor_arm_sha256'])+"\nPHONE_PACKET_SHA="+repr(arm['phone_packet_sha256'])+'\n\n'+'\n\n'.join(parts)+'''


def validate_weekly_account(state,wall):
    # Reuse exact controller weekly_row; no account RPC or private account file.
    # state.credit_budget is retained historical data; only settings.billing is live.
    billing=(state.get('settings')or{}).get('billing')or{}
    need(billing.get('mode')=='included_only' and billing.get('credit_budget')is None
         and billing.get('automatic_credit_purchase')is False and billing.get('api_key_billing')is False
         and billing.get('account_wide_balance_guard')is False,'current included-only worker billing')
    row=weekly_row(state.get('last_rate_limits'))
    need(state.get('weekly_usage')==row and row['usedPercent']<100 and wall<RESET and not state.get('weekly_usage_error'),'current exact unexhausted weekly observation')
    need(state.get('weekly_usage_thread_id')==THREAD and state.get('weekly_usage_worker_pid')==INITIAL['worker'][0]
         and state.get('weekly_usage_worker_start')==INITIAL['worker'][1],'weekly account observation belongs to current worker/Root')
    age=wall-datetime.fromisoformat(state['weekly_usage_observation_at'].replace('Z','+00:00')).timestamp()
    need(0<=age<120,'weekly account observation unavailable or stale')
    return row


def validate_lease_rows(rows,subjects):
    for pid,device,inode in subjects:
        need(any(len(fields)>=8 and fields[1:4]==['FLOCK','ADVISORY','WRITE'] and fields[4]==str(pid)
                 and fields[5]==format(os.major(device),'02x')+':'+format(os.minor(device),'02x')+':'+str(inode)
                 and fields[6:8]==['0','EOF'] for fields in (line.split()for line in rows)),
             'actual dedicated auxiliary lease held by measured actor '+str(pid))
    return True


def validate_auxiliary_leases():
    paths=[(EXPECTED_ACTORS['guardian'][0],CONTROL/'armed-controller/bridge.lock'),
           (EXPECTED_ACTORS['monitor'][0],CONTROL/'twenty-minute-steering/supervisor.lock'),
           (EXPECTED_ACTORS['phone'][0],CAMPAIGN/'phone-control/watch.lock')]
    subjects=[]
    for pid,path in paths:
        st=path.stat();subjects.append((pid,st.st_dev,st.st_ino))
    return validate_lease_rows(Path('/proc/locks').read_text().splitlines(),subjects)

'''
s=s.replace('def guard():',extra+'def guard():')
s=s.replace("    return validate(json.loads(window_raw)","    validate_auxiliary_leases()\n    return validate(json.loads(window_raw)")
ast.parse(s);(D/'guardian_guard.py').write_text(s)
print('GUARD',ref(D/'guardian_guard.py'))
