"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure bounded interpretation of an already retained reader result; no IO or runtime operations.
These are source-shaped serial facts only, not independent proof of app/ownership state.
"""
import base64,hashlib,re
PHASES={'setup-spool','round-evidence','callback-discover','callback-launch','callback-load','callback-postflight','callback-gate','callback-report','failure-trace-snapshot','failure-trace-save'}
def interpret(record):
 prefix=record['prefix'];encoded=prefix['base64']
 if not isinstance(encoded,str) or len(encoded)>11184812:raise ValueError('bounded retained prefix base64')
 raw=base64.b64decode(encoded,validate=True)
 if len(raw)>8388608 or len(raw)!=prefix['bytes'] or hashlib.sha256(raw).hexdigest()!=prefix['sha256']:raise ValueError('exact retained prefix bytes')
 end=raw.rfind(b'\n')+1;lines=raw[:end].splitlines()
 if len(lines)>262144:raise ValueError('bounded retained line count')
 phases=[];failures=[];trace_headers=[];trace_errors=[];aborts=0;errors=[]
 for index,line in enumerate(lines,1):
  if line==b'ND_PAIR_LONG_ABORT':aborts+=1
  if not line.startswith(b'P12_LONG_'):continue
  if len(line)>511:errors.append({'line':index,'error':'overlong diagnostic record'});continue
  text=line.decode('ascii')
  match=re.fullmatch(r'P12_LONG_PHASE round=(\d+) stage=([a-z-]+)',text)
  if match:
   round_id=int(match[1]);stage=match[2]
   if round_id<2048 and stage in PHASES:phases.append(dict(line=index,round=round_id,stage=stage))
   else:errors.append(dict(line=index,error='unknown phase or round'))
   continue
  match=re.fullmatch(r'P12_LONG_FAILURE round=(\d+) stage=([a-z-]+) pair_stage=([A-Za-z0-9_]+) result=(-?\d+) ownership_complete=([01]) rounds=(\d+) launches=(\d+) trace_bytes=(\d+)',text)
  if match:
   failures.append(dict(line=index,round=int(match[1]),stage=match[2],pair_stage=match[3],result=int(match[4]),ownership_complete_reported=int(match[5]),rounds_reported=int(match[6]),launches_reported=int(match[7]),trace_bytes_reported=int(match[8])));continue
  match=re.fullmatch(r'P12_LONG_FAILURE_TRACE_(BEGIN|END) bytes=(\d+)(?: saved=([01]))?',text)
  if match:
   trace_headers.append(dict(line=index,kind=match[1],bytes_declared=int(match[2]),saved_reported=None if match[3] is None else int(match[3])));continue
  match=re.fullmatch(r'P12_LONG_FAILURE_TRACE_ERROR stage=(snapshot|save)',text)
  if match:trace_errors.append(dict(line=index,stage=match[1]));continue
  errors.append(dict(line=index,error='unrecognized diagnostic record'))
 return dict(last_phase=phases[-1] if phases else None,phase_records=phases,failure_records=failures,abort_records=aborts,trace_headers=trace_headers,trace_errors=trace_errors,diagnostic_parse_errors=errors,partial_tail_excluded_bytes=len(raw)-end,launch_credit=0,work_hour_credit=0,ownership_clearance=False,application_acceptance=False,native_acceptance=False,qualification='Last phase identifies an entered boundary only; absence of a next line does not prove blocking, liveness, app start, safe ownership or cause. Failure fields and trace headers are reported serial values. Raw retained prefix preserves trace bytes; no trace/retirement proof is inferred. Existing strict terminal consumer remains authoritative.')
