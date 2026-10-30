"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pre-registered caller-owned record for an uncertain newly opened pidfd.
"""
import fcntl
import json
import os
import stat
import threading


class PublicationUnknown(RuntimeError):
    def __init__(self,record):
        super().__init__('pidfd retained; UNKNOWN journal publication failed')
        self.record=record


class PidfdCustodyRecord:
    """Hold an unverified FD and journal its identity; never close/release it.

    The operation owner must retain this record. The root supervisor must create,
    own and pass the exact append-only journal FD before validator launch; source
    validation here does not authenticate that parent or grant execution authority.
    """
    def __init__(self,journal_fd,nonce):
        if type(nonce) is not str or len(nonce)!=64 or any(x not in '0123456789abcdef' for x in nonce):
            raise ValueError('operation nonce required')
        if type(journal_fd) is not int or journal_fd<0:raise ValueError('journal descriptor required')
        info=os.fstat(journal_fd);flags=fcntl.fcntl(journal_fd,fcntl.F_GETFL)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid!=0 or stat.S_IMODE(info.st_mode)!=0o600 or
            info.st_nlink!=1 or not flags&os.O_APPEND or flags&os.O_ACCMODE==os.O_RDONLY):
            raise ValueError('root-created append-only journal descriptor required')
        self.journal_fd=journal_fd;self.journal_identity=(info.st_dev,info.st_ino)
        self.owner_pid=os.getpid()
        fields=open('/proc/self/stat').read().rsplit(')',1)[1].split()
        if len(fields)<20:raise ValueError('validator birth unavailable')
        self.owner_birth=fields[19];self.nonce=nonce
        self.boot_id=open('/proc/sys/kernel/random/boot_id').read().strip()
        self.fd=None;self.state='REGISTERED';self.lock=threading.RLock()

    def _publish(self,status,reason,target_pid,target_birth):
        event={'status':status,'reason':reason,'owner_pid':self.owner_pid,
               'owner_birth':self.owner_birth,'boot_id':self.boot_id,'nonce':self.nonce,
               'pidfd':self.fd,'target_pid':target_pid,'target_birth':target_birth,
               'journal_device':self.journal_identity[0],'journal_inode':self.journal_identity[1]}
        raw=(json.dumps(event,sort_keys=True,separators=(',',':'))+'\n').encode()
        before=os.fstat(self.journal_fd)
        if (before.st_dev,before.st_ino)!=self.journal_identity:raise RuntimeError('custody journal identity changed')
        offset=0
        while offset<len(raw):
            count=os.write(self.journal_fd,raw[offset:])
            if count<=0:raise OSError('short custody journal write')
            offset+=count
        os.fsync(self.journal_fd)
        after=os.fstat(self.journal_fd)
        if (after.st_dev,after.st_ino)!=self.journal_identity:raise RuntimeError('custody journal identity changed after fsync')

    def retain_verified(self,fd,target_pid,target_birth):
        if type(fd) is not int or fd<0:raise ValueError('descriptor identity')
        if type(target_pid) is not int or target_pid<=0 or type(target_birth) is not str or not target_birth.isdigit():
            raise ValueError('target process identity required')
        with self.lock:
            if self.state!='REGISTERED' or self.fd is not None:raise RuntimeError('custody record already consumed')
            # Own first; publish the live descriptor before stop signals resume.
            self.fd=fd;self.target_pid=target_pid;self.target_birth=target_birth;self.state='VERIFIED_HELD'
            try:self._publish('VERIFIED_HELD','PIDFD_ACQUIRED',target_pid,target_birth)
            except BaseException as error:
                self.state='UNKNOWN_RETAINED'
                raise PublicationUnknown(self) from error
            return self

    def retain_unknown(self,fd,target_pid,target_birth):
        if type(fd) is not int or fd<0:raise ValueError('unverified descriptor identity')
        if type(target_pid) is not int or target_pid<=0 or type(target_birth) is not str or not target_birth.isdigit():
            raise ValueError('target process identity required')
        with self.lock:
            if self.state=='UNKNOWN_RETAINED':
                if self.fd!=fd:raise RuntimeError('unknown descriptor differs')
                return self
            if self.state=='REGISTERED' and self.fd is None:
                self.fd=fd;self.target_pid=target_pid;self.target_birth=target_birth
            elif (self.state!='VERIFIED_HELD' or self.fd!=fd or self.target_pid!=target_pid or
                  self.target_birth!=target_birth):raise RuntimeError('custody record already consumed')
            # Sticky before publication: a failed fsync never loses the descriptor.
            self.state='UNKNOWN_RETAINED'
            try:self._publish('UNKNOWN_RETAINED','PIDFD_OR_STOP_UNCERTAIN',target_pid,target_birth)
            except BaseException as error:raise PublicationUnknown(self) from error
            return self

    def close_verified(self):
        with self.lock:
            if self.state!='VERIFIED_HELD':raise RuntimeError('unknown descriptor cannot be closed')
            os.close(self.fd);self.state='OBSERVER_CLOSED'

    def retire(self):
        raise RuntimeError('no authority to close an uncertain retained pidfd')
