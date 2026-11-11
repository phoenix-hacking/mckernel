"""Five changed lazy-pidfd dispatch checks; every process/syscall effect controlled."""
import ctypes
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import sys
from types import SimpleNamespace
from unittest.mock import patch
SOURCE=Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110/native-controller-normal-transition-proposal-publicabi-max-1/current-468d-generation-1/pidfd-compatibility-repair-1/canonical-wrapper-reuse-1/candidate/scripts/os_goal_guard_protocol.py')
SOURCE_SHA='9bc35f56234b30e892828b6f75b4f909896b4125f4d4397e3a02fa810f602d09'
SCRIPTS=Path('/home/holden/mckernel/scripts')
WATCHER=SCRIPTS/'watch_os_goal.py'
WATCHER_SHA='9a105b4f37f61bed7ffbffd848ed0f02d2e792e4797a38609761e98480e7a1bb'
class Syscall:
    def __init__(self,replies):self.replies=list(replies);self.records=[];self.restype=None
    def __call__(self,number,*args):
        if not self.replies:raise AssertionError("controlled syscall script exhausted")
        expected,result,error=self.replies.pop(0)
        if number.value!=expected:raise AssertionError("unexpected syscall number")
        self.records.append(dict(number=number.value,number_type=type(number).__name__,argument_types=[type(v).__name__ for v in args],arguments=[v.value for v in args],restype=self.restype.__name__,errno_before=ctypes.get_errno()))
        ctypes.set_errno(error)
        return result
class Effects:
    def __init__(self,replies,identities,close_error=None):
        self.backend=Syscall(replies);self.identities=list(identities);self.close_error=close_error
        self.loads=[];self.identify=[];self.closes=[];self.numeric_signals=[]
        host=os.uname();self.uname=SimpleNamespace(sysname=host.sysname,machine=host.machine)
    def loader(self,name,use_errno=False):self.loads.append(dict(name=name,use_errno=use_errno));return SimpleNamespace(syscall=self.backend)
    def identity(self,pid):
        self.identify.append(pid)
        if not self.identities:raise AssertionError("controlled identity script exhausted")
        return self.identities.pop(0)
    def close(self,fd):
        self.closes.append(fd)
        if self.close_error is not None:raise OSError(self.close_error,"controlled close failure")
    def forbidden_numeric(self,*args):self.numeric_signals.append(list(args));raise AssertionError("numeric signal forbidden")
def exercise(module,watcher,name,replies,identities,close_error=None):
    e=Effects(replies,identities,close_error)
    fakeos=SimpleNamespace(name=os.name,uname=lambda:e.uname,strerror=os.strerror,close=e.close,kill=e.forbidden_numeric,killpg=e.forbidden_numeric)
    fakesignal=SimpleNamespace()
    fakectypes=SimpleNamespace(CDLL=e.loader,c_long=ctypes.c_long,c_int=ctypes.c_int,c_uint=ctypes.c_uint,c_void_p=ctypes.c_void_p,sizeof=ctypes.sizeof,set_errno=ctypes.set_errno,get_errno=ctypes.get_errno)
    result=dict(name=name,returned_none=False,exception=None,errno=None,message=None)
    # The genuine locally imported wrappers retain watcher globals. Replace only
    # their lowest effects and the protocol's point-read/finally-close endpoints.
    with patch.object(watcher,'os',fakeos),patch.object(watcher,'signal',fakesignal),patch.object(watcher,'ctypes',fakectypes),patch.object(module,'os',fakeos),patch.object(module,'process_start',e.identity):
        try:result['returned_none']=module.signal_exact(20000001,'111',15) is None
        except Exception as error:
            result.update(exception=type(error).__name__,errno=getattr(error,'errno',None),message=None if isinstance(error,OSError) else str(error))
    result.update(syscalls=e.backend.records,loader_calls=e.loads,identity_reads=e.identify,close_calls=e.closes,builtin_open_calls=[],builtin_send_calls=[],numeric_signal_calls=e.numeric_signals,syscall_replies_remaining=len(e.backend.replies),identity_replies_remaining=len(e.identities))
    return result

def main():
    raw=SOURCE.read_bytes();assert hashlib.sha256(raw).hexdigest()==SOURCE_SHA
    assert hashlib.sha256(WATCHER.read_bytes()).hexdigest()==WATCHER_SHA
    # This search path belongs only to the isolated fixture. Production uses its
    # existing scripts context and has no path edit or private watcher package.
    sys.path.insert(0,str(SCRIPTS))
    watcher=importlib.import_module('watch_os_goal')
    assert Path(watcher.__file__).resolve()==WATCHER
    assert watcher.pidfd_open.__globals__ is watcher.__dict__ and watcher.pidfd_send_signal.__globals__ is watcher.__dict__
    spec=importlib.util.spec_from_file_location('actual_private_guard_protocol',str(SOURCE));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    actual_runtime=dict(version=list(sys.version_info[:3]),executable_real=str(Path(sys.executable).resolve()),pidfd_open_builtin_available=callable(getattr(os,'pidfd_open',None)),pidfd_send_builtin_available=callable(getattr(signal,'pidfd_send_signal',None)),OS_name=os.name,sysname=os.uname().sysname,machine=os.uname().machine,pointer_bytes=ctypes.sizeof(ctypes.c_void_p))
    tests=[exercise(module,watcher,'missing_builtins_real_wrapper_syscall_ABI',[(434,777,0),(424,0,0)],['111']),exercise(module,watcher,'birth_mismatch_no_send',[(434,777,0)],['222']),exercise(module,watcher,'open_errno_no_handle_or_send',[(434,-1,38)],[]),exercise(module,watcher,'send_errno_still_closes_once',[(434,777,0),(424,-1,3)],['111']),exercise(module,watcher,'close_failure_observable_no_retry',[(434,777,0),(424,0,0)],['111'],close_error=5)]
    print(json.dumps(dict(scope='ACTUAL_ANACONDA_GUARD_LAZY_CANONICAL_PIDFD_CONTROLLED_LOWER_ONLY',actual_runtime=actual_runtime,canonical_watcher=dict(path=str(WATCHER),sha256=WATCHER_SHA),real_process_signal_or_controller_service_action=False,cases=tests),sort_keys=True,separators=(',',':')))
if __name__=='__main__':main()
