"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One operation-scoped owner; synchronized UNKNOWN and retained failure custody.
"""
import hashlib
import os
import select
import threading
import graph_observations as obs
import graph_producer as graph
import graph_server
import inplace_custody as source
import union_server_guarded as union_server
import custody_protocol_v2 as wire
import root_bootstrap
import deferred_fork
from ownership_latch import CustodyLatch


def fail(message):raise ValueError(message)


class OperationSupervisor:
    def __init__(self,root_fd,lease_fd,nonce,boot_id,caps,watchdog_pid,watchdog_birth):
        self.latch=CustodyLatch('INITIALIZING');self.latch.retain(root_fd,lease_fd)
        self.root_fd,self.nonce,self.boot_id,self.caps=root_fd,nonce,boot_id,dict(caps)
        self.owner=None;self.source=None;self.graph=None;self.graph_channel=None
        self.opened_fds=[];self.direct_joins={};self.service_stop=threading.Event();self.service_threads=[];self.service_error=None
        try:
            source.root_private(root_fd);wire.sha256_hex(nonce);graph.cap(self.caps,self.boot_id)
            self.lease=graph.RootLease(lease_fd,root_fd,nonce,watchdog_pid,watchdog_birth)
            self.custody_sha256=hashlib.sha256(obs.canonical({'lease_sha256':self.lease.lease_sha256,
                'nonce':nonce,'operation_root':obs.ident(os.fstat(root_fd))})).hexdigest()
            name='GRAPH-NONCE-INTENT-'+nonce+'.json'
            fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=root_fd)
            self.latch.retain(fd)
            try:
                source.write_all(fd,obs.canonical({'status':'INTENT','nonce':nonce,
                    'lease_sha256':self.lease.lease_sha256,'custody_sha256':self.custody_sha256})+b'\n')
                os.fsync(fd);os.fsync(root_fd)
            finally:os.close(fd)
            self.lease.verify();self.latch.commit(('INITIALIZING',0),'ROOT_HELD')
        except BaseException as error:
            self.abort(error);raise

    @property
    def state(self):return self.latch.snapshot()[0]

    def abort(self,error,*handles):
        self.latch.fail(error,*handles);self.service_stop.set()

    def launch_owner(self,executable,executable_sha,entry_source,entry_sha,argv,environment,expected_targets,deadline,max_step):
        token=self.latch.begin('ROOT_HELD')
        if entry_source not in argv or argv[0]!=executable:fail('owner argv/source binding')
        record=None
        try:
            with deferred_fork.DeferredFork() as guard:
                record=self.latch.reserve_child('owner',self.root_fd,self.lease.fd)
                exe_fd,_=root_bootstrap.pinned_root_file(executable,executable_sha,128*1024*1024)
                record.add(exe_fd);self.opened_fds.append(exe_fd)
                entry_fd,_=root_bootstrap.pinned_root_file(entry_source,entry_sha)
                record.add(entry_fd);self.opened_fds.append(entry_fd)
                sock,pid,pidfd,result=root_bootstrap.fork_union_owner(executable,argv,environment,record,guard)
            if result[0]!='BOUND':fail('owner pidfd unavailable')
            birth=record.birth
            candidate=union_server.UnionChannel.__new__(union_server.UnionChannel);record.add(candidate)
            candidate.__init__(sock,pid,birth,self.lease,self.custody_sha256,expected_targets,deadline,max_step,self.latch)
            self.latch.commit(token,'OWNER_HELD',candidate)
            self.owner=candidate
            return pid,birth
        except BaseException as error:
            if record is not None:record.unknown(error)
            self.abort(error,record);raise

    def service_owner_once(self):
        state,_=self.latch.snapshot()
        if state not in ('OWNER_HELD','SOURCES_HELD','PRE_SHADOW_HELD','GRAPH_HELD'):fail('owner state unavailable')
        try:self.owner.handle_one()
        except BaseException as error:self.abort(error);raise

    def acquire_sources(self,source_manifest,manifest_sha):
        token=self.latch.begin('OWNER_HELD')
        try:
            self.owner.require_ready()
            if set(self.owner.observed_targets)!=set(self.owner.expected):fail('four owner targets not observed')
            fds={}
            for target,row in self.owner.observed_targets.items():
                fd=source.open_exact(row['path']);self.latch.retain(fd);self.opened_fds.append(fd);fds[target]=fd
                if obs.ident(os.fstat(fd))!=row['identity']:fail('owner target changed')
            candidate=source.ExactSourceCustody.__new__(source.ExactSourceCustody);self.latch.retain(candidate)
            candidate.__init__(self.lease,self.root_fd,source_manifest,manifest_sha,fds,self.caps['boot'],self.latch)
            if candidate.custody_sha256!=self.custody_sha256:fail('custody commitment differs')
            candidate.acquire();self.owner.require_ready()
            self.latch.commit(token,'SOURCES_HELD',candidate);self.source=candidate
        except BaseException as error:self.abort(error);raise

    def observe_before_children(self,target_pid,hosts):
        token=self.latch.begin('SOURCES_HELD')
        try:
            candidate=graph.GraphProducer.__new__(graph.GraphProducer);self.latch.retain(candidate)
            candidate.__init__(self.source,self.owner,target_pid,hosts,self.source.owner_fds,self.boot_id,self.caps,self.latch)
            result=candidate.observe_pre_shadow();self.owner.require_ready()
            self.latch.commit(token,'PRE_SHADOW_HELD',candidate,result);self.graph=candidate
            return result
        except BaseException as error:self.abort(error);raise

    def observe_effective_graph(self):
        token=self.latch.begin('PRE_SHADOW_HELD')
        try:
            result=self.graph.observe_effective();self.owner.require_ready()
            self.latch.commit(token,'GRAPH_HELD',result);return result
        except BaseException as error:self.abort(error);raise

    def reserve_validator(self,*handles):
        self.latch.begin('GRAPH_HELD')
        return self.latch.reserve_child('validator',*handles)

    def bind_validator(self,sock,pid,birth,pidfd,deadline,max_age,max_step,record):
        token=self.latch.begin('GRAPH_HELD')
        try:
            if record.birth!=birth or record.pidfd!=pidfd:fail('validator owned record differs')
            candidate=graph_server.GraphChannel.__new__(graph_server.GraphChannel);record.add(candidate)
            candidate.__init__(sock,self.graph,pid,birth,deadline,max_age,max_step,self.latch)
            self.owner.require_ready();self.latch.commit(token,'GRAPH_HELD',candidate)
            self.graph_channel=candidate
        except BaseException as error:record.unknown(error);self.abort(error,record);raise

    def service_validator_once(self):
        self.latch.begin('GRAPH_HELD')
        if self.graph_channel is None:fail('validator not bound')
        try:self.graph_channel.handle_one()
        except BaseException as error:self.abort(error);raise

    def _start_service(self,sock,handler):
        def loop():
            poll=select.poll();poll.register(sock.fileno(),select.POLLIN|select.POLLERR|select.POLLHUP)
            try:
                while not self.service_stop.is_set():
                    self.lease.verify();graph.cap(self.caps,self.boot_id);self.owner.verify_owner()
                    events=poll.poll(1000)
                    if events:
                        event=events[0][1]
                        if event&(select.POLLERR|select.POLLHUP|select.POLLNVAL):fail('service peer lost')
                        if event&select.POLLIN:handler()
            except BaseException as error:
                self.service_error=(type(error).__name__,str(error));self.abort(error)
        worker=threading.Thread(target=loop,daemon=False)
        self.latch.retain(worker);self.service_threads.append(worker);worker.start();return worker

    def start_owner_service(self):
        self.latch.begin('OWNER_HELD')
        if self.service_threads:fail('owner service already started')
        return self._start_service(self.owner.sock,self.service_owner_once)

    def start_graph_service(self):
        self.latch.begin('GRAPH_HELD')
        if self.graph_channel is None or len(self.service_threads)!=1:fail('graph service not ready')
        return self._start_service(self.graph_channel.sock,self.service_validator_once)

    def collect_direct_joins(self):
        for role,record in self.latch.children.items():
            if role in self.direct_joins or record.pid is None or record.pidfd is None:continue
            poll=select.poll();poll.register(record.pidfd,select.POLLIN)
            if not poll.poll(0):continue
            got,status=os.waitpid(record.pid,os.WNOHANG)
            if got==0:continue
            if got!=record.pid:fail('direct wait identity')
            result={'status':'DIRECT_WAIT_ONLY_UNKNOWN_RETAINED','role':role,'pid':record.pid,
                    'birth':record.birth,'wait_status':status,'nonce':self.nonce}
            self.latch.retain(result)
            name='GRAPH-DIRECT-JOIN-'+role+'-'+self.nonce+'.json'
            fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=self.root_fd)
            self.latch.retain(fd)
            try:source.write_all(fd,obs.canonical(result)+b'\n');os.fsync(fd);os.fsync(self.root_fd)
            finally:os.close(fd)
            self.direct_joins[role]=result
        return dict(self.direct_joins)

    def retire(self):raise RuntimeError('retirement needs independent physical acceptance; custody remains held')


if __name__=='__main__':raise RuntimeError('SOURCE ONLY: no approved root bootstrap or one-shot admission')
