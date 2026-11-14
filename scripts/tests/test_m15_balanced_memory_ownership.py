"""Candidate-only actual balanced-memory cleanup errors and safe controls.

Requires explicit actual CC/RUSTC. Current source/fixture bindings are captured
dynamically; no historical baseline or balanced-success path executes.
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
ROOT=Path(os.environ.get('M15_REPO',str(HERE.parents[1])))
FIXTURES=HERE/'fixtures/m15-balanced-memory'

def function(source,marker):
 start=source.index(marker);brace=source.index('{',start);depth=0
 for offset in range(brace,len(source)):
  if source[offset]=='{':depth+=1
  elif source[offset]=='}':
   depth-=1
   if depth==0:return source[start:offset+1]+'\n'
 raise ValueError(marker)

def declaration(source,marker):
 body=function(source,marker);return body.rstrip()+';\n'

def generate_units(c_source,rust_source,observer,template):
 global_conf=declaration(c_source,'struct ihklib_reserve_mem_conf reserve_mem_conf =')
 observer=observer.replace('__CONF_GLOBAL__',global_conf)
 units={'observer.c':observer};blocks={}
 for mode,c,rust in (('candidate',c_source,rust_source),):
  default=declaration(c,'static const struct ihklib_reserve_mem_conf reserve_mem_conf_default =')
  macros=c[c.index('#else\n#define dnprintk(')+len('#else\n'):c.index('\n#endif',c.index('#else\n#define dnprintk('))]+'\n'
  chk=c[c.index('#define CHKANDJUMP('):c.index('\n\n',c.index('#define CHKANDJUMP('))]+'\n'
  all_macro=re.search(r'^#define IHK_SMP_MEM_ALL[^\n]*',c,re.M).group(0)+'\n'
  readable=function(c,'static int ihklib_device_readable(');reserve=function(c,'int ihk_reserve_mem(')
  aliases='\n'+''.join('#define '+a+' '+b+'\n' for a,b in [('calloc','observation_calloc'),('free','observation_free'),('access','observation_access'),('ihklib_device_open','observation_device_open'),('ioctl','observation_ioctl'),('close','observation_close'),('ihk_get_num_reserved_mem_chunks','observation_count'),('ihk_query_mem','observation_query'),('ihk_release_mem','observation_release')])
  units['c-'+mode+'.c']=observer+aliases+macros+chk+all_macro+default+readable+reserve+'\nint main(void){return observation_run(ihk_reserve_mem,'+str(int(mode=='baseline'))+');}\n'
  types=rust[rust.index('#[repr(C)]'):rust.index('// Exact selected glibc Linux x86_64 dirent ABI')]
  values={'__TYPES__':types,'__DEFAULT_CONF__':declaration(rust,'const DEFAULT_CONF:'),'__ERRNO__':function(rust,'unsafe fn errno_negative('),'__READABLE__':function(rust,'unsafe fn readable('),'__RESERVE__':function(rust,'#[no_mangle]\npub unsafe extern "C" fn ihk_reserve_mem('),'__BASELINE__':str(int(mode=='baseline'))}
  output=template
  for marker,body in values.items():output=output.replace(marker,body)
  assert not any(marker in output for marker in values)
  units['rust-'+mode+'.rs']=output;blocks[mode]={'C':{'DEBUGoff_macros':macros,'CHKANDJUMP':chk,'all_sentinel':all_macro,'default_config':default,'readable':readable,'reserve':reserve},'Rust':values}
 return units,blocks

def profile(label,payload,receipt):
 return ['/usr/bin/taskset','-c','7','/usr/bin/timeout','--signal=TERM','--kill-after=2s','58s','/usr/bin/prlimit','--as=1073741824:1073741824','--cpu=45:45','--fsize=67108864:67108864','--core=0:0','--','/usr/bin/time','-v','-o',str(receipt/(label+'.metrics'))]+payload

def command_plan(work,cc,rustc,includes):
 rows=[('observer-compile',[cc,'-std=gnu11','-DPAGE_SIZE=4096','-Wall','-Wextra','-Werror',*includes,'-c',str(work/'observer.c'),'-o',str(work/'observer.o')])]
 for mode in ('candidate',):rows.append(('c-'+mode+'-compile',[cc,'-std=gnu11','-DPAGE_SIZE=4096','-Wall','-Werror','-Wno-unused-but-set-variable',*includes,str(work/('c-'+mode+'.c')),'-o',str(work/('c-'+mode))]))
 for mode in ('candidate',):rows.append(('rust-'+mode+'-compile',[rustc,'--edition=2021','-Dwarnings',str(work/('rust-'+mode+'.rs')),'-C','link-arg='+str(work/'observer.o'),'-o',str(work/('rust-'+mode))]))
 for kind in ('c','rust'):
  for mode in ('candidate',):rows.append((kind+'-'+mode+'-run',[str(work/(kind+'-'+mode))]))
 return rows

class M15BalancedMemoryOwnershipTests(unittest.TestCase):
 def test_defined_error_exits_and_controls(self):
  self.assertTrue(os.environ.get('CC') and os.environ.get('RUSTC'),'Set explicit actual CC and RUSTC paths')
  cpath=Path(os.environ.get('M15_BALANCED_C_CANDIDATE',str(ROOT/'ihk/linux/user/ihklib.c')));rpath=Path(os.environ.get('M15_BALANCED_RUST_CANDIDATE',str(ROOT/'ihk/linux/user/rust/whole70/ihklib_memory_os_and_os_assigned.rs')))
  units,blocks=generate_units(cpath.read_text(),rpath.read_text(),(FIXTURES/'observations.c.in').read_text(),(FIXTURES/'rust.rs.in').read_text())
  frozen={'source_sha256':{str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in (cpath,rpath)},'generated_unit_sha256':{name:hashlib.sha256(text.encode()).hexdigest() for name,text in units.items()}}
  if os.environ.get('M15_BALANCED_EXPECTED_PROOF'):
   expected=json.loads(Path(os.environ['M15_BALANCED_EXPECTED_PROOF']).read_text());self.assertEqual(frozen['generated_unit_sha256'],{name:expected['generated_unit_sha256'][name] for name in units})
  if os.environ.get('M15_BALANCED_RECEIPT_DIR'):receipt=Path(os.environ['M15_BALANCED_RECEIPT_DIR'])
  else:
   temporary=tempfile.TemporaryDirectory(prefix='m15-balanced-memory-');self.addCleanup(temporary.cleanup);receipt=Path(temporary.name)
  receipt.mkdir(parents=True,exist_ok=True);work=receipt/'work';work.mkdir(exist_ok=True)
  (receipt/'SOURCE-BINDING.json').write_text(json.dumps(frozen,indent=2)+'\n')
  for name,text in units.items():(work/name).write_text(text)
  (receipt/'EXTRACTED-BLOCKS.json').write_text(json.dumps(blocks,indent=2)+'\n');rows=[]
  for label,payload in command_plan(work,os.environ['CC'],os.environ['RUSTC'],['-I'+str(ROOT/'ihk/linux/include'),'-I'+str(ROOT/'ihk/linux/include/ihk/arch/x86_64')]):
   argv=profile(label,payload,receipt)
   with (receipt/(label+'.stdout')).open('xb') as stdout,(receipt/(label+'.stderr')).open('xb') as stderr:
    child=subprocess.Popen(argv,cwd=ROOT,stdout=stdout,stderr=stderr)
    try:birth=Path('/proc/'+str(child.pid)+'/stat').read_text().rsplit(')',1)[1].split()[19]
    except FileNotFoundError:birth=None
    finally:status=child.wait()
   rows.append({'label':label,'argv':argv,'pid':child.pid,'proc_start_ticks':birth,'returncode':status,'direct_wait_joined':True});(receipt/'COMMANDS.json').write_text(json.dumps(rows,indent=2)+'\n')
   (receipt/'ARTIFACTS.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in work.iterdir() if p.is_file()},indent=2)+'\n')
   stdout=(receipt/(label+'.stdout')).read_text();stderr=(receipt/(label+'.stderr')).read_text();self.assertEqual(status,0,label+'\n'+stdout+stderr);self.assertEqual(stderr,'',label+' unexpecteddiagnostics')
   if label.endswith('-run'):
    mode='baseline' if '-baseline-' in label else 'candidate';self.assertEqual(stdout.count('CASE mode='),7);self.assertTrue(stdout.endswith('balanced-memory cases=7 mode='+mode+' defined-balanced-errors=5 controls=2 all-owners-reclaimed all-anonymous-FDs-once-closed\n'))
  (receipt/'RESULT.json').write_text(json.dumps({'status':'PASS_DEFINED_BALANCED_MEMORY_OWNERSHIP_EXITS','candidate_C_cases':7,'candidate_Rust_cases':7,'candidate_survivors':0,'all_direct_waits_joined':True,'commands':rows,'source_binding':frozen,'balanced_success_or_backend_native_executed':False},indent=2)+'\n')
if __name__=='__main__':unittest.main()
