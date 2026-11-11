"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Immutable held-lease epoch: full hash once, fresh full inode/flag checks later.
"""
import os
import stat
import time
import graph_observations as obs
import inplace_custody as custody


def fail(msg):raise ValueError(msg)


class ImmutableEpoch:
    def __init__(self, roots, expected_contents, deadline_boot):
        if type(roots) is not dict or type(expected_contents) is not dict or set(roots)!=set(expected_contents) or '/work' in roots:
            fail('exact immutable root set')
        self.roots=dict(roots);self.contents=dict(expected_contents);self.deadline_boot=deadline_boot
        self.namespace_fd=os.open('/proc/self/ns/mnt',os.O_RDONLY|os.O_CLOEXEC)
        self.namespace_identity=(os.fstat(self.namespace_fd).st_dev,os.fstat(self.namespace_fd).st_ino)
        self.baseline=self._scan()
        for target,path in self.roots.items():
            self._deadline()
            st=os.lstat(path)
            actual=obs.inventory(path) if stat.S_ISDIR(st.st_mode) else obs.file_sha(path)
            if actual!=self.contents[target]:fail('epoch content differs')
        if self._scan()!=self.baseline:fail('epoch changed during initial content verification')

    def _deadline(self):
        if time.clock_gettime(time.CLOCK_BOOTTIME)>=self.deadline_boot:raise TimeoutError('immutable epoch deadline')

    def _scan(self):
        current={}; seen={}
        process=obs.process(os.getpid());mounts=obs.read_mountinfo(os.getpid(),process)
        ns=os.fstat(self.namespace_fd)
        if (process[1],process[2])!=self.namespace_identity or (ns.st_dev,ns.st_ino)!=self.namespace_identity:
            fail('mount namespace identity changed')
        roots={}
        for target,path in self.roots.items():
            self._deadline()
            if any(mount!=path and mount.startswith(path.rstrip('/')+'/') for mount in mounts):
                fail('nested source mount')
            ancestors={m:mounts[m] for m in mounts if path==m or path.startswith(m.rstrip('/')+'/')}
            if not ancestors:fail('source ancestor mounts missing')
            roots[target]=ancestors
            fd=custody.open_exact(path)
            try:
                root=os.fstat(fd);self._visit(fd,path,root.st_dev,current,seen)
                named,_=obs.direct_path(path)
                if (root.st_dev,root.st_ino)!=(named.st_dev,named.st_ino):fail('epoch root changed')
            finally:os.close(fd)
        after_process=obs.process(os.getpid())
        if after_process!=process or obs.read_mountinfo(os.getpid(),process)!=mounts:
            fail('mount topology changed across epoch scan')
        return (self.namespace_identity,mounts,roots,current)

    def _visit(self,fd,path,device,current,seen):
        self._deadline();st=os.fstat(fd)
        if st.st_dev!=device or not (stat.S_ISREG(st.st_mode) or stat.S_ISDIR(st.st_mode)):
            fail('epoch cross-device or unsupported inode')
        key=(st.st_dev,st.st_ino)
        if key in seen and seen[key]!=path:fail('epoch inode alias')
        seen[key]=path
        if not custody.flags(fd)&custody.IMMUTABLE:fail('epoch immutable flag missing')
        fingerprint=obs.stable(st)
        if path in current and current[path]!=fingerprint:fail('epoch repeated path changed')
        current[path]=fingerprint
        if stat.S_ISDIR(st.st_mode):
            names=sorted(os.listdir(fd))
            if len(current)+len(names)>500000:fail('epoch entry cap')
            for name in names:
                entry=os.stat(name,dir_fd=fd,follow_symlinks=False)
                if not (stat.S_ISREG(entry.st_mode) or stat.S_ISDIR(entry.st_mode)):
                    fail('epoch symlink or special inode')
                flags=os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC
                if stat.S_ISDIR(entry.st_mode):flags|=os.O_DIRECTORY
                child=os.open(name,flags,dir_fd=fd)
                try:
                    if obs.stable(os.fstat(child))!=obs.stable(entry):fail('epoch child changed')
                    self._visit(child,path+'/'+name,device,current,seen)
                finally:os.close(child)
            if sorted(os.listdir(fd))!=names or obs.stable(os.fstat(fd))!=fingerprint:fail('epoch directory changed')

    def verify(self):
        if self._scan()!=self.baseline:fail('immutable epoch changed')
        return self.contents
