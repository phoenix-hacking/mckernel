"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Fixed tiny no-guest attach/retirement smoke. NOT RELEASED; no native/app credit.
Uses unchanged inherited owner creation/profile/identity/cleanup/lease mechanisms.
"""
from pathlib import Path
import hashlib, importlib.util, json, os, resource, sys, time
D=Path(__file__).resolve().parent
OWNER=D/'source/native_diagnostic_container_owner.py'
OWNER_SHA='2525d2524a74de6d4443e2eb54fbc9d8d01be9ab124674da9c4d38858da154c7'
NONCE='089abb30162c46c4b42b86db06235ecf'
PROGRAM="import os;os.write(1,b'P12_NONE_STDOUT\\n');os.write(2,b'P12_NONE_STDERR\\n')"

def load():
    if hashlib.sha256(OWNER.read_bytes()).hexdigest()!=OWNER_SHA:raise RuntimeError('owner source drift')
    spec=importlib.util.spec_from_file_location('p12_none_smoke_owner',OWNER)
    o=importlib.util.module_from_spec(spec);spec.loader.exec_module(o);return o

def make(o):
    class SmokeOwner(o.DiagnosticOwner):
        def _inside_args(self):return ['-I','-B','-c',PROGRAM]
        def run(self):
            o.need(os.getuid()==os.geteuid()==0,'root owner required')
            o.need(os.sched_getaffinity(0)=={7},'root smoke CPU7')
            for k,pair in [(resource.RLIMIT_AS,(2*2**30,)*2),(resource.RLIMIT_CPU,(resource.RLIM_INFINITY,resource.RLIM_INFINITY)),
                           (resource.RLIMIT_FSIZE,(384*2**20,)*2),(resource.RLIMIT_CORE,(0,0)),
                           (resource.RLIMIT_NOFILE,(4096,4096))]:
                o.need(resource.getrlimit(k)==pair,'exact smoke root limits')
            st=self.parent.lstat()
            o.need(self.parent.is_dir() and not self.parent.is_symlink() and st.st_uid==st.st_gid==1000 and
                   st.st_mode&0o777==0o700 and not list(self.parent.iterdir()),'fresh private smoke parent')
            o.need(o._digest(o.IMAGE_RECORD)==o.IMAGE_RECORD_SHA256,'accepted image record')
            retained=o.one(o.regular(o.IMAGE_RECORD))
            self.outer_identity=o._outer_identity()
            self.evidence.mkdir(mode=0o700)
            self._acquire();self.may_exist=True;self._queue_owner()
            try:
                o.need(self._lookup() is None,'fresh smoke owner identity')
                image=o.one(self._call(['image','inspect',o.IMAGE]).stdout)
                o.need(image.get('Id')==o.IMAGE and image.get('Architecture')=='amd64' and image.get('Os')=='linux' and
                       o.same(image.get('Config'),retained.get('Config')) and o.same(image.get('RootFS'),retained.get('RootFS')),
                       'accepted image bytes/config')
                self.create_issued=True
                created=self._call(self._create_argv())
                cid=created.stdout.decode('ascii').strip()
                o.need(o.HEX.fullmatch(cid) and created.stdout==(cid+'\n').encode(),'full create identity')
                self.container=cid;self.create_completed=True
                row=self._lookup();o.need(row is not None,'created identity');self._profile(row,image)
                o.need(row['State']['Status']=='created' and row['State']['Running'] is False,'never started before profile')
                started=self._call(['start','--attach',cid],timeout=10)
                o.need(started.stdout==b'P12_NONE_STDOUT\n' and started.stderr==b'P12_NONE_STDERR\n','exact attached streams')
                waited=self._call(['wait',cid],timeout=3)
                o.need(waited.stdout==b'0\n' and waited.stderr==b'','exact wait exit0')
                row=self._lookup();o.need(row is not None,'final identity');self._profile(row,image)
                st=row['State'];self._save('state.json',st)
                o.need(st.get('Status')=='exited' and st.get('Pid')==0 and st.get('ExitCode')==0 and
                       all(st.get(k) is False for k in ('Running','Paused','Restarting','OOMKilled','Dead')) and
                       st.get('Error','')=='','exact stopped state')
                self._save('attach-observation.json',{'stdout':'P12_NONE_STDOUT\n','stderr':'P12_NONE_STDERR\n',
                    'logconfig':row['HostConfig']['LogConfig'],'guest':False,'application_acceptance':False})
            except BaseException as exc:self._remember(exc)
            finally:
                self._cleanup()
                if self.absent:self._release()
                if self.absent and self.lock is None:self._flush()
            if self.failure is not None:raise self.failure
    i=object.__new__(SmokeOwner)
    i.parent=D/'p';i.long_requested=True;i.name='mckernel-native-diagnostic-'+NONCE
    i.label='mckernel.native-diagnostic.owner='+NONCE;i.nonce=NONCE;i.container=None
    i.evidence=D/('p.owner-'+NONCE);i.attempt=i.parent/('attempt-'+NONCE)
    i.backend=o.DockerBackend();i.clock=time.monotonic;i.sleep=time.sleep
    i.lock=None;i.sequence=0;i.failure=None;i.secondary=[];i.secondary_omitted=0
    i.may_exist=False;i.create_issued=False;i.create_completed=False;i.absent=False
    i.cleaning=False;i.command_deadline=None;i.pending_evidence=[];i.pending_bytes=0
    i.flushing=False;i.signal_number=None;i.outer_identity=None;i.lock_identity=None
    i.cgroup_profile=None;i.owner_queued=False;i.retirement_sequence=0;i.long_logs_issued=False
    i.owner_sha=OWNER_SHA;i.admitted_qemu_argv=None
    return i

def main():
    if len(sys.argv)!=2 or hashlib.sha256(Path(__file__).read_bytes()).hexdigest()!=sys.argv[1]:
        raise RuntimeError('exact smoke source digest argument')
    o=load();return o.execute_owner(make(o))
if __name__=='__main__':raise SystemExit(main())
