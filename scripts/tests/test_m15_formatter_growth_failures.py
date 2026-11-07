"""Candidate C and already-safe current Rust formatter realloc failure coverage.

Valid records grow exactly64→128→256; genuine success runs first, followed by
ordinary injected failures at the first and second realloc. The failed realloc
seam keeps the old allocation owned; only the actual helper may free it.
No old C failed-realloc baseline or old parser/scratch suite is executed.
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
FIXTURES=HERE/'fixtures/m15-formatter-growth'


def function(source,marker):
 start=source.index(marker);brace=source.index('{',start);depth=0
 for offset in range(brace,len(source)):
  if source[offset]=='{':depth+=1
  elif source[offset]=='}':
   depth-=1
   if depth==0:return source[start:offset+1]+'\n'
 raise ValueError('Unterminated actual source function: '+marker)


def generate_units(c,shared,ikc,observer,template):
 declaration=re.search(r'^int loglevel = [^;]+;',c,re.M).group(0);observer=observer.replace('__LOGLEVEL_DECL__',declaration)
 start=c.index('#define eprintf(');error_macro=c[start:c.index('\n\n',start)]+'\n'
 markers=['static int snprintf_realloc(','static char *cpu_array2str(','char *cpu_req2str(','static char *mem_array2str(','char *mem_req2str(','char *ikc_req2str('];c_blocks={marker:function(c,marker) for marker in markers}
 aliases='\n#define dprintf(...) ((void)0)\n'+''.join('#define '+name+' '+target+'\n' for name,target in [('malloc','observation_malloc'),('calloc','observation_calloc'),('realloc','observation_realloc'),('free','observation_free'),('snprintf','observation_snprintf'),('vsnprintf','observation_vsnprintf')])
 c_unit=observer+aliases+error_macro+''.join(c_blocks.values())+'\nint main(void){return observation_run(cpu_req2str,mem_req2str,ikc_req2str);}\n'
 start=shared.index('#[repr(C)]');end=shared.index('unsafe extern "C"',start);ikc_start=ikc.index('#[repr(C)]');ikc_end=ikc.index('unsafe extern "C"',ikc_start)
 values={'__CPU_MEMORY_TYPES__':shared[start:end],'__APPEND__':function(shared,'pub(super) unsafe fn append('),'__ZERO_MEM__':function(shared,'unsafe fn zero_mem('),'__QUERY_STRING__':function(shared,'unsafe fn query_string('),'__LOG__':function(shared,'pub(super) unsafe fn log<'),'__CPU_PUBLIC__':function(shared,'#[no_mangle]\npub unsafe extern "C" fn cpu_req2str('),'__MEMORY_PUBLIC__':function(shared,'#[no_mangle]\npub unsafe extern "C" fn mem_req2str('),'__IKC_TYPE__':ikc[ikc_start:ikc_end],'__ALLOCATION_ERROR__':function(ikc,'unsafe fn allocation_error('),'__IKC_PUBLIC__':function(ikc,'#[no_mangle]\npub unsafe extern "C" fn ikc_req2str(')}
 rust_unit=template
 for marker,body in values.items():rust_unit=rust_unit.replace(marker,body)
 if any(marker in rust_unit for marker in values):raise ValueError('Unresolved source marker')
 return {'observer.c':observer,'c-candidate.c':c_unit,'rust-current.rs':rust_unit},{'C':c_blocks,'Rust':values}


def profile(label,payload,receipt):
 return ['/usr/bin/taskset','-c','7','/usr/bin/timeout','--signal=TERM','--kill-after=2s','58s','/usr/bin/prlimit','--as=1073741824:1073741824','--cpu=45:45','--fsize=67108864:67108864','--core=0:0','--','/usr/bin/time','-v','-o',str(receipt/(label+'.metrics'))]+payload


def command_plan(work,cc,rustc,includes):
 return [('observer-compile',[cc,'-std=gnu11','-Wall','-Wextra','-Werror',*includes,'-c',str(work/'observer.c'),'-o',str(work/'observer.o')]),('c-candidate-compile',[cc,'-std=gnu11','-Wall','-Werror',*includes,str(work/'c-candidate.c'),'-o',str(work/'c-candidate')]),('rust-current-compile',[rustc,'--edition=2021','-Dwarnings',str(work/'rust-current.rs'),'-C','link-arg='+str(work/'observer.o'),'-o',str(work/'rust-current')]),('c-candidate-run',[str(work/'c-candidate')]),('rust-current-run',[str(work/'rust-current')])]


class M15FormatterGrowthFailureTests(unittest.TestCase):
 def test_actual_three_public_formatters_growth_failures(self):
  self.assertTrue(os.environ.get('CC') and os.environ.get('RUSTC'),'Set explicit actual CC and RUSTC paths')
  defaults=('ihk/linux/user/ihklib.c','ihk/linux/user/rust/whole70/ihklib_cli_parsers_ikc_shared.rs','ihk/linux/user/rust/whole70/ihklib_ikc.rs')
  paths=[Path(os.environ.get(name,str(ROOT/default))) for name,default in zip(('M15_GROWTH_C_CANDIDATE','M15_GROWTH_RUST_SHARED','M15_GROWTH_RUST_IKC'),defaults)]
  units,blocks=generate_units(*(path.read_text() for path in paths),(FIXTURES/'observations.c.in').read_text(),(FIXTURES/'rust.rs.in').read_text())
  frozen={'source_sha256':{str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},'generated_unit_sha256':{name:hashlib.sha256(text.encode()).hexdigest() for name,text in units.items()}}
  if os.environ.get('M15_GROWTH_EXPECTED_PROOF'):
   expected=json.loads(Path(os.environ['M15_GROWTH_EXPECTED_PROOF']).read_text());self.assertEqual(frozen['generated_unit_sha256'],expected['generated_unit_sha256'])
  if os.environ.get('M15_GROWTH_RECEIPT_DIR'):receipt=Path(os.environ['M15_GROWTH_RECEIPT_DIR'])
  else:
   temporary=tempfile.TemporaryDirectory(prefix='m15-formatter-growth-');self.addCleanup(temporary.cleanup);receipt=Path(temporary.name)
  receipt.mkdir(parents=True,exist_ok=True);work=receipt/'work';work.mkdir(exist_ok=True)
  (receipt/'SOURCE-BINDING.json').write_text(json.dumps(frozen,indent=2)+'\n')
  for name,text in units.items():(work/name).write_text(text)
  (receipt/'EXTRACTED-BLOCKS.json').write_text(json.dumps(blocks,indent=2)+'\n');rows=[]
  for label,payload in command_plan(work,os.environ['CC'],os.environ['RUSTC'],['-I'+str(ROOT/'ihk/linux/include'),'-I'+str(ROOT/'ihk/linux/include/ihk/arch/x86_64')]):
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
    self.assertEqual(stdout.count('CASE formatter='),9)
    self.assertTrue(stdout.endswith('candidate growth cases=9 exact-two-growth-successes=3 realloc-failures-NULL=6 failed-old-owner-freed-once=6 all-output-and-scratch-owners-released\n'))
  (receipt/'RESULT.json').write_text(json.dumps({'status':'PASS_THREE_PUBLIC_FORMATTERS_GENUINE_GROWTH_AND_DEFINED_REALLOC_FAILURE_SEAMS','C_candidate_cases':9,'Rust_current_cases':9,'old_C_failed_realloc_executed':False,'all_direct_waits_joined':True,'commands':rows,'source_binding':frozen,'backend_device_native_or_old_suite_executed':False},indent=2)+'\n')


if __name__=='__main__':unittest.main()
