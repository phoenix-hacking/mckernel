"""Six actual C environment consumers retain borrows and release parsed owners.

Candidate-only default reads current canonical C. Historical defined baseline
observations remain private evidence; no baseline execution mode is provided.
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
FIXTURES=HERE/'fixtures/m15-public-env-consumer-lifetimes'
NAMES=('ihk_reserve_cpu_str','ihk_reserve_mem_conf_str','ihk_reserve_mem_str','ihk_os_assign_cpu_str','ihk_os_set_ikc_map_str','ihk_os_kargs_str')


def function(source,marker):
 start=source.index(marker);brace=source.index('{',start);depth=0
 for offset in range(brace,len(source)):
  if source[offset]=='{':depth+=1
  elif source[offset]=='}':
   depth-=1
   if depth==0:return source[start:offset+1]+'\n'
 raise ValueError('Unterminated actual C function: '+marker)


def generate_c_unit(source,observer):
 blocks={'parse_env':function(source,'int parse_env(')}
 blocks['free_parsed_env']=function(source,'static void free_parsed_env(')
 start=source.index('#define RESERVE_MEM_CONF_PARSE(');macro=source[start:source.index('\n\n',start)]+'\n'
 for name in NAMES:blocks[name]=function(source,'int '+name+'(')
 callbacks=[('calloc','observation_calloc'),('strndup','observation_strndup'),('strdup','observation_strdup'),('free','observation_free'),('_ihk_reserve_cpu_str','observation_reserve_cpu'),('_ihk_reserve_mem_str','observation_reserve_mem'),('_ihk_os_assign_cpu_str','observation_assign_cpu'),('_ihk_os_set_ikc_map_str','observation_set_ikc'),('ihk_reserve_mem_conf','observation_mem_conf'),('ihk_os_kargs','observation_kargs')]
 aliases='\n#define dprintf(...) ((void)0)\n#define dprintk(...) ((void)0)\n'+''.join('#define '+name+' '+target+'\n' for name,target in callbacks)
 wrapper='\nstatic int call_kargs(int index,const char *env,int count){return ihk_os_kargs_str(index,env,count,default_kargs);}\nint main(void){Consumer consumers[]={'+','.join(NAMES[:-1])+',call_kargs};return observation_run(0,consumers);}\n'
 return observer+aliases+macro+''.join(blocks.values())+wrapper,blocks


def profile(label,payload,receipt):
 return ['/usr/bin/taskset','-c','6','/usr/bin/timeout','--signal=TERM','--kill-after=2s','58s','/usr/bin/prlimit','--as=1073741824:1073741824','--cpu=45:45','--fsize=67108864:67108864','--core=0:0','--','/usr/bin/time','-v','-o',str(receipt/(label+'.metrics'))]+payload


def command_plan(work,cc,includes):
 return [('candidate-compile',[cc,'-std=gnu11','-Wall','-Werror',*includes,str(work/'candidate.c'),'-o',str(work/'candidate')]),('candidate-run',[str(work/'candidate')])]



class M15PublicEnvConsumerLifetimeTests(unittest.TestCase):
 def test_six_actual_C_consumer_owner_lifetimes(self):
  source=ROOT/'ihk/linux/user/ihklib.c';observer_path=FIXTURES/'observations.c.in';compiler=Path(os.environ['CC'])
  self.assertTrue(compiler.is_absolute() and compiler.is_file() and os.access(compiler,os.X_OK),'CC must select an explicit executable')
  unit,blocks=generate_c_unit(source.read_text(),observer_path.read_text())
  binding={'sources':{str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in (source,observer_path)},'candidate_unit_sha256':hashlib.sha256(unit.encode()).hexdigest()}
  if 'M15_ENV_CONSUMER_RECEIPT_DIR' in os.environ:receipt=Path(os.environ['M15_ENV_CONSUMER_RECEIPT_DIR'])
  else:
   temporary=tempfile.TemporaryDirectory(prefix='m15-public-env-consumer-lifetimes-');self.addCleanup(temporary.cleanup);receipt=Path(temporary.name)
  receipt.mkdir(parents=True,exist_ok=True);work=receipt/'work';work.mkdir(exist_ok=True);(work/'candidate.c').write_text(unit)
  (receipt/'SOURCE-BINDING.json').write_text(json.dumps(binding,indent=2)+'\n')
  (receipt/'EXTRACTED-BLOCKS.json').write_text(json.dumps(blocks,indent=2)+'\n')
  rows=[]
  for label,payload in command_plan(work,os.environ['CC'],['-I'+str(ROOT/'ihk/linux/include'),'-I'+str(ROOT/'ihk/linux/include/ihk/arch/x86_64')]):
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
    self.assertEqual(stdout.count('CASE function='),24)
    expected='candidate public-consumers cases=24 providers-borrow-live=13 after-return-cleanup=18 parse-failure-no-double-free=6 borrowed-default-not-freed=1 live=0\n'
    self.assertTrue(stdout.endswith(expected))
  (receipt/'RESULT.json').write_text(json.dumps({'status':'PASS_SIX_C_CONSUMER_CANDIDATE_LIFETIMES','candidate_cases':24,'all_direct_waits_joined':True,'commands':rows,'source_binding':binding,'actual_IHK_device_backend_native_or_Rust_execution':False},indent=2)+'\n')


if __name__=='__main__':unittest.main()
