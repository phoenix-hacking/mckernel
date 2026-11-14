# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import sys,os,json,hashlib,base64,traceback
OUTPUT='/home/holden/mckernel/docs/verification/evidence/p12-daemon-bound-20261023-1/coherent-successor/none-attach-smoke-1/debugger-state-export-1/debugger-ordinary-fixture/TARGET-STATE.json'
try:
 assert os.getpid()==3509156
 st=open('/proc/self/stat').read().rpartition(') ')[2].split();assert int(st[19])==52943557
 assert len(os.listdir('/proc/self/task'))==1
 frames=[]
 for f in sys._current_frames().values():
  for _ in range(128):
   if f is None:break
   if f.f_code.co_name=='execute_owner' and f.f_globals.get('__file__')=='/home/holden/mckernel/docs/verification/evidence/p12-daemon-bound-20261023-1/coherent-successor/source/native_diagnostic_container_owner.py':frames.append(f)
   f=f.f_back
 assert len(frames)==1
 f=frames[0];owner=f.f_locals['owner'];v=vars(owner)
 assert v['nonce']=='7247e16d234147afa148cd0ef24206d4' and v['owner_sha']=='a15680bb1a50d05bc8ee167ca20b0c1d3e34b8dc5fc1d1bdd593f4dc4f31eefe'
 assert type(v['lock']) is int
 lock=os.fstat(v['lock']);assert (lock.st_dev,lock.st_ino)==(66306,48765032)
 pending=v['pending_evidence'];assert type(pending) is list and len(pending)<=4096 and v['pending_bytes']<=8*2**20
 records=[];total=0
 for path,raw in pending:
  assert type(raw) is bytes;total+=len(raw);assert total<=8*2**20
  records.append({'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'base64':base64.b64encode(raw).decode('ascii')})
 failure=v['failure'];trace=''.join(traceback.format_exception(type(failure),failure,failure.__traceback__)) if failure is not None else None
 assert trace is None or len(trace)<=65536
 backend=vars(v['backend']);ledger=vars(backend['children'])
 clients=[]
 for child in ledger['pending']:
  cv=vars(child);row={}
  for key in ('pid','identity','initial_observation'):
   value=cv.get(key)
   if value is None or type(value) in (int,str,dict,list,tuple):row[key]=value
  clients.append(row)
 assert len(clients)<=512
 state={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'DIAGNOSTIC_STATE_EXPORTED_NO_OWNER_METHODS_OR_FLAG_CHANGES','pid':os.getpid(),'start':int(st[19]),'nonce':v['nonce'],'failure_type':type(failure).__name__,'failure_message':str(failure)[:65536],'failure_traceback':trace,'fields':{k:v.get(k) for k in ('create_issued','create_completed','container','sequence','absent','may_exist','cleaning','command_deadline','pending_bytes','retirement_sequence','owner_queued','signal_number')},'lock':{'fd':v['lock'],'device':lock.st_dev,'inode':lock.st_ino},'recovery':{k:f.f_locals.get(k) for k in ('delay','recoveries')},'pending_clients':clients,'reap_records':ledger['final_reap_records'],'ledger_errors':[str(x)[:4096] for x in ledger['errors']],'retained_pending_evidence':records,'retained_pending_bytes':total,'physical_clearance':False,'owner_methods_invoked':0,'owner_flags_changed':0}
 raw=(json.dumps(state,sort_keys=True)+'\n').encode();assert len(raw)<=16*2**20
except BaseException:
 raw=(json.dumps({'status':'DIAGNOSTIC_ERROR_NO_OWNER_FLAGS_CHANGED','traceback':traceback.format_exc()})+'\n').encode()
fd=os.open(OUTPUT,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
try:
 with os.fdopen(fd,'wb',closefd=False) as h:h.write(raw);h.flush();os.fsync(h.fileno())
finally:os.close(fd)
