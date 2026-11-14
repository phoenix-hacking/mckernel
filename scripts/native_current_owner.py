"""Current owning-Campaign account/control handoff; never a native RAM grant.

Imported by the existing worker and by its immutable root-operation package.
Only CurrentOwnerServer calls the already-owning Campaign's account methods.
No Campaign/RPC/CreditBudget object is constructed here. Import launches nothing.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import select
import socket
import stat
import struct
import time
import pidfd_compat
from decimal import Decimal

ROOT_THREAD = '01a18bc3-e072-7810-9426-75101b0856c0'
CREDIT_RUN = '7c6ef3604bfb4008a917bba8cfb6cfaa'
SCHEMA = 'mckernel-current-owning-controller-v1'
MAX_FRAME = 32768
MAX_AGE = 5.0
HANDOFF_SECONDS = 60.0
ACCOUNT_RESERVE_SECONDS = 45.0
HOLDS = ('service_hold','policy_hold','auth_hold','billing_hold','budget_hold',
         'permission_hold','source_hold','resource_hold','native_hold',
         'transport_uncertain','pending_request','credit_budget_error')
LOADED_SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def need(ok, message):
    if not ok: raise RuntimeError(message)


def birth(pid):
    raw = Path('/proc/%d/stat' % pid).read_bytes()
    need(len(raw)<=4096 and raw.startswith(('%d (' % pid).encode()),'controller process stat')
    tail=raw.rsplit(b')',1)[1].split()
    need(len(tail)>=20 and tail[0] not in (b'Z',b'X',b'x'),'controller process unavailable')
    return tail[19].decode()


def unique(pairs):
    value={}
    for k,v in pairs:
        need(k not in value,'duplicate control key');value[k]=v
    return value


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


class ChannelCleanupError(RuntimeError):
    def __init__(self, primary, secondary):
        super().__init__('current-owner channel cleanup incomplete')
        self.primary=primary;self.secondary=tuple(secondary)
        self.interrupt=interruption(primary)
        if self.interrupt is None:
            for row in self.secondary:
                error=row[-1] if isinstance(row,tuple) else row
                self.interrupt=interruption(error)
                if self.interrupt is not None:break


def interruption(error):
    if isinstance(error,(KeyboardInterrupt,SystemExit)):return error
    if isinstance(error,ChannelCleanupError):return error.interrupt
    return None


def remaining(deadline):
    need(type(deadline) in (int,float) and math.isfinite(deadline),'absolute control deadline')
    left=deadline-time.monotonic();need(left>0,'current control total deadline')
    return left


def send(sock,value,deadline):
    raw=json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    need(0<len(raw)<=MAX_FRAME,'control frame bound')
    frame=struct.pack('!I',len(raw))+raw;offset=0
    while offset<len(frame):
        sock.settimeout(remaining(deadline))
        n=sock.send(frame[offset:]);need(n>0,'control channel EOF');offset+=n
    remaining(deadline)


def receive(sock,deadline):
    def read(n):
        out=bytearray()
        while len(out)<n:
            sock.settimeout(remaining(deadline))
            part=sock.recv(n-len(out));need(bool(part),'control channel EOF');out.extend(part)
        remaining(deadline);return bytes(out)
    n=struct.unpack('!I',read(4))[0];need(0<n<=MAX_FRAME,'control frame bound')
    value=json.loads(read(n),object_pairs_hook=unique,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite control frame')))
    remaining(deadline);return value


def close_pair(conn,pfd):
    errors=[]
    # Attempt every owned handle once; never retry an ambiguous numeric close.
    for name,handle,close in [('socket',conn,lambda:conn.close()),
                              ('pidfd',pfd,lambda:os.close(pfd))]:
        if handle is None:continue
        try:close()
        except BaseException as error:errors.append((name,handle,error))
    return errors


class CurrentOwnerServer:
    """Polled only by the existing Campaign.run loop, not a second controller.

    Root peers obtain data from fresh actual account reads. The reply deliberately
    grants no native allocation; the root physical-resource owner remains separate.
    """
    def __init__(self, campaign):
        self.campaign=campaign;self.clients=[];self.closed=False;self.close_state='OPEN';self.close_errors=[];self.unknown_handles=[];self.sock=None;self.identity=None;self.path=None
        self.pid=os.getpid();self.start=birth(self.pid)
        self._owning_context()
        self.path=str(campaign.directory/('native-current-owner.%d.%s.sock'%(self.pid,self.start)))
        need(len(os.fsencode(self.path))<104,'owning controller socket pathname')
        need(not os.path.lexists(self.path),'current controller channel already exists')
        self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        self.sock.bind(self.path)
        info=os.lstat(self.path);self.identity=(info.st_dev,info.st_ino)
        os.chmod(self.path,0o600);self.sock.listen(1);self.sock.setblocking(False)

    def _owning_context(self):
        c=self.campaign
        need(c.controlled and c.rpc is not None and c.state.get('thread_id')==ROOT_THREAD,
             'current already-owning Campaign required')
        need(c.state.get('worker_pid')==os.getpid() and str(c.state.get('worker_start'))==birth(os.getpid()),
             'foreign or recovered Campaign object')
        guard=c.credit_guard
        need(guard is not None and guard.identifier==CREDIT_RUN and guard.initialized,
             'same durable initialized credit run required')
        need(getattr(c.args,'credit_run_id',None)==CREDIT_RUN,'credit-run argument mismatch')
        need(hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==LOADED_SOURCE_SHA256,
             'owning control source changed after import')

    def _snapshot(self, request, deadline):
        self._owning_context();c=self.campaign
        # Existing account/read<=10s plus actual refresh retries<=33s; reserve
        # those unchanged calls inside this SAME60s handoff. No RPC proxy or
        # replacement credit guard can change same-RPC fallback semantics.
        need(remaining(deadline)>=ACCOUNT_RESERVE_SECONDS,'account handoff reserve exhausted')
        need(type(request) is dict and set(request)=={'schema','nonce','config_sha256','challenge','seq'},
             'current control request shape')
        need(request['schema']==SCHEMA and type(request['seq']) is int and request['seq']>0,
             'current control request identity')
        for k in ('nonce','config_sha256','challenge'):
            need(type(request[k]) is str and len(request[k])==64 and
                 all(ch in '0123456789abcdef' for ch in request[k]),'current control digest')
        # These calls execute only here, in the real already-owning controller.
        # refresh_credit_budget retains its actual same-RPC notification fallback,
        # persisted cumulative budget, unknown/exhausted stops and no new allowance.
        account=c.rpc.call('account/read',{'refreshToken':False},timeout=10).get('account') or {}
        if account.get('type')!='chatgpt':
            c.stop_reason,c.stop_now='chatgpt_auth_changed',True;c.save(auth_mode=account.get('type'))
        need(account.get('type')=='chatgpt','current signed-in ChatGPT account required')
        c.refresh_credit_budget()
        need(not c.stop_now and not c.stop_reason and not c.checkpoint_requested and not c.stopping,
             'owning controller stop/checkpoint')
        need(c.state.get('phase') in ('running','ready'),'owning controller phase')
        need(not any(c.state.get(k) for k in HOLDS),'current controller hold or unknown')
        budget=c.state.get('credit_budget')
        need(type(budget) is dict and budget.get('id')==CREDIT_RUN and
             Decimal(budget.get('budget'))==c.credit_guard.budget and
             Decimal(budget.get('remaining'))>0,'actual retained credit budget unavailable')
        self._owning_context();remaining(deadline)
        now=time.clock_gettime(time.CLOCK_BOOTTIME)
        return dict(schema=SCHEMA,authority=None,native_grant=False,
          scope='fresh-current-controller-account-data-only',request=request,
          controller_pid=self.pid,controller_birth=self.start,thread_id=ROOT_THREAD,
          guardian_run_id=c.state.get('guardian_run_id'),credit_run_id=CREDIT_RUN,
          credit_budget=budget,observed_boot=now,expires_boot=now+MAX_AGE,
          boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
          source_sha256=LOADED_SOURCE_SHA256)

    def poll(self):
        self._owning_context();need(self.close_state=='OPEN','controller service closed')
        try:
            conn,_=self.sock.accept();pfd=None
            try:
                conn.settimeout(15)
                pid,uid,gid=struct.unpack('3i',conn.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
                need(uid==0 and pid>1,'root native-operation peer required')
                start=birth(pid)
                try:pfd=pidfd_compat.open_pidfd(pid,0)
                except pidfd_compat.PidfdVerificationError as error:
                    pfd=error.fd;raise
                need(birth(pid)==start,'native-operation peer changed')
                need(not self.clients,'one native account handoff at a time')
                self.clients.append([conn,pid,start,pfd,None,0])
            except BaseException as primary:
                errors=close_pair(conn,pfd)
                if errors:
                    self.unknown_handles.extend(errors)
                    raise ChannelCleanupError(primary,errors) from primary
                raise
        except BlockingIOError:pass
        for client in tuple(self.clients):
            conn,pid,start,pfd,binding,seq=client
            poll=select.poll();poll.register(pfd,select.POLLIN)
            ready=select.poll();ready.register(conn,select.POLLIN|select.POLLHUP|select.POLLERR)
            events=ready.poll(0)
            if poll.poll(0) or birth(pid)!=start or (events and events[0][1]&(select.POLLHUP|select.POLLERR)):
                self.clients.remove(client)
                errors=close_pair(conn,pfd)
                if errors:
                    self.unknown_handles.extend(errors);raise ChannelCleanupError(None,errors)
                continue
            if not events:continue
            try:
                deadline=time.monotonic()+HANDOFF_SECONDS
                request=receive(conn,deadline)
                current=(request.get('nonce'),request.get('config_sha256'))
                need((binding is None or binding==current) and request.get('seq')==seq+1,
                     'native control binding or sequence changed')
                response=self._snapshot(request,deadline);send(conn,response,deadline)
                client[4],client[5]=current,seq+1
            except BaseException as primary:
                self.clients.remove(client)
                errors=close_pair(conn,pfd)
                if errors:
                    self.unknown_handles.extend(errors)
                    raise ChannelCleanupError(primary,errors) from primary
                raise

    def close(self):
        if self.close_state=='CLOSED':return
        if self.close_state!='OPEN':
            raise ChannelCleanupError(None,self.close_errors)
        self.close_state='CLOSING';errors=[]
        clients,self.clients=self.clients,[]
        for conn,pid,start,pfd,binding,seq in clients:
            errors.extend(close_pair(conn,pfd))
        if self.sock is not None:
            try:self.sock.close()
            except BaseException as error:errors.append(('listener',self.sock,error))
        if self.identity is not None:
            try:
                st=os.lstat(self.path)
                need((st.st_dev,st.st_ino)==self.identity and stat.S_ISSOCK(st.st_mode),
                     'current controller socket ownership changed')
                os.unlink(self.path)  # exact own socket only, never a resource lease
            except BaseException as error:errors.append(('socket_path',self.path,error))
        errors=self.unknown_handles+errors
        self.close_errors=errors
        self.closed=not errors;self.close_state='UNKNOWN_RETAINED' if errors else 'CLOSED'
        if errors:raise ChannelCleanupError(None,errors)


class CurrentOwnerSession:
    """Root-side authenticated client; has no native RAM permission semantics."""
    def __init__(self,path,controller_pid,controller_birth,source_sha256,nonce,config_sha256):
        self.sock=None;self.pidfd=None;self.closed=False;self.close_state='OPEN';self.close_errors=[];self.data=None
        need(os.geteuid()==0,'root operation caller required')
        st=os.lstat(path)
        need(stat.S_ISSOCK(st.st_mode) and st.st_uid==1000 and stat.S_IMODE(st.st_mode)==0o600,
             'owning controller socket identity')
        self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);self.sock.settimeout(15)
        self.sock.connect(path)
        pid,uid,gid=struct.unpack('3i',self.sock.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
        need((pid,uid)==(controller_pid,1000) and birth(pid)==controller_birth,
             'actual owning controller peer differs')
        self.pid,self.birth,self.source_sha=pid,controller_birth,source_sha256
        self.nonce,self.config_sha,self.seq=nonce,config_sha256,0
        try:self.pidfd=pidfd_compat.open_pidfd(pid,0)
        except pidfd_compat.PidfdVerificationError as error:
            self.pidfd=error.fd;raise
        need(birth(pid)==controller_birth,'controller changed during pidfd acquisition')
        self.revalidate()

    def revalidate(self):
        need(self.close_state=='OPEN' and birth(self.pid)==self.birth,'current owner session unavailable')
        p=select.poll();p.register(self.pidfd,select.POLLIN);need(not p.poll(0),'owning controller exited')
        if self.data is not None and time.clock_gettime(time.CLOCK_BOOTTIME)+0.5<self.data['expires_boot']:
            return self.data
        self.seq+=1
        request=dict(schema=SCHEMA,nonce=self.nonce,config_sha256=self.config_sha,
                     challenge=secrets.token_hex(32),seq=self.seq)
        deadline=time.monotonic()+HANDOFF_SECONDS
        start=time.clock_gettime(time.CLOCK_BOOTTIME)
        send(self.sock,request,deadline);row=receive(self.sock,deadline)
        need(type(row) is dict and set(row)=={'schema','authority','native_grant','scope','request',
          'controller_pid','controller_birth','thread_id','guardian_run_id','credit_run_id',
          'credit_budget','observed_boot','expires_boot','boot_id','source_sha256'},'owning snapshot shape')
        now=time.clock_gettime(time.CLOCK_BOOTTIME)
        need(row['schema']==SCHEMA and row['authority'] is None and row['native_grant'] is False and
          row['scope']=='fresh-current-controller-account-data-only' and row['request']==request and
          (row['controller_pid'],row['controller_birth'])==(self.pid,self.birth) and
          row['thread_id']==ROOT_THREAD and row['credit_run_id']==CREDIT_RUN and
          row['source_sha256']==self.source_sha==LOADED_SOURCE_SHA256 and
          row['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
          'owning snapshot binding')
        need(type(row['observed_boot']) in (int,float) and type(row['expires_boot']) in (int,float) and
          math.isfinite(row['observed_boot']) and math.isfinite(row['expires_boot']) and
          start<=row['observed_boot']<=now<row['expires_boot']<=row['observed_boot']+MAX_AGE,
          'owning snapshot stale')
        need(birth(self.pid)==self.birth and not p.poll(0),'owning controller lost after reply')
        self.data=row;return row

    def close(self):
        if self.close_state=='CLOSED':return
        if self.close_state!='OPEN':raise ChannelCleanupError(None,self.close_errors)
        self.close_state='CLOSING'
        errors=close_pair(self.sock,self.pidfd)
        self.close_errors=errors
        self.closed=not errors;self.close_state='UNKNOWN_RETAINED' if errors else 'CLOSED'
        if errors:raise ChannelCleanupError(None,errors)
