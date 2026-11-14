"""Exact creation rollback tails consume only successful complete enumerations.

Zeroed/partially written baseline arrays are valid initialized storage, and every
per-OS action is a local synchronous observation, never an actual lifecycle call.
Primary/index/message are MODELED context around the actual rollback tail.
Current creation prefixes are captured as source-only bindings; actual upstream
creation/publication/diagnostic behavior is not executed or claimed.
"""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
ROOT=Path(os.environ.get('M15_REPO',Path(__file__).resolve().parents[2]))
FIXTURES=HERE/'fixtures/m15-create-list-errors'


def function(source,marker):
 start=source.index(marker);brace=source.index('{',start);depth=0
 for offset in range(brace,len(source)):
  if source[offset]=='{':depth+=1
  elif source[offset]=='}':
   depth-=1
   if depth==0:return source[start:offset+1]+'\n'
 raise ValueError('Unterminated actual source function: '+marker)


def slices(source,language):
 marker='int ihk_create_os_str(' if language=='c' else '#[no_mangle]\npub unsafe extern "C" fn ihk_create_os_str('
 body=function(source,marker);start=body.index('\t/* roll back */') if language=='c' else body.index('    if result != 0 {\n        // Original rollback')
 return body[:start],body[start:]


def generate_units(c,rust,observer,template):
 c_prefix,c_tail=slices(c,'c')
 aliases='\n'+''.join('#define '+name+' '+target+'\n' for name,target in [('calloc','observation_calloc'),('free','observation_free'),('ihk_get_num_os_instances','observation_count'),('ihk_get_os_instances','observation_list'),('os_release_cpu_all','observation_os_cpu'),('ihk_os_release_mem','observation_os_mem'),('ihk_destroy_os','observation_destroy'),('release_cpu_all','observation_device_cpu'),('ihk_release_mem','observation_device_mem')])
 wrapper='\nstatic int rollback(int dev_index,int primary,int *_os_index,char *err_msg){int ret=primary;int i;int os_index=*_os_index;(void)os_index;(void)err_msg;struct ihk_mem_chunk mem_chunks[1]={{.size=~0UL,.numa_node_number=0}};\n'
 c_unit=observer+aliases+wrapper+c_tail+'\nint main(void){return observation_run(0,rollback);}\n'
 rust_prefix,rust_tail=slices(rust,'rust')
 return {'observer.c':observer,'c-candidate.c':c_unit,'rust-candidate.rs':template.replace('__ROLLBACK__',rust_tail)},{'C':{'current_creation_prefix_source_only':c_prefix,'actual_rollback_tail':c_tail},'Rust':{'current_creation_prefix_source_only':rust_prefix,'actual_rollback_tail':rust_tail}}


def profile(label,payload,receipt):
 return ['/usr/bin/taskset','-c','7','/usr/bin/timeout','--signal=TERM','--kill-after=2s','58s','/usr/bin/prlimit','--as=1073741824:1073741824','--cpu=45:45','--fsize=67108864:67108864','--core=0:0','--','/usr/bin/time','-v','-o',str(receipt/(label+'.metrics'))]+payload


def command_plan(work,cc,rustc,includes):
 return [('c-candidate-compile',[cc,'-std=gnu11','-Wall','-Werror',*includes,str(work/'c-candidate.c'),'-o',str(work/'c-candidate')]),('c-candidate-run',[str(work/'c-candidate')]),('observer-compile',[cc,'-std=gnu11','-Wall','-Wextra','-Werror',*includes,'-c',str(work/'observer.c'),'-o',str(work/'observer.o')]),('rust-candidate-compile',[rustc,'--edition=2021','-Dwarnings',str(work/'rust-candidate.rs'),'-C','link-arg='+str(work/'observer.o'),'-o',str(work/'rust-candidate')]),('rust-candidate-run',[str(work/'rust-candidate')])]



class M15CreateListErrorTests(unittest.TestCase):
 def test_actual_rollback_list_status_gate(self):
  paths=[ROOT/'ihk/linux/user/ihklib.c',ROOT/'ihk/linux/user/rust/whole70/ihklib_create_os_environment.rs']
  for compiler in ('CC','RUSTC'):
   path=Path(os.environ[compiler]);self.assertTrue(path.is_absolute() and path.is_file() and os.access(path,os.X_OK),compiler+' must select an explicit executable')
  units,blocks=generate_units(*(path.read_text() for path in paths),(FIXTURES/'observations.c.in').read_text(),(FIXTURES/'rust.rs.in').read_text())
  binding={'sources':{str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},'current_creation_prefix_source_only_sha256':{language:hashlib.sha256(group['current_creation_prefix_source_only'].encode()).hexdigest() for language,group in blocks.items()},'generated_unit_sha256':{n:hashlib.sha256(t.encode()).hexdigest() for n,t in units.items()},'context_scope':'MODELED primary/index/message context; actual upstream creation not executed'}
  if 'M15_CREATE_LIST_RECEIPT_DIR' in os.environ:receipt=Path(os.environ['M15_CREATE_LIST_RECEIPT_DIR'])
  else:
   temporary=tempfile.TemporaryDirectory(prefix='m15-create-list-errors-');self.addCleanup(temporary.cleanup);receipt=Path(temporary.name)
  receipt.mkdir(parents=True,exist_ok=True);work=receipt/'work';work.mkdir(exist_ok=True)
  for name,text in units.items():(work/name).write_text(text)
  (receipt/'SOURCE-BINDING.json').write_text(json.dumps(binding,indent=2)+'\n')
  (receipt/'EXTRACTED-BLOCKS.json').write_text(json.dumps(blocks,indent=2)+'\n');rows=[]
  commands=command_plan(work,os.environ['CC'],os.environ['RUSTC'],['-I'+str(ROOT/'ihk/linux/include'),'-I'+str(ROOT/'ihk/linux/include/ihk/arch/x86_64')])
  languages=(os.environ['M15_CREATE_LIST_LANGUAGE'],) if 'M15_CREATE_LIST_LANGUAGE' in os.environ else ('c','rust')
  self.assertTrue(all(language in ('c','rust') for language in languages),'Select c or rust')
  labels={'c':('c-candidate-compile','c-candidate-run'),'rust':('observer-compile','rust-candidate-compile','rust-candidate-run')};plan=dict(commands)
  for label,payload in [(label,plan[label]) for language in languages for label in labels[language]]:
   argv=profile(label,payload,receipt);environment=os.environ.copy();environment.pop('M15_CREATE_LIST_BASELINE_ONLY',None)
   with (receipt/(label+'.stdout')).open('xb') as stdout,(receipt/(label+'.stderr')).open('xb') as stderr:
    child=subprocess.Popen(argv,cwd=ROOT,env=environment,stdout=stdout,stderr=stderr)
    try:start=Path('/proc/'+str(child.pid)+'/stat').read_text().rsplit(')',1)[1].split()[19]
    except FileNotFoundError:start=None
    finally:status=child.wait()
   rows.append({'label':label,'argv':argv,'pid':child.pid,'proc_start_ticks':start,'returncode':status,'direct_wait_joined':True});(receipt/'COMMANDS.json').write_text(json.dumps(rows,indent=2)+'\n')
   (receipt/'ARTIFACTS.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in work.iterdir() if p.is_file()},indent=2)+'\n')
   stdout=(receipt/(label+'.stdout')).read_text();stderr=(receipt/(label+'.stderr')).read_text();self.assertEqual(status,0,label+'\n'+stdout+stderr);self.assertEqual(stderr,'',label+' unexpected diagnostics')
   if label.endswith('-run'):
    self.assertEqual(stdout.count('CASE list='),3)
    summary='candidate rollback-list cases=3 failed-lists-skipped=2 complete-broad-control=1 list-freed-once primary-context-and-final-release-order-preserved\n'
    self.assertTrue(stdout.endswith(summary))
  (receipt/'RESULT.json').write_text(json.dumps({'status':'PASS_CANDIDATE_CREATION_ROLLBACK_LIST_GUARD','cases_per_language':3,'languages':list(languages),'context_scope':'MODELED primary/index/message; no actual upstream creation runtime','all_direct_waits_joined':True,'commands':rows,'source_binding':binding,'actual_lifecycle_device_native_or_creation_prefix_executed':False},indent=2)+'\n')


if __name__=='__main__':unittest.main()
