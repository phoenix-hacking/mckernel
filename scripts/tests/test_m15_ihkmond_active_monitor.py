"""Two active monitor HOST cases under a separately admitted stat mapping.

Explicit absolute CC/RUSTC and fresh aggregate HOST admission required. The one
literal /dev/mcos0 stat is forwarded to a liveness-owned regular tempfile through
genuine HOST stat. DETECT takes scalar unsigned long and errors are nonfatal.
No device metadata, actual hung-up detection, native or milestone claim.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest

from test_m15_ihkmond_active_workers import generate_sources,profile

HERE=Path(__file__).resolve().parent
ROOT=Path(os.environ.get('M15_REPO',Path(__file__).resolve().parents[2]))
FIXTURES=HERE/'fixtures/m15-ihkmond-active-monitor'


def generate_monitor_sources(supervisor,event_provider,tail):
 units=generate_sources(supervisor,event_provider,tail);unit=units.pop('active.rs')
 start=unit.index('extern "C"{');end=unit.index('\n}\nfn errno',start);declarations=unit[start:end]
 if declarations.count('fn stat(')!=1:raise ValueError('Expected one actual monitor stat declaration')
 declarations=declarations.replace('fn stat(','#[link_name="fixture_stat"] fn stat(')
 units['monitor.rs']=unit[:start]+declarations+unit[end:];return units


class M15IhkmondActiveMonitorTests(unittest.TestCase):
 def test_two_actual_monitor_cases(self):
  compilers={name:Path(os.environ[name]) for name in ('CC','RUSTC')}
  for name,path in compilers.items():self.assertTrue(path.is_absolute() and path.is_file() and os.access(path,os.X_OK),name+' requires an explicit absolute executable')
  sources={'supervisor':ROOT/'ihk/linux/user/rust/ihkmond.rs','event_provider':ROOT/'ihk/linux/user/rust/whole70/ihklib_eventfd.rs','header':ROOT/'ihk/linux/include/ihk/ihk_host_user.h','stat_oracle':ROOT/'ihk/linux/user/rust/whole70/abi/selected_target_stat_dirent_ABI.c','tail':FIXTURES/'cases.rs.in','seam':FIXTURES/'seams.c'}
  inputs={name:path.read_text() for name,path in sources.items()};units=generate_monitor_sources(inputs['supervisor'],inputs['event_provider'],inputs['tail']);units['seams.c']=inputs['seam']
  with tempfile.TemporaryDirectory(prefix='m15-active-monitor-',dir=os.environ.get('TMPDIR')) as directory:
   work=Path(directory);receipt=Path(os.environ['M15_ACTIVE_MONITOR_RECEIPT_DIR']) if 'M15_ACTIVE_MONITOR_RECEIPT_DIR' in os.environ else work/'receipt';receipt.mkdir(parents=True,exist_ok=False)
   for name,text in units.items():(work/name).write_text(text)
   (receipt/'source-binding.json').write_text(json.dumps({name:{'path':str(sources[name]),'sha256':hashlib.sha256(text.encode()).hexdigest()} for name,text in inputs.items()},indent=2)+'\n')
   binary=work/'monitor';seam=work/'seams.o';stat_path=str(work/'stat-exists');includes=['-I'+str(ROOT/'ihk/linux/include'),'-I'+str(ROOT/'ihk/linux/include/ihk/arch/x86_64')]
   commands=[('monitor-seam-compile',[str(compilers['CC']),'-std=gnu11','-Wall','-Wextra','-Werror',*includes,'-DACTIVE_MONITOR_STAT_PATH='+json.dumps(stat_path),'-c',str(work/'seams.c'),'-o',str(seam)]),('monitor-compile',[str(compilers['RUSTC']),'--edition=2021','-Dwarnings','-Adead_code','-Aunused_imports',str(work/'monitor.rs'),'-C','link-arg='+str(seam),'-o',str(binary)]),('monitor-two-cases',[str(binary)])]
   environment={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C','IHKMOND_TMP':str(work/'unused-ring'),'MONITOR_STAT_PATH':stat_path};rows=[]
   for label,payload in commands:
    argv=profile(payload,receipt/(label+'.metrics'))
    with (receipt/(label+'.stdout')).open('xb') as stdout,(receipt/(label+'.stderr')).open('xb') as stderr:
     child=subprocess.Popen(argv,cwd=ROOT,env=environment,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
     try:birth=Path('/proc/'+str(child.pid)+'/stat').read_text().rsplit(')',1)[1].split()[19]
     except FileNotFoundError:birth=None
     finally:status=child.wait()
    rows.append({'label':label,'argv':argv,'environment':environment,'pid':child.pid,'proc_start_ticks':birth,'returncode':status,'direct_wait_joined':True});(receipt/'commands.json').write_text(json.dumps(rows,indent=2)+'\n');artifacts={}
    for artifact in [*(work/name for name in units),seam,binary]:
     if artifact.is_file():shutil.copyfile(artifact,receipt/artifact.name);artifacts[artifact.name]=hashlib.sha256(artifact.read_bytes()).hexdigest()
    (receipt/'artifacts.json').write_text(json.dumps(artifacts,indent=2)+'\n')
    stdout=(receipt/(label+'.stdout')).read_text();stderr=(receipt/(label+'.stderr')).read_text();self.assertEqual(status,0,label+'\n'+stdout+stderr);self.assertEqual(stderr,'',label+' unexpected diagnostics')
    if label=='monitor-two-cases':
     for mode in ('normal','ioctl-eio'):self.assertEqual(stdout.count('CASE active-monitor-'+mode+' ticks-at-least=2 nonfatal-continuation=1 worker-status=0 all-owned-fds-tasks-restored=1\n'),1)
     self.assertTrue(stdout.endswith('active-monitor cases=2 genuine-stat-threads-timing-eventfd-epoll=1 nonfatal-ioctl-contract=1 no-device-native-claim=1\n'))


if __name__=='__main__':unittest.main()
