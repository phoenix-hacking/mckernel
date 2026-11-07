"""Two active ihkmond HOST cases; explicit absolute CC/RUSTC required.

Current actual worker/provider bodies run with real threads,eventfd,epoll and
files. Only selected local IHK open/ioctl and syslog seams are substituted.
This is neither daemon/device/native qualification nor milestone acceptance.
Invoke only under fresh aggregate ordinary HOST admission (CPU0, one local job).
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
ROOT=Path(os.environ.get('M15_REPO',Path(__file__).resolve().parents[2]))
FIXTURES=HERE/'fixtures/m15-ihkmond-active-workers'


def generate_sources(supervisor,event_provider,tail):
 prefix=supervisor[:supervisor.index('struct SignalMask{')]
 start=prefix.index('extern "C"{');end=prefix.index('\n}\nfn errno',start)
 declarations=prefix[start:end]
 for name in ('ioctl','openlog','closelog','syslog'):
  marker='fn '+name+'('
  if declarations.count(marker)!=1:raise ValueError('Expected one actual FFI declaration: '+name)
  declarations=declarations.replace(marker,'#[link_name="fixture_'+name+'"] '+marker)
 prefix=prefix[:start]+declarations+prefix[end:]
 if event_provider.count('fn ioctl(')!=1:raise ValueError('Expected actual event-provider ioctl declaration')
 event_provider=event_provider.replace('fn ioctl(','#[link_name="fixture_ioctl"] fn ioctl(')
 return {'active.rs':prefix+'\n#[path="eventfd.actual.rs"]mod actual_event_provider;\n'+tail,'eventfd.actual.rs':event_provider}


def profile(payload,metrics):
 return ['/usr/bin/taskset','-c','0','/usr/bin/timeout','--signal=TERM','--kill-after=2s','58s','/usr/bin/prlimit','--as=1073741824:1073741824','--cpu=45:45','--fsize=67108864:67108864','--core=0:0','--','/usr/bin/time','-v','-o',str(metrics)]+payload


class M15IhkmondActiveWorkersTests(unittest.TestCase):
 def test_two_actual_active_worker_cases(self):
  compilers={name:Path(os.environ[name]) for name in ('CC','RUSTC')}
  for name,path in compilers.items():self.assertTrue(path.is_absolute() and path.is_file() and os.access(path,os.X_OK),name+' requires an explicit absolute executable')
  sources={'supervisor':ROOT/'ihk/linux/user/rust/ihkmond.rs','event_provider':ROOT/'ihk/linux/user/rust/whole70/ihklib_eventfd.rs','header':ROOT/'ihk/linux/include/ihk/ihk_host_user.h','tail':FIXTURES/'cases.rs.in','seam':FIXTURES/'seams.c'}
  inputs={name:path.read_text() for name,path in sources.items()}
  units=generate_sources(inputs['supervisor'],inputs['event_provider'],inputs['tail']);units['seams.c']=inputs['seam']
  with tempfile.TemporaryDirectory(prefix='m15-active-workers-',dir=os.environ.get('TMPDIR')) as directory:
   work=Path(directory);receipt=Path(os.environ['M15_ACTIVE_WORKERS_RECEIPT_DIR']) if 'M15_ACTIVE_WORKERS_RECEIPT_DIR' in os.environ else work/'receipt';receipt.mkdir(parents=True,exist_ok=False)
   for name,text in units.items():(work/name).write_text(text)
   binding={name:{'path':str(sources[name]),'sha256':hashlib.sha256(text.encode()).hexdigest()} for name,text in inputs.items()}
   (receipt/'source-binding.json').write_text(json.dumps(binding,indent=2)+'\n')
   binary=work/'active';seam=work/'seams.o';includes=['-I'+str(ROOT/'ihk/linux/include'),'-I'+str(ROOT/'ihk/linux/include/ihk/arch/x86_64')]
   commands=[('seam-compile',[str(compilers['CC']),'-std=gnu11','-Wall','-Wextra','-Werror',*includes,'-c',str(work/'seams.c'),'-o',str(seam)]),('active-compile',[str(compilers['RUSTC']),'--edition=2021','-Dwarnings','-Adead_code','-Aunused_imports',str(work/'active.rs'),'-C','link-arg='+str(seam),'-o',str(binary)]),('active-two-cases',[str(binary)])]
   environment={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C','IHKMOND_TMP':str(work/'ring')};rows=[]
   for label,payload in commands:
    argv=profile(payload,receipt/(label+'.metrics'))
    with (receipt/(label+'.stdout')).open('xb') as stdout,(receipt/(label+'.stderr')).open('xb') as stderr:
     child=subprocess.Popen(argv,cwd=ROOT,env=environment,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
     try:birth=Path('/proc/'+str(child.pid)+'/stat').read_text().rsplit(')',1)[1].split()[19]
     except FileNotFoundError:birth=None
     finally:status=child.wait()
    rows.append({'label':label,'argv':argv,'environment':environment,'pid':child.pid,'proc_start_ticks':birth,'returncode':status,'direct_wait_joined':True});(receipt/'commands.json').write_text(json.dumps(rows,indent=2)+'\n')
    artifacts={}
    for artifact in [*(work/name for name in units),seam,binary]:
     if artifact.is_file():shutil.copyfile(artifact,receipt/artifact.name);artifacts[artifact.name]=hashlib.sha256(artifact.read_bytes()).hexdigest()
    (receipt/'artifacts.json').write_text(json.dumps(artifacts,indent=2)+'\n')
    stdout=(receipt/(label+'.stdout')).read_text();stderr=(receipt/(label+'.stderr')).read_text();self.assertEqual(status,0,label+'\n'+stdout+stderr);self.assertEqual(stderr,'',label+' unexpected diagnostics')
    if label=='active-two-cases':
     self.assertEqual(stdout.count('CASE active-two-generation-stop status=0 generations=2 reads=6 releases=2 exact-lines=4 restored-fds-tasks=1\n'),1)
     self.assertEqual(stdout.count('CASE partial-second-register status=-22 first-registration-real=1 reads=0 releases=1 restored-fds-tasks=1\n'),1)
     self.assertTrue(stdout.endswith('active-supervisor cases=2 genuine-threads-eventfd-epoll-ring=1 all-owned-fds-tasks-restored=1 local-IHK-syslog-seams-only=1\n'))


if __name__=='__main__':unittest.main()
