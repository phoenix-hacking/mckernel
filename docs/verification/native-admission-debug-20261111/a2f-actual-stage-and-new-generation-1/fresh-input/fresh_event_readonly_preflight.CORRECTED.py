from pathlib import Path
import json,hashlib,datetime,time,types,sys
E=Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110/native-code-package-preparation-sdk-max-1/a2f-fixed30-normal-operation-proposal-1/correction-1/account-snapshot-correction-1/primary-guard-correction-1');src=E/'ROOT-ISSUE-AND-EXECUTE-ONCE.py';raw=src.read_bytes();assert hashlib.sha256(raw).hexdigest()=='9daec4d582c13e58ca2ac467e1a0566440f17497eaad621c07df6ef6987695c3';mod=types.ModuleType('_reviewed_readonly_snapshot');mod.__file__=str(src);exec(compile(raw,str(src),'exec'),mod.__dict__)
protocol=Path('/home/holden/mckernel/.git/os-autopilot/runs/20261110T060029Z-3fe88dab/protocol.jsonl');started=time.monotonic();seen=set();failed_at=datetime.datetime.fromisoformat(json.loads((E/'ROOT-FAILED-FRESHNESS-VETO.json').read_text())['at']).timestamp()
while time.monotonic()-started<60:
 s=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text());g=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/guardian.json').read_text());assert s.get('phase')=='running' and not s.get('stop_reason') and not s.get('credit_budget_error') and not g.get('user_stop')
 with protocol.open('rb') as f:
  f.seek(0,2);f.seek(max(0,f.tell()-4*1024*1024));lines=f.read().splitlines()
 selected=None
 for line in reversed(lines):
  try:row=json.loads(line)
  except (ValueError,UnicodeError):continue
  if row.get('event',{}).get('method')=='account/rateLimits/updated':selected=row;break
 if selected is not None:
  observed=datetime.datetime.fromisoformat(selected['at']).timestamp();age=time.time()-observed;key=selected['at']
  if observed>failed_at and 0<=age<10 and key not in seen:
   seen.add(key)
   try:
    state,usage,credit,accepted=mod.current_account_snapshot();age=time.time()-accepted
    assert accepted>failed_at and 0<=age<15
    print(json.dumps({'status':'GENUINELY_NEW_FRESH_COHERENT_INPUT','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'event_at':usage['at'],'age_seconds':age,'full_current_helper_accepted':True,'no_query_state_write_or_issuer':True}),flush=True);sys.exit(0)
   except Exception as exc:
    print(json.dumps({'status':'NEW_INPUT_HELPER_VETO_NO_ISSUER','error_type':type(exc).__name__,'no_query_state_write_or_issuer':True}),flush=True);sys.exit(76)
 time.sleep(1)
print(json.dumps({'status':'NO_NEW_QUALIFYING_NOTIFICATION_WITHIN_BOUNDED_READONLY_WAIT','no_query_state_write_or_issuer':True}),flush=True);sys.exit(75)
