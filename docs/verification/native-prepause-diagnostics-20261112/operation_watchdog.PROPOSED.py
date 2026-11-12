"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Future one-shot parent watchdog. No process or root operation starts at import.
"""
import fcntl
import hashlib
import json
import math
import sys
import os
import select
import resource
import signal
import time
import graph_observations as obs
import inplace_custody as source
import custody_protocol_v2 as wire
import root_bootstrap
from ownership_latch import CustodyLatch,ChildRecord
import deferred_fork
import pidfd_compat
import runtime_binding


def fail(message):raise ValueError(message)


class LeaseStartUnknown(RuntimeError):
    def __init__(self,fd):
        super().__init__('operation lease acquisition uncertain; retain descriptor')
        self.fd=fd


def create_lease(root_fd,nonce):
    """Exclusive operation lease; caller retains this FD across child failure."""
    source.root_private(root_fd);wire.sha256_hex(nonce)
    name='GRAPH-LEASE-'+nonce
    fd=os.open(name,os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=root_fd)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        source.write_all(fd,obs.canonical({'nonce':nonce,'status':'OWNED_LEASE'})+b'\n')
        os.fsync(fd);os.fsync(root_fd)
        return fd
    except BaseException as error:
        # Caller receives and retains the uncertain descriptor and never unlinks it.
        raise LeaseStartUnknown(fd) from error


def fork_supervisor(executable,argv,environment,root_fd,lease_fd,record,guard):
    """Start a root child inheriting exactly the watchdog-owned operation FDs.

    The parent retains both descriptions. Caller first verifies immutable entry,
    interpreter and exact source bytes and separately obtains operation release.
    """
    if os.geteuid()!=0 or type(argv) is not list or not argv or argv[0]!=executable:
        fail('root and exact supervisor argv required')
    if type(environment) is not dict or any(type(k) is not str or type(v) is not str for k,v in environment.items()):
        fail('exact supervisor environment')
    if root_fd==lease_fd or min(root_fd,lease_fd)<3:fail('custody descriptors')
    source.root_private(root_fd)
    if type(record) is not ChildRecord or type(guard) is not deferred_fork.DeferredFork or not guard.entered:
        fail('guarded pre-registered supervisor custody required')
    record.add(root_fd,lease_fd)
    def child_exec():
        for fd in (root_fd,lease_fd):os.set_inheritable(fd,True)
        keep=sorted((root_fd,lease_fd))
        upper=resource.getrlimit(resource.RLIMIT_NOFILE)[0]
        if upper==resource.RLIM_INFINITY or upper>1048576:upper=1048576
        os.closerange(3,keep[0]);os.closerange(keep[0]+1,keep[1]);os.closerange(keep[1]+1,int(upper))
        env=dict(environment);env['MCKERNEL_OPERATION_ROOT_FD']=str(root_fd);env['MCKERNEL_OPERATION_LEASE_FD']=str(lease_fd)
        os.execve(executable,argv,env)
    pid,pidfd,birth=guard.fork_and_pin(record,child_exec)
    return pid,pidfd,('BOUND',None)


class LaunchUnknown(RuntimeError):
    def __init__(self,latch):
        super().__init__('supervisor launch outcome uncertain; retain registered custody')
        self.latch=latch


def launch_reviewed(root_fd,nonce,executable,executable_sha,bootstrap_path,bootstrap_sha,
                    loader_manifest,loader_sha,entry_path,environment,deadline_boot,grace_seconds,runtime_path,runtime_sha,native_request=None):
    """Future root-owner entry; reserve custody before a possible fork."""
    runtime_binding.verify_current(runtime_path,runtime_sha)
    if native_request is not None:
        import native_resource_admission as native
        if type(native_request) is not native.VerifiedNativeRequest:fail('typed named watchdog request')
        native_request.verify()
        cfg=native_request.cfg
        if native.file_identity(root_fd)!=cfg['operation_root']:fail('named operation root changed')
        if (cfg['watchdog_pid']!=os.getpid() or cfg['watchdog_birth']!=obs.process(os.getpid())[0] or
            cfg['nonce']!=nonce or deadline_boot!=cfg['caps']['boot']):fail('actual named watchdog/request join')
        lf,lr=root_bootstrap.pinned_root_file(loader_manifest,loader_sha)
        try:
            import json
            loader=json.loads(lr,object_pairs_hook=source.unique)
            if (loader.get('kind')!='mckernel-native-signal-loader-v1' or
                loader.get('operation_config_path')!=native_request.path or
                loader.get('operation_config_sha')!=native_request.sha256):fail('named loader/request join')
        finally:os.close(lf)
    if executable!=runtime_path or executable_sha!=runtime_sha:fail('watchdog/supervisor runtime differs')
    latch=CustodyLatch('WATCHDOG_HELD');latch.retain(root_fd)
    record=None
    try:
        with deferred_fork.DeferredFork() as guard:
            record=latch.reserve_child('supervisor',root_fd)
            token=latch.begin('WATCHDOG_HELD')
            source.root_private(root_fd)
            exe_fd,_=root_bootstrap.pinned_root_file(executable,executable_sha,128*1024*1024);record.add(exe_fd)
            bs_fd,bs_bytes=root_bootstrap.pinned_root_file(bootstrap_path,bootstrap_sha);record.add(bs_fd)
            manifest_fd,_=root_bootstrap.pinned_root_file(loader_manifest,loader_sha);record.add(manifest_fd)
            lease_fd=create_lease(root_fd,nonce);record.add(lease_fd)
            argv=root_bootstrap.supervisor_argv(executable,bs_bytes,loader_manifest,loader_sha,entry_path)
            pid,pidfd,result=fork_supervisor(executable,argv,environment,root_fd,lease_fd,record,guard)
        if result[0]!='BOUND':raise RuntimeError('supervisor pidfd unavailable')
        birth=record.birth
        watchdog=Watchdog.__new__(Watchdog);record.add(watchdog)
        watchdog.__init__(root_fd,lease_fd,nonce,pid,pidfd,birth,deadline_boot,grace_seconds,native_request)
        watchdog.latch=latch;watchdog.child_record=record
        latch.commit(token,'SUPERVISOR_BOUND',watchdog)
        return watchdog
    except BaseException as error:
        if record is not None:
            if isinstance(error,LeaseStartUnknown):record.add(error.fd)
            record.unknown(error)
        else:latch.fail(error)
        raise LaunchUnknown(latch) from error


def publish_unknown(root_fd,nonce,reason):
    name='GRAPH-WATCHDOG-UNKNOWN-'+nonce+'.json'
    fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=root_fd)
    try:
        source.write_all(fd,obs.canonical({'status':'UNKNOWN_RETAINED','nonce':nonce,'reason':reason})+b'\n')
        os.fsync(fd);os.fsync(root_fd)
    finally:os.close(fd)


def capture_raw_exception(label, error, traceback_object=None):
    if traceback_object is None:
        traceback_object = BaseException.__dict__['__traceback__'].__get__(error, type(error))
    key = (label, id(error), id(traceback_object))
    if key not in RAW_SEEN:
        RAW_SEEN.add(key)
        RAW_FAILURES.append({'label': label, 'error': error, 'traceback': traceback_object})
    # Explicit exception chains are evidence too. Read builtin descriptors, not
    # a user-defined attribute/formatting hook; cycles remain raw and bounded.
    chain_seen = {id(error)}
    current = error
    for index in range(16):
        cause = BaseException.__dict__['__cause__'].__get__(current, type(current))
        context = BaseException.__dict__['__context__'].__get__(current, type(current))
        child = cause if cause is not None else context
        if child is None or id(child) in chain_seen:
            break
        chain_seen.add(id(child))
        tb = BaseException.__dict__['__traceback__'].__get__(child, type(child))
        chain_label = label + ':chain:' + str(index)
        chain_key = (chain_label, id(child), id(tb))
        if chain_key not in RAW_SEEN:
            RAW_SEEN.add(chain_key)
            RAW_FAILURES.append({'label': chain_label, 'error': child, 'traceback': tb})
        current = child

def capture_secondary_exceptions():
    global SECONDARY_CAPTURED
    while SECONDARY_CAPTURED < len(SECONDARY):
        index = SECONDARY_CAPTURED
        label, error = SECONDARY[index]
        SECONDARY_CAPTURED += 1
        capture_raw_exception('secondary:' + str(index) + ':' + label, error)

def diagnostic_secondary(label, error):
    # The original exception/TB is retained before any attempt to describe it.
    capture_raw_exception(label, error)
    SECONDARY.append((label, error))

def diagnostic_type(value):
    cls = type(value)
    return type.__getattribute__(cls, '__module__') + '.' + type.__getattribute__(cls, '__name__')

def diagnostic_value(value, depth=0):
    cls = type(value)
    if value is None or cls in (bool, int):
        return value
    if cls is float:
        return value if math.isfinite(value) else {'nonfinite_float': True}
    if cls is str:
        return {'text': value[:32768], 'truncated': len(value) > 32768,
                'sha256': hashlib.sha256(value.encode('utf-8', 'backslashreplace')).hexdigest()}
    if cls is bytes:
        return {'bytes_hex': value[:16384].hex(), 'truncated': len(value) > 16384,
                'sha256': hashlib.sha256(value).hexdigest()}
    if depth < 4 and cls in (tuple, list):
        return {'items': [diagnostic_value(item, depth + 1) for item in value[:64]],
                'truncated': len(value) > 64}
    return {'opaque_type': diagnostic_type(value), 'raw_object_retained': True}

def render_raw_failure(record):
    error = record['error']
    raw_args = BaseException.__dict__['args'].__get__(error, type(error))
    value = {'label': record['label'], 'type': diagnostic_type(error),
             'raw_args': diagnostic_value(raw_args), 'errno': None,
             'traceback_frames': [], 'traceback_truncated': False,
             'raw_exception_and_traceback_retained': True}
    if isinstance(error, OSError):
        value['errno'] = diagnostic_value(OSError.__dict__['errno'].__get__(error, type(error)))
    tb = record['traceback']
    while tb is not None and len(value['traceback_frames']) < 128:
        code = tb.tb_frame.f_code
        value['traceback_frames'].append({'file': code.co_filename,
                                           'line': tb.tb_lineno, 'function': code.co_name})
        tb = tb.tb_next
    value['traceback_truncated'] = tb is not None
    # A formatter/report failure must not recursively invoke the same failing
    # hook. Its exact primitive BaseException args and real TB remain evidence.
    if 'diagnostic-' in record['label']:
        value['message'] = json.dumps(value['raw_args'], sort_keys=True)
        value['message_encoding'] = 'exact_bounded_primitive_baseexception_args'
    else:
        try:
            message = str(error)
        except BaseException as formatting_error:
            diagnostic_secondary('diagnostic-message-format:' + record['label'], formatting_error)
            value['message'] = json.dumps(value['raw_args'], sort_keys=True)
            value['message_encoding'] = 'formatter_failed_exact_bounded_args_and_raw_object_retained'
        else:
            value['message'] = message[:65536]
            value['message_truncated'] = len(message) > 65536
            value['message_sha256'] = hashlib.sha256(message.encode('utf-8', 'backslashreplace')).hexdigest()
            value['message_encoding'] = 'actual_exception_str'
    return value

def diagnostic_payload(phase):
    capture_secondary_exceptions()
    records = []
    index = 0
    # Rendering can add a formatting failure; include that real exception too.
    while index < len(RAW_FAILURES):
        records.append(render_raw_failure(RAW_FAILURES[index]))
        index += 1
        capture_secondary_exceptions()
    return {'schema': 'native-root-caller-failure-diagnostics-v1', 'phase': phase,
            'pid': os.getpid(), 'exceptions': records,
            'native_authority_or_release': False, 'raw_objects_retained': True}

def diagnostic_write(fd, raw):
    offset = 0
    while offset < len(raw):
        wrote = os.write(fd, raw[offset:])
        need(wrote > 0, 'short caller diagnostic capture write')
        offset += wrote

def need(ok,message):
    if not ok:raise ValueError(message)

def own(fd,label):
    row={'fd':fd,'historical_fd':fd,'label':label,'state':'HELD'};OWNED.append(row);return row

def close_once(row):
    if row['state']!='HELD':return
    fd=row.pop('fd');row['state']='CLOSE_ATTEMPTED_UNKNOWN'
    try:os.close(fd)
    except BaseException as error:
        diagnostic_secondary('provider-close:'+row['label'],error);raise
    row['state']='CLOSED'

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()

# Reporting owns only its newly opened report FDs. The caller's root_fd is
# borrowed for this finite write; it is never closed or transferred here.
OWNED=[]
SECONDARY=[]
RAW_FAILURES=[]
RAW_SEEN=set()
SECONDARY_CAPTURED=0
NATIVE_REPORT_BOUNDARIES=[]
NATIVE_REPORT_SECONDARY=[]
DIAGNOSTIC_SEQUENCE=0
REPORT_LIMIT=512*1024


def _persist_native_context(root_fd,phase,payload):
    global DIAGNOSTIC_SEQUENCE
    record=None;stored=False
    try:
        source.root_private(root_fd)
        DIAGNOSTIC_SEQUENCE+=1
        nonce=payload['nonce']
        need(type(nonce) is str and len(nonce)==64 and all(x in '0123456789abcdef' for x in nonce),'native diagnostic nonce shape')
        name='NATIVE-CONTEXT-DIAGNOSTIC-'+nonce+'-'+str(os.getpid())+'-'+str(DIAGNOSTIC_SEQUENCE)+'.json'
        raw=canonical(payload)+b'\n';need(len(raw)<=REPORT_LIMIT,'bounded native diagnostic payload')
        fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=root_fd)
        record=own(fd,'native-context-diagnostic:'+name)
        diagnostic_write(fd,raw);os.fsync(fd);os.fsync(root_fd);stored=True
    except BaseException as reporting_error:
        diagnostic_secondary('diagnostic-private-native-context:'+phase,reporting_error)
    finally:
        if record is not None and record['state']=='HELD':
            try:close_once(record)
            except BaseException:stored=False
    return stored


def _native_report_notice(payload,stored):
    # Full exception args/messages and account/config contents stay private.
    # A successful normal wait emits no stream data.
    notice={'schema':'native-context-diagnostic-notice-v1','phase':payload['phase'],
      'nonce':payload['nonce'],'config_sha256':payload['config_sha256'],
      'pid':payload['pid'],'birth':payload.get('birth'),'private_record_complete':stored,
      'primary_type':payload.get('primary_type'),'native_authority_or_release':False,
      'primary_raw_exception_and_traceback_retained':True,'reporting_failure_is_secondary':True}
    raw=canonical(notice)+b'\n';need(len(raw)<=8192,'bounded native diagnostic notice')
    for fd,label in ((2,'stderr'),(1,'stdout')):
        try:diagnostic_write(fd,raw)
        except BaseException as reporting_error:
            diagnostic_secondary('diagnostic-native-context-'+label,reporting_error)
        else:return True
    return False


def report_native_context(root_fd,phase,nonce,config_sha,error=None,wait_data=None):
    """Finite DATA reporting; no wait, signal, resource or lifetime decision."""
    stored=False;boundary=None
    try:
        tb=None if error is None else BaseException.__dict__['__traceback__'].__get__(error,type(error))
        boundary={'phase':phase,'error':error,'traceback':tb,'wait_data':wait_data,
          'caller_root_fd_borrowed_not_owned':root_fd,'secondary':[]}
        NATIVE_REPORT_BOUNDARIES.append(boundary)
        if error is not None:capture_raw_exception('primary',error,tb)
        payload=diagnostic_payload(phase)
        payload.update({'source_component':'operation_watchdog','nonce':nonce,'config_sha256':config_sha,
          'utc_ns':time.time_ns(),'mono_ns':time.monotonic_ns(),'birth':None,
          'wait_data':wait_data,'primary_type':None if error is None else diagnostic_type(error),
          'reporting_only_no_native_or_resource_authority':True})
        try:payload['birth']=sys.modules['native_current_owner'].birth(os.getpid())
        except BaseException as reporting_error:
            diagnostic_secondary('diagnostic-native-context-birth',reporting_error)
            payload['birth_unproved']=True
        boundary['payload_context']=payload
        stored=_persist_native_context(root_fd,phase,payload)
        boundary['private_record_complete']=stored
        if error is not None or not stored:_native_report_notice(payload,stored)
    except BaseException as reporting_error:
        # Nothing in reporting may replace a primary or bypass its old hold.
        raw=(reporting_error,BaseException.__dict__['__traceback__'].__get__(reporting_error,type(reporting_error)))
        NATIVE_REPORT_SECONDARY.append(raw)
        if boundary is not None:boundary['secondary'].append(raw)
    return stored


def report_native_wait(watchdog,returned_pid,raw_status):
    try:
        exited=os.WIFEXITED(raw_status);signalled=os.WIFSIGNALED(raw_status)
        expected=sys.modules['native_resource_admission'].VerifiedNativeRequest
        data={'requested_pid':watchdog.pid,'expected_supervisor_birth':watchdog.birth,
          'returned_pid':returned_pid,'raw_wait_status':raw_status,
          'WIFEXITED':exited,'exit_status':os.WEXITSTATUS(raw_status) if exited else None,
          'WIFSIGNALED':signalled,'term_signal':os.WTERMSIG(raw_status) if signalled else None,
          'request_type':diagnostic_type(watchdog.native_request),
          'request_exact_current_type':type(watchdog.native_request) is expected,
          'one_existing_own_waitpid_return_only':True,'native_validation_or_success':False}
        return report_native_context(watchdog.root_fd,'OWN_SUPERVISOR_WAITPID_RETURNED',
          watchdog.nonce,watchdog.native_request.sha256,wait_data=data)
    except BaseException as reporting_error:
        NATIVE_REPORT_SECONDARY.append((reporting_error,BaseException.__dict__['__traceback__'].__get__(reporting_error,type(reporting_error))))
        return False


class Watchdog:
    """Retain the same open lease description while supervising exact child PID.

    Caller must hold approved root operation/admission and independently assess
    all descendants and native state. A signal or direct wait never proves cleanup.
    """
    def __init__(self,root_fd,lease_fd,nonce,pid,pidfd,birth,deadline_boot,grace_seconds,native_request=None):
        source.root_private(root_fd);wire.sha256_hex(nonce)
        if type(pid) is not int or pid<=0 or type(birth) is not str or not birth.isdigit():fail('child identity')
        if obs.process(pid)[0]!=birth:fail('child birth changed')
        if native_request is None:
            if type(deadline_boot) not in (int,float) or not wire.boot_now()<deadline_boot<=1571567.6959065471:fail('deadline')
        else:
            import native_resource_admission as native
            if type(native_request) is not native.VerifiedNativeRequest:fail('named watchdog type')
            native_request.verify()
            if not wire.boot_now()<deadline_boot==native_request.cfg['caps']['boot']:fail('named watchdog deadline')
        self.native_request=native_request
        if type(grace_seconds) not in (int,float) or not 0<grace_seconds<=30:fail('grace')
        self.root_fd,self.lease_fd,self.nonce=root_fd,lease_fd,nonce
        self.pid,self.pidfd,self.birth,self.deadline,self.grace=pid,pidfd,birth,deadline_boot,grace_seconds
        self.state='HELD';self.wait_status=None

    def _poll(self,until):
        poll=select.poll();poll.register(self.pidfd,select.POLLIN)
        while wire.boot_now()<until:
            if poll.poll(max(1,min(1000,int((until-wire.boot_now())*1000)))):return True
        return False

    def _signal(self,sig):
        if obs.process(self.pid)[0]!=self.birth:fail('signal identity ambiguous')
        pidfd_compat.send_signal(self.pidfd,sig)

    def supervise(self):
        if self.state!='HELD':fail('watchdog already used')
        try:
            if not self._poll(self.deadline):
                self.state='UNKNOWN_RETAINED';self.latch.fail('supervisor deadline');publish_unknown(self.root_fd,self.nonce,'supervisor deadline')
                self._signal(signal.SIGTERM)
                if not self._poll(wire.boot_now()+self.grace):
                    self._signal(signal.SIGKILL)
                    if not self._poll(wire.boot_now()+self.grace):fail('supervisor direct join unknown')
            # waitpid only for this own child; other process/cgroup custody is unknown.
            got,status=os.waitpid(self.pid,0)
            if self.native_request is not None:report_native_wait(self,got,status)
            if got!=self.pid:fail('direct wait identity')
            self.wait_status=status
            if self.native_request is not None:
                import native_resource_admission as native
                terminal=native.NativeParentRetirement.__new__(native.NativeParentRetirement)
                self.latch.retain(terminal)
                terminal.__init__(self)
                self.native_terminal=terminal;self.state='CURRENT_NATIVE_RESTORED_PENDING_OWN_FD_CLOSE'
                return {'status':'CURRENT_NAMED_NATIVE_RESTORED_DATA_ONLY','wait_status':status,
                        'nonce':self.nonce,'functional_pass':terminal.terminal['functional_pass'],
                        'application_acceptance':False,'actual_client_waits':terminal.command_count}
            self.state='UNKNOWN_RETAINED';self.latch.fail('direct wait only')
            return {'status':'DIRECT_WAIT_ONLY_UNKNOWN_RETAINED','wait_status':status,'nonce':self.nonce}
        except BaseException as error:
            self.state='UNKNOWN_RETAINED';self.latch.fail(error);raise

    def retire(self):
        if self.native_request is not None:
            import native_resource_admission as native
            if self.state!='CURRENT_NATIVE_RESTORED_PENDING_OWN_FD_CLOSE' or type(getattr(self,'native_terminal',None)) is not native.NativeParentRetirement:
                fail('positive current native/source/parent retirement required')
            # Recheck kernel/source/owner facts immediately before closing only
            # this new watchdog's own descriptors. No historical scope changes.
            check=native.NativeParentRetirement(self)
            handles=[self.lease_fd,self.pidfd]
            handles += [x for x in self.child_record.handles if type(x) is int and x>=3 and x!=self.root_fd]
            handles += list(getattr(self,'source_loader_holds',[]))
            handles.append(self.native_request.fd)
            errors=[];attempted=set()
            for fd in handles:
                if fd is None or fd in attempted:continue
                attempted.add(fd)
                try:os.close(fd)
                except BaseException as error:errors.append((fd,error))
            self.closed_handle_attempts=attempted;self.close_errors=errors
            if errors:
                self.state='OWN_CLOSURE_UNKNOWN';self.latch.fail('own descriptor close uncertain',errors)
                raise RuntimeError('current watchdog descriptor close uncertain')
            self.state='RETIRED_CURRENT_NATIVE_OPERATION_ONLY'
            return {'status':self.state,'nonce':self.nonce,'native_pool':'STATIC_HELD_UNCHANGED',
                    'historical_outcomes':'UNCHANGED','application_acceptance':False}
        raise RuntimeError('lease and flags remain held pending independent physical retirement')


if __name__=='__main__':raise RuntimeError('SOURCE ONLY: no root operation admission')
