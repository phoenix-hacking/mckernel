"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Synchronized sticky failure and pre-fork custody records; no operating effects.
"""
import threading


class StaleTransition(RuntimeError):pass


class CustodyLatch:
    def __init__(self,state):
        self.lock=threading.RLock();self.state=state;self.epoch=0
        self.failure=None;self.retained=[];self.children={}

    def snapshot(self):
        with self.lock:return self.state,self.epoch

    def begin(self,expected):
        with self.lock:
            if self.failure is not None or self.state!=expected:raise StaleTransition('state unavailable')
            return (self.state,self.epoch)

    def check(self,token):
        with self.lock:
            if self.failure is not None or token!=(self.state,self.epoch):
                raise StaleTransition('failure or epoch changed')

    def retain(self,*handles):
        with self.lock:
            self.retained.extend(handles)

    def commit(self,token,new_state,*handles):
        with self.lock:
            # Every produced handle remains reachable even if failure races success.
            self.retained.extend(handles)
            if self.failure is not None or token!=(self.state,self.epoch):
                raise StaleTransition('failure or epoch changed before success')
            self.state=new_state;self.epoch+=1
            return self.epoch

    def publish(self,token,action,*handles):
        """Linearize bounded publication with failure latching; retain on failure."""
        with self.lock:
            self.retained.extend(handles)
            if self.failure is not None or token!=(self.state,self.epoch):
                raise StaleTransition('failure or epoch changed before publication')
            try:return action()
            except BaseException as error:
                self.fail(error)
                raise

    def fail(self,reason,*handles):
        with self.lock:
            self.retained.extend(handles)
            if self.failure is None:self.failure=str(reason)
            self.state='UNKNOWN_RETAINED';self.epoch+=1

    def reserve_child(self,role,*handles):
        with self.lock:
            if self.failure is not None or role in self.children:raise StaleTransition('child reservation refused')
            record=ChildRecord(self,role,handles)
            self.children[role]=record;self.retained.append(record)
            return record


class ChildRecord:
    """Registered before fork; every later resource is retained under latch lock."""
    def __init__(self,latch,role,handles):
        self.latch=latch;self.role=role;self.handles=list(handles)
        self.pid=None;self.birth=None;self.pidfd=None;self.status='PENDING'

    def add(self,*handles):
        with self.latch.lock:self.handles.extend(handles)

    def assigned(self,pid):
        with self.latch.lock:
            if type(pid) is not int or pid<=0 or self.pid is not None:raise StaleTransition('child pid assignment')
            self.pid=pid;self.status='UNKNOWN_RETAINED' if self.latch.failure is not None else 'PID_ASSIGNED'

    def pin_pidfd(self,pidfd):
        with self.latch.lock:
            if self.pid is None or type(pidfd) is not int or pidfd<0 or self.pidfd is not None:
                raise StaleTransition('pidfd assignment')
            self.pidfd=pidfd;self.status='UNKNOWN_RETAINED' if self.latch.failure is not None else 'PIDFD_ASSIGNED'

    def identified(self,birth,pidfd):
        with self.latch.lock:
            if self.pid is None or type(birth) is not str or not birth.isdigit() or type(pidfd) is not int or pidfd<0:
                raise StaleTransition('child identity unavailable')
            if self.pidfd != pidfd:raise StaleTransition('pidfd differs from retained descriptor')
            self.birth=birth
            if self.latch.failure is not None:
                self.status='UNKNOWN_RETAINED'
                raise StaleTransition('failure latched before child identification')
            self.status='IDENTIFIED'

    def unknown(self,error):
        with self.latch.lock:
            self.status='UNKNOWN_RETAINED'
            self.latch.fail(error)
