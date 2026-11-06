"""Candidate-only ordinary strdup failures in the distinct private create parser.

Actual complete create function and its allocation-owning helpers are extracted.
No predecessor failed-pointer execution or real IHK lifecycle provider is used.
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
FIXTURES=HERE/'fixtures/m15-create-entry-allocations'


def function(source,marker):
 start=source.index(marker);brace=source.index('{',start);depth=0
 for offset in range(brace,len(source)):
  if source[offset]=='{':depth+=1
  elif source[offset]=='}':
   depth-=1
   if depth==0:return source[start:offset+1]+'\n'
 raise ValueError('Unterminated actual source function: '+marker)


def generate_c_unit(c,observer):
 markers=['static int os_assign_cpu_all(','static int os_assign_mem_all(','static int os_release_cpu_all(','static int release_cpu_all(','int ihk_create_os_str(']
 c_blocks={marker:function(c,marker) for marker in markers}
 start=c.index('#define RESERVE_MEM_CONF_PARSE(');macro=c[start:c.index('\n\n',start)]+'\n'
 callbacks=[('calloc','observation_calloc'),('strdup','observation_strdup'),('strndup','observation_strndup'),('free','observation_free'),('ihk_get_num_reserved_cpus','observation_cpu_count'),('ihk_get_num_reserved_mem_chunks','observation_mem_count'),('ihk_query_cpu','observation_query_cpu'),('ihk_query_mem','observation_query_mem'),('ihk_release_cpu','observation_release_cpu'),('ihk_release_mem','observation_release_mem'),('ihk_create_os','observation_create'),('ihk_get_num_os_instances','observation_os_count'),('ihk_get_os_instances','observation_list'),('ihk_destroy_os','observation_destroy'),('ihk_os_assign_cpu','observation_assign_cpu'),('ihk_os_assign_mem','observation_assign_mem'),('ihk_os_get_num_assigned_cpus','observation_assigned_cpu_count'),('ihk_os_query_cpu','observation_query_assigned_cpu'),('ihk_os_release_cpu','observation_release_assigned_cpu'),('ihk_os_release_mem','observation_release_assigned_mem'),('ihk_reserve_mem_conf','observation_reserve_conf'),('_ihk_reserve_cpu_str','observation_raw'),('_ihk_reserve_mem_str','observation_raw'),('_ihk_os_set_ikc_map_str','observation_raw'),('ihk_os_load','observation_load'),('ihk_os_kargs','observation_kargs')]
 aliases='\n#define dprintf(...) ((void)0)\n#define dprintk(...) ((void)0)\n'+''.join('#define '+name+' '+target+'\n' for name,target in callbacks)
 c_unit=observer+aliases+macro+''.join(c_blocks.values())+'\nint main(void){return observation_run(ihk_create_os_str);}\n'
 return c_unit,c_blocks


def generate_units(c,rust,origins,observer,template):
 c_unit,c_blocks=generate_c_unit(c,observer)
 helpers_start=rust.index('unsafe fn cpu_all(');helpers_end=rust.index('const CONFIG_KEYS:',helpers_start);config_start=helpers_end;config_end=rust.index('/// Perform the original',config_start)
 values={'__ORIGINS__':origins,'__ERROR__':function(rust,'unsafe fn error('),'__HELPERS__':rust[helpers_start:helpers_end],'__CONFIG_AND_IS__':rust[config_start:config_end],'__CREATE__':function(rust,'#[no_mangle]\npub unsafe extern "C" fn ihk_create_os_str(')}
 rust_unit=template
 for marker,body in values.items():rust_unit=rust_unit.replace(marker,body)
 if any(marker in rust_unit for marker in values):raise ValueError('Unresolved source marker')
 return {'observer.c':observer,'c-candidate.c':c_unit,'rust-candidate.rs':rust_unit},{'C':c_blocks,'Rust':values}


def profile(label,payload,receipt):
 return ['/usr/bin/taskset','-c','6','/usr/bin/timeout','--signal=TERM','--kill-after=2s','58s','/usr/bin/prlimit','--as=1073741824:1073741824','--cpu=45:45','--fsize=67108864:67108864','--core=0:0','--','/usr/bin/time','-v','-o',str(receipt/(label+'.metrics'))]+payload


def command_plan(work,cc,rustc,includes):
 return [('observer-compile',[cc,'-std=gnu11','-Wall','-Wextra','-Werror',*includes,'-c',str(work/'observer.c'),'-o',str(work/'observer.o')]),('c-candidate-compile',[cc,'-std=gnu11','-Wall','-Werror',*includes,str(work/'c-candidate.c'),'-o',str(work/'c-candidate')]),('rust-candidate-compile',[rustc,'--edition=2021','-Dwarnings',str(work/'rust-candidate.rs'),'-C','link-arg='+str(work/'observer.o'),'-o',str(work/'rust-candidate')]),('c-candidate-run',[str(work/'c-candidate')]),('rust-candidate-run',[str(work/'rust-candidate')])]


class M15CreateEntryAllocationTests(unittest.TestCase):
 def test_private_create_entry_allocation_failures(self):
  operation=os.environ.get('M15_CREATE_ENTRY_OPERATION_MODE')=='1'
  sources=[Path(os.environ['M15_CREATE_ENTRY_C_SOURCE']) if operation else ROOT/'ihk/linux/user/ihklib.c',Path(os.environ['M15_CREATE_ENTRY_RUST_SOURCE']) if operation else ROOT/'ihk/linux/user/rust/whole70/ihklib_create_os_environment.rs',Path(os.environ['M15_CREATE_ENTRY_ORIGINS'])]
  for compiler in ('CC','RUSTC'):
   path=Path(os.environ[compiler]);self.assertTrue(path.is_absolute() and path.is_file() and os.access(path,os.X_OK),compiler+' must select an explicit executable')
  units,blocks=generate_units(*(path.read_text() for path in sources),(FIXTURES/'observations.c.in').read_text(),(FIXTURES/'rust.rs.in').read_text())
  binding={'sources':{str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},'generated_unit_sha256':{n:hashlib.sha256(t.encode()).hexdigest() for n,t in units.items()}}
  if operation:
   frozen=json.loads(Path(os.environ['M15_CREATE_ENTRY_FROZEN_PROOF']).read_text());self.assertEqual(binding['generated_unit_sha256'],frozen['generated_unit_sha256'])
  if 'M15_CREATE_ENTRY_RECEIPT_DIR' in os.environ:receipt=Path(os.environ['M15_CREATE_ENTRY_RECEIPT_DIR'])
  else:
   temporary=tempfile.TemporaryDirectory(prefix='m15-create-entry-allocations-');self.addCleanup(temporary.cleanup);receipt=Path(temporary.name)
  receipt.mkdir(parents=True,exist_ok=True);work=receipt/'work';work.mkdir(exist_ok=True)
  for name,text in units.items():(work/name).write_text(text)
  (receipt/'SOURCE-BINDING.json').write_text(json.dumps(binding,indent=2)+'\n')
  (receipt/'EXTRACTED-BLOCKS.json').write_text(json.dumps(blocks,indent=2)+'\n')
  commands=command_plan(work,os.environ['CC'],os.environ['RUSTC'],['-I'+str(ROOT/'ihk/linux/include'),'-I'+str(ROOT/'ihk/linux/include/ihk/arch/x86_64')]);rows=[]
  languages=(os.environ['M15_CREATE_ENTRY_LANGUAGE'],) if 'M15_CREATE_ENTRY_LANGUAGE' in os.environ else ('c','rust')
  self.assertTrue(all(language in ('c','rust') for language in languages),'Select c or rust')
  labels={'c':('c-candidate-compile','c-candidate-run'),'rust':('observer-compile','rust-candidate-compile','rust-candidate-run')}
  plan=dict(commands);commands=[(label,plan[label]) for language in languages for label in labels[language]]
  for label,payload in commands:
   argv=profile(label,payload,receipt)
   with (receipt/(label+'.stdout')).open('xb') as stdout,(receipt/(label+'.stderr')).open('xb') as stderr:
    child=subprocess.Popen(argv,cwd=ROOT,stdout=stdout,stderr=stderr)
    try:start=Path('/proc/'+str(child.pid)+'/stat').read_text().rsplit(')',1)[1].split()[19]
    except FileNotFoundError:start=None
    finally:status=child.wait()
   rows.append({'label':label,'argv':argv,'pid':child.pid,'proc_start_ticks':start,'returncode':status,'direct_wait_joined':True});(receipt/'COMMANDS.json').write_text(json.dumps(rows,indent=2)+'\n')
   (receipt/'ARTIFACTS.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in work.iterdir() if p.is_file()},indent=2)+'\n')
   stdout=(receipt/(label+'.stdout')).read_text();stderr=(receipt/(label+'.stderr')).read_text();self.assertEqual(status,0,label+'\n'+stdout+stderr);self.assertEqual(stderr,'',label+' unexpected diagnostics')
   if label.endswith('-run'):
    self.assertEqual(stdout.count('CASE shape='),11)
    self.assertTrue(stdout.endswith('candidate creation-entry cases=11 duplicate-failures=8 success-controls=2 late-index-control=1 positive-broad-rollback=1 live-owned=0\n'))
  (receipt/'RESULT.json').write_text(json.dumps({'status':'PASS_CANDIDATE_PRIVATE_CREATE_ENTRY_ALLOCATION_FAILURES_ONLY','cases_per_language':11,'duplicate_failure_cases_per_language':8,'all_direct_waits_joined':True,'commands':rows,'source_binding':binding,'predecessor_failed_strdup_executed':False,'actual_IHK_backend_device_native_provider_claimed':False},indent=2)+'\n')


if __name__=='__main__':unittest.main()
