# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import sys,os,json,hashlib,traceback
OUTPUT='/home/holden/mckernel/docs/verification/evidence/p12-daemon-bound-20261023-1/coherent-successor/none-attach-smoke-1/debugger-state-export-1/shim-reconciliation-1/TARGET-STATE.json'
CANDIDATE='"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\nPRIVATE CANDIDATE ONLY: function definition; does nothing unless explicitly called.\nFor exact reviewed in-process recovery on Python3.8 only. No owner methods,\nownership flags, signals, ACK, filesystem writes or historical exit-code repair.\nRoot must independently review/bind the live intervention and current identity.\n"""\ndef install_missing_waitstatus_converter(os_module, version_info):\n    if tuple(version_info[:2]) != (3, 8):\n        raise RuntimeError("expected affected Python3.8")\n    if getattr(os_module, "__name__", None) != "os":\n        raise RuntimeError("expected live os module")\n    if hasattr(os_module, "waitstatus_to_exitcode"):\n        raise RuntimeError("converter already exists; do not replace")\n    # Capture only the existing POSIX status decoders; no owner object is held.\n    exited = os_module.WIFEXITED\n    exit_status = os_module.WEXITSTATUS\n    signaled = os_module.WIFSIGNALED\n    term_signal = os_module.WTERMSIG\n    def waitstatus_to_exitcode(status):\n        if exited(status):\n            return exit_status(status)\n        if signaled(status):\n            return -term_signal(status)\n        raise ValueError("wait status does not describe an exited or signaled process")\n    os_module.waitstatus_to_exitcode = waitstatus_to_exitcode\n    return {"compatibility_converter_installed": True,\n            "owner_flags_changed": 0, "owner_methods_invoked": 0,\n            "historical_statuses_reconstructed": False}\n'
installed=False
try:
 assert os.getpid()==3502879
 parts=open('/proc/self/stat').read().rpartition(') ')[2].split();assert int(parts[19])==52840595
 assert len(os.listdir('/proc/self/task'))==1
 frames=[]
 for f in sys._current_frames().values():
  for _ in range(128):
   if f is None:break
   if f.f_code.co_name=='execute_owner' and f.f_globals.get('__file__')=='/home/holden/mckernel/docs/verification/evidence/p12-daemon-bound-20261023-1/coherent-successor/source/native_diagnostic_container_owner.py':frames.append(f)
   f=f.f_back
 assert len(frames)==1
 frame=frames[0];owner=frame.f_locals['owner'];v=vars(owner)
 assert v['nonce']=='7247e16d234147afa148cd0ef24206d4' and v['owner_sha']=='a15680bb1a50d05bc8ee167ca20b0c1d3e34b8dc5fc1d1bdd593f4dc4f31eefe'
 assert v['create_issued'] is False and v['container'] is None and v['absent'] is False
 assert frame.f_locals.get('recoveries',0)>=24
 assert type(v['lock']) is int
 lock=os.fstat(v['lock']);assert (lock.st_dev,lock.st_ino)==(27,4)
 assert not vars(vars(v['backend'])['children'])['pending']
 cause=v['failure'].__cause__;assert isinstance(cause,AttributeError) and str(cause)=="module 'os' has no attribute 'waitstatus_to_exitcode'"
 keys=('create_issued','create_completed','container','sequence','absent','may_exist','cleaning','command_deadline','pending_bytes','retirement_sequence','owner_queued','signal_number','lock')
 before={k:v.get(k) for k in keys};error=v['failure'];queue=v['pending_evidence'];assert len(queue)<=4096 and v['pending_bytes']<=8*2**20
 signature=[(str(p),len(b),hashlib.sha256(b).hexdigest()) for p,b in queue]
 scope={'__builtins__':__builtins__}
 exec(compile(CANDIDATE,'<reviewed-waitstatus-compatibility>','exec'),scope)
 result=scope['install_missing_waitstatus_converter'](os,sys.version_info);installed=True
 assert result=={'compatibility_converter_installed':True,'owner_flags_changed':0,'owner_methods_invoked':0,'historical_statuses_reconstructed':False}
 assert os.waitstatus_to_exitcode(0)==0 and os.waitstatus_to_exitcode(37<<8)==37 and os.waitstatus_to_exitcode(15)==-15
 after={k:v.get(k) for k in keys};assert before==after and v['failure'] is error and v['pending_evidence'] is queue
 assert signature==[(str(p),len(b),hashlib.sha256(b).hexdigest()) for p,b in queue]
 state={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'WAITSTATUS_COMPATIBILITY_INSTALLED_ONLY','pid':os.getpid(),'start':int(parts[19]),'nonce':v['nonce'],'candidate_sha256':'bbe91fe030b93f7c0d88b7d2bd8e53aa5c6bb2e7212510af6b92cf48df812cd7','before':before,'after':after,'original_failure_preserved':True,'pending_evidence_preserved':True,'converter_installed':True,'owner_flags_changed':0,'owner_methods_invoked':0,'historical_statuses_reconstructed':False,'normal_cleanup_not_invoked_by_intervention':True,'physical_clearance':False}
except BaseException:
 state={'status':'COMPATIBILITY_INTERVENTION_ERROR','converter_installed':installed,'owner_flags_changed':0,'owner_methods_invoked':0,'traceback':traceback.format_exc(),'physical_clearance':False}
encoded=(json.dumps(state,sort_keys=True)+'\n').encode();assert len(encoded)<=65536
fd=os.open(OUTPUT,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
try:
 with os.fdopen(fd,'wb',closefd=False) as f:f.write(encoded);f.flush();os.fsync(f.fileno())
finally:os.close(fd)
