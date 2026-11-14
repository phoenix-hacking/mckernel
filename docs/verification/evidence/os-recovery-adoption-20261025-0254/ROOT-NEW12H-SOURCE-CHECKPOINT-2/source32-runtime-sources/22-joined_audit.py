"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure durable join/procfs witness validation. No process access or runtime on import.
"""
import hashlib,json

def need(value,message):
 if not value:raise ValueError(message)
def pairs(rows):
 result={}
 for key,value in rows:need(key not in result,'duplicate audit key');result[key]=value
 return result
def identity(raw,pid):
 need(isinstance(raw,str) and raw.startswith(str(pid)+' ('),'task stat PID differs')
 pieces=raw.rsplit(')',1);need(len(pieces)==2,'task comm missing');fields=pieces[1].split()
 need(len(fields)>=20 and len(fields[0])==1 and fields[0] in 'RSDZTtXxKWPI' and fields[19].isdecimal() and int(fields[19])>0,'task birth/state missing')
 return int(fields[19])
def snapshot(value,pid,known,absent):
 need(value.get('valid') is True and value.get('event')=='snapshot','valid complete snapshot required')
 rows=value.get('rows');need(isinstance(rows,list) and 1<=len(rows)<=64 and type(value.get('literal_threads')) is int and value['literal_threads']==len(rows),'literal count differs')
 seen=set();main_birth=None
 for row in rows:
  tid=row.get('tid');slot=row.get('slot');read=row.get('stat_read')
  need(type(tid) is int and tid>0 and tid not in seen and type(read) is int and read in (0,1),'distinct complete task row required');seen.add(tid)
  if tid==pid:
   need(slot==-1 and read==1,'main task not fully observed');main_birth=identity(row.get('raw_stat'),tid);need(row.get('birth')==main_birth,'main birth differs')
  else:
   need(type(slot) is int and slot in known and known[slot]['tid']==tid and slot not in absent and known[slot]['joined'] is True,'unknown/unjoined/reappeared task')
   if read:need(identity(row.get('raw_stat'),tid)==row.get('birth')==known[slot]['birth'],'reused worker TID')
   else:need(row.get('raw_stat')=='' and row.get('birth')==0,'typed exact worker ENOENT required')
 need(pid in seen,'main not enumerated');return main_birth
def validate(raw,pid,birth=None):
 need(type(pid) is int and pid>0 and len(raw)<=1<<20 and raw.endswith(b'\n'),'bounded complete audit required')
 rows=[json.loads(line,object_pairs_hook=pairs) for line in raw.splitlines()];need(rows,'empty audit')
 slots={};started_tids=set();known={};absent=set();phase='workers';initial=None;final=None
 for sequence,row in enumerate(rows):
  event=row.get('event')
  if event in ['thread_start','create_return','join_return']:
   need(phase=='workers','worker activity after terminal observation');slot=row.get('slot');need(type(slot) is int and 0<=slot<64,'bounded worker slot')
   state=slots.setdefault(slot,{})
   need(event not in state,'duplicate worker event');state[event]=(sequence,row)
   need(type(row.get('result')) is int and row['result']>=0,'typed actual pthread/proc result required')
   if event=='thread_start':
    tid=row.get('tid');need(row.get('result')==1 and type(tid) is int and tid>0 and tid!=pid and tid not in started_tids,'unknown/reused worker birth')
    started_tids.add(tid);need(identity(row.get('initial_raw_stat'),tid)==row.get('birth'),'initial worker identity differs')
  elif event=='snapshot':
   if row.get('phase')=='initial':
    need(phase=='workers','duplicate initial snapshot');phase='waiting'
    need(set(slots)==set(range(len(slots))),'incomplete worker inventory')
    for slot,state in slots.items():
     need('create_return' in state,'missing actual create return');create=state['create_return'][1]
     if create.get('result')!=0:need(set(state)=={'create_return'},'failed create has task');continue
     need(set(state)=={'thread_start','create_return','join_return'},'missing positive real join')
     start_sequence,start=state['thread_start'];join_sequence,joined=state['join_return']
     if state['create_return'][0]<start_sequence:need(create.get('tid')==0 and create.get('birth')==0 and create.get('initial_raw_stat')=='','pre-start create witness differs')
     else:need(all(create.get(key)==start.get(key) for key in ['tid','birth','initial_raw_stat']),'create/start identity differs')
     need(join_sequence>start_sequence and join_sequence>state['create_return'][0] and joined.get('result')==0 and joined.get('tid')==start['tid'] and joined.get('birth')==start['birth'] and joined.get('initial_raw_stat')==start['initial_raw_stat'],'actual target join0 witness differs')
     known[slot]=dict(tid=start['tid'],birth=start['birth'],joined=True,initial_raw_stat=start['initial_raw_stat'])
    initial=snapshot(row,pid,known,absent)
    if birth is not None:need(type(birth) is int and initial==birth,'captured main birth differs')
   else:
    need(row.get('phase')=='final' and phase=='waiting' and absent==set(known),'final before each exact joined directory ENOENT')
    final=snapshot(row,pid,known,absent);need(final==initial and row['literal_threads']==1 and row['rows'][0]['tid']==pid,'final literal main singleton required');phase='final'
  elif event in ['joined_directory_present','joined_directory_ENOENT']:
   need(phase=='waiting','wait outside terminal observer');slot=row.get('slot');need(slot in known and slot not in absent and row.get('tid')==known[slot]['tid'],'wait on unknown/unjoined/absent task')
   if event=='joined_directory_ENOENT':
    need(row.get('result')==2 and row.get('birth')==known[slot]['birth'] and row.get('initial_raw_stat')==known[slot]['initial_raw_stat'],'typed exact joined directory ENOENT required');absent.add(slot)
   else:
    read=row.get('stat_read');need(type(read) is int and read in (0,1),'failed task observation')
    if read:need(identity(row.get('raw_stat'),row['tid'])==row.get('birth')==known[slot]['birth'],'joined worker birth changed')
    else:need(row.get('raw_stat')=='' and row.get('birth')==0,'wrong stat ENOENT')
  elif event=='FINAL_SINGLETON':need(phase=='final' and sequence==len(rows)-1 and type(row.get('threads')) is int and row['threads']==1,'terminal singleton missing');phase='done'
  else:need(False,'observer refusal or unknown event: '+str(event))
 need(phase=='done' and final is not None,'incomplete join/absence audit')
 return dict(status='PASS_KNOWN_REAL_JOINS_CURRENT_ABSENCE_AND_LITERAL_SINGLETON',worker_count=len(known),audit_sha256=hashlib.sha256(raw).hexdigest(),historical_1fff_extra_task_identity=None)
