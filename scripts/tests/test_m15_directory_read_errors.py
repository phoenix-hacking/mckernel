"""Actual public directory readers distinguish genuine EOF and local read errors.

All entries/handles are ordinary private HOST directory objects. Error injection
is deterministic after zero/one matching entries. Candidate-only default reads
current canonical source; historical baselines remain private. No sorted ordering, races,
actual /dev access, transactional list output or TLS errno promise is assumed.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
ROOT=Path(os.environ.get('M15_REPO',Path(__file__).resolve().parents[2]))
FIXTURES=HERE/'fixtures/m15-directory-read-errors'


def function(source,marker):
 start=source.index(marker);brace=source.index('{',start);depth=0
 for offset in range(brace,len(source)):
  if source[offset]=='{':depth+=1
  elif source[offset]=='}':
   depth-=1
   if depth==0:return source[start:offset+1]+'\n'
 raise ValueError('Unterminated actual source function: '+marker)


def generate_units(c,rust,observer,template):
 c_blocks={name:function(c,marker) for name,marker in [('readable','static int ihklib_device_readable('),('count','int ihk_get_num_os_instances('),('list','int ihk_get_os_instances(')]}
 aliases='\n#define dprintf(...) ((void)0)\n#define dprintk(...) ((void)0)\n#define dnprintk(...) ((void)0)\n'+''.join('#define '+name+' '+target+'\n' for name,target in [('geteuid','observation_geteuid'),('access','observation_access'),('opendir','observation_opendir'),('readdir','observation_readdir'),('closedir','observation_closedir')])
 c_unit=observer+aliases+''.join(c_blocks.values())+'\nint main(int argc,char **argv){assert(argc==2);return observation_run(0,ihk_get_num_os_instances,ihk_get_os_instances,argv[1]);}\n'
 start=rust.index('#[repr(C)]\nstruct Dirent');end=rust.index('const _: ()',start)
 values={'__DIRENT__':rust[start:end],'__ERRNO__':function(rust,'unsafe fn errno_negative('),'__READABLE__':function(rust,'unsafe fn readable('),'__COUNT__':function(rust,'#[no_mangle]\npub unsafe extern "C" fn ihk_get_num_os_instances('),'__LIST__':function(rust,'#[no_mangle]\npub unsafe extern "C" fn ihk_get_os_instances(')}
 rust_unit=template
 for marker,body in values.items():rust_unit=rust_unit.replace(marker,body)
 if any(marker in rust_unit for marker in values):raise ValueError('Unresolved source marker')
 return {'observer.c':observer,'c-candidate.c':c_unit,'rust-candidate.rs':rust_unit},{'C':c_blocks,'Rust':values}


def profile(label,payload,receipt):
 return ['/usr/bin/taskset','-c','7','/usr/bin/timeout','--signal=TERM','--kill-after=2s','58s','/usr/bin/prlimit','--as=1073741824:1073741824','--cpu=45:45','--fsize=67108864:67108864','--core=0:0','--','/usr/bin/time','-v','-o',str(receipt/(label+'.metrics'))]+payload


def command_plan(work,cc,rustc,includes):
 return [('c-candidate-compile',[cc,'-std=gnu11','-Wall','-Werror',*includes,str(work/'c-candidate.c'),'-o',str(work/'c-candidate')]),('c-candidate-run',[str(work/'c-candidate'),str(work/'directory')]),('observer-compile',[cc,'-std=gnu11','-Wall','-Wextra','-Werror',*includes,'-c',str(work/'observer.c'),'-o',str(work/'observer.o')]),('rust-candidate-compile',[rustc,'--edition=2021','-Dwarnings',str(work/'rust-candidate.rs'),'-C','link-arg='+str(work/'observer.o'),'-o',str(work/'rust-candidate')]),('rust-candidate-run',[str(work/'rust-candidate'),str(work/'directory')])]



class M15DirectoryReadErrorTests(unittest.TestCase):
 def test_actual_count_and_list_read_errors(self):
  paths=[ROOT/'ihk/linux/user/ihklib.c',ROOT/'ihk/linux/user/rust/whole70/ihklib_memory_os_and_os_assigned.rs']
  for compiler in ('CC','RUSTC'):
   path=Path(os.environ[compiler]);self.assertTrue(path.is_absolute() and path.is_file() and os.access(path,os.X_OK),compiler+' must select an explicit executable')
  units,blocks=generate_units(*(path.read_text() for path in paths),(FIXTURES/'observations.c.in').read_text(),(FIXTURES/'rust.rs.in').read_text())
  binding={'sources':{str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},'generated_unit_sha256':{n:hashlib.sha256(t.encode()).hexdigest() for n,t in units.items()}}
  if 'M15_DIRECTORY_RECEIPT_DIR' in os.environ:receipt=Path(os.environ['M15_DIRECTORY_RECEIPT_DIR'])
  else:
   temporary=tempfile.TemporaryDirectory(prefix='m15-directory-read-errors-');self.addCleanup(temporary.cleanup);receipt=Path(temporary.name)
  receipt.mkdir(parents=True,exist_ok=True);work=receipt/'work';work.mkdir(exist_ok=True)
  for name,text in units.items():(work/name).write_text(text)
  directory=work/'directory';directory.mkdir(exist_ok=True)
  for name in ('mcos1','mcos3','notes'):
   with (directory/name).open('xb') as entry:entry.write(b'ordinary HOST entry\n')
  (receipt/'SOURCE-BINDING.json').write_text(json.dumps(binding,indent=2)+'\n')
  (receipt/'EXTRACTED-BLOCKS.json').write_text(json.dumps(blocks,indent=2)+'\n');rows=[]
  commands=command_plan(work,os.environ['CC'],os.environ['RUSTC'],['-I'+str(ROOT/'ihk/linux/include'),'-I'+str(ROOT/'ihk/linux/include/ihk/arch/x86_64')])
  languages=(os.environ['M15_DIRECTORY_LANGUAGE'],) if 'M15_DIRECTORY_LANGUAGE' in os.environ else ('c','rust')
  self.assertTrue(all(language in ('c','rust') for language in languages),'Select c or rust')
  labels={'c':('c-candidate-compile','c-candidate-run'),'rust':('observer-compile','rust-candidate-compile','rust-candidate-run')};plan=dict(commands)
  for label,payload in [(label,plan[label]) for language in languages for label in labels[language]]:
   argv=profile(label,payload,receipt);environment=os.environ.copy();environment.pop('M15_DIRECTORY_BASELINE_ONLY',None)
   with (receipt/(label+'.stdout')).open('xb') as stdout,(receipt/(label+'.stderr')).open('xb') as stderr:
    child=subprocess.Popen(argv,cwd=ROOT,env=environment,stdout=stdout,stderr=stderr)
    try:start=Path('/proc/'+str(child.pid)+'/stat').read_text().rsplit(')',1)[1].split()[19]
    except FileNotFoundError:start=None
    finally:status=child.wait()
   rows.append({'label':label,'argv':argv,'pid':child.pid,'proc_start_ticks':start,'returncode':status,'direct_wait_joined':True});(receipt/'COMMANDS.json').write_text(json.dumps(rows,indent=2)+'\n')
   (receipt/'ARTIFACTS.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in work.iterdir() if p.is_file()},indent=2)+'\n')
   stdout=(receipt/(label+'.stdout')).read_text();stderr=(receipt/(label+'.stderr')).read_text();self.assertEqual(status,0,label+'\n'+stdout+stderr);self.assertEqual(stderr,'',label+' unexpected diagnostics')
   if label.endswith('-run'):
    self.assertEqual(stdout.count('COUNT fault-after='),3);self.assertEqual(stdout.count('LIST fault-after='),4)
    summary='candidate directory cases=7 read-errors-EIO=5 normal-EOF-order=2 partial-slots-permitted each-read-errno-cleared genuine-DIR-close-once\n'
    self.assertTrue(stdout.endswith(summary))
  (receipt/'RESULT.json').write_text(json.dumps({'status':'PASS_CANDIDATE_PUBLIC_DIRECTORY_READ_ERRORS','cases_per_language':7,'languages':list(languages),'all_direct_waits_joined':True,'commands':rows,'source_binding':binding,'actual_device_backend_native_or_creationrollback_executed':False},indent=2)+'\n')


if __name__=='__main__':unittest.main()
