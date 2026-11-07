"""Defined IKC formatter scratch failures with real libc ownership observation.

Candidate-only default reads current selected C/Rust and shared helper sources.
Only valid three-entry requests and ordinary pre-format allocation failures are
used. Historical baseline observations remain private evidence.
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
FIXTURES=HERE/'fixtures/m15-ikc-formatter-allocations'


def function(source,marker):
 start=source.index(marker);brace=source.index('{',start);depth=0
 for offset in range(brace,len(source)):
  if source[offset]=='{':depth+=1
  elif source[offset]=='}':
   depth-=1
   if depth==0:return source[start:offset+1]+'\n'
 raise ValueError('Unterminated actual source function: '+marker)


def generate_units(c,rust,shared,observer,template):
 declaration=re.search(r'^int loglevel = [^;]+;',c,re.M).group(0);observer=observer.replace('__LOGLEVEL_DECL__',declaration)
 start=c.index('#define eprintf(');error_macro=c[start:c.index('\n\n',start)]+'\n'
 helper=function(c,'static int snprintf_realloc(');formatter=function(c,'char *ikc_req2str(')
 aliases='\n#define dprintf(...) ((void)0)\n'+''.join('#define '+name+' '+target+'\n' for name,target in [('malloc','observation_malloc'),('calloc','observation_calloc'),('free','observation_free'),('realloc','observation_realloc'),('vsnprintf','observation_vsnprintf'),('snprintf','observation_snprintf')])
 c_unit=observer+aliases+error_macro+helper+formatter+'\nint main(void){return observation_run(0,ikc_req2str);}\n'
 start=rust.index('#[repr(C)]');end=rust.index('unsafe extern "C"',start)
 values={'__REQUEST_TYPE__':rust[start:end],'__APPEND__':function(shared,'pub(super) unsafe fn append('),'__LOG__':function(shared,'pub(super) unsafe fn log<'),'__ALLOCATION_ERROR__':function(rust,'unsafe fn allocation_error('),'__FORMATTER__':function(rust,'#[no_mangle]\npub unsafe extern "C" fn ikc_req2str(')}
 values['__ERRNO_DECL__']=' fn __errno_location()->*mut c_int;' if '__errno_location' in values['__FORMATTER__'] else ''
 rust_unit=template
 for marker,body in values.items():rust_unit=rust_unit.replace(marker,body)
 if any(marker in rust_unit for marker in values):raise ValueError('Unresolved source marker')
 return {'observer.c':observer,'c-candidate.c':c_unit,'rust-candidate.rs':rust_unit},{'C':{'error_macro':error_macro,'snprintf_realloc':helper,'ikc_req2str':formatter},'Rust':values}


def profile(label,payload,receipt):
 return ['/usr/bin/taskset','-c','6','/usr/bin/timeout','--signal=TERM','--kill-after=2s','58s','/usr/bin/prlimit','--as=1073741824:1073741824','--cpu=45:45','--fsize=67108864:67108864','--core=0:0','--','/usr/bin/time','-v','-o',str(receipt/(label+'.metrics'))]+payload


def command_plan(work,cc,rustc,includes):
 return [('c-candidate-compile',[cc,'-std=gnu11','-Wall','-Werror',*includes,str(work/'c-candidate.c'),'-o',str(work/'c-candidate')]),('c-candidate-run',[str(work/'c-candidate')]),('observer-compile',[cc,'-std=gnu11','-Wall','-Wextra','-Werror',*includes,'-c',str(work/'observer.c'),'-o',str(work/'observer.o')]),('rust-candidate-compile',[rustc,'--edition=2021','-Dwarnings',str(work/'rust-candidate.rs'),'-C','link-arg='+str(work/'observer.o'),'-o',str(work/'rust-candidate')]),('rust-candidate-run',[str(work/'rust-candidate')])]



class M15IkcFormatterAllocationTests(unittest.TestCase):
 def test_actual_formatter_defined_failures(self):
  paths=[ROOT/'ihk/linux/user/ihklib.c',ROOT/'ihk/linux/user/rust/whole70/ihklib_ikc.rs',ROOT/'ihk/linux/user/rust/whole70/ihklib_cli_parsers_ikc_shared.rs']
  for compiler in ('CC','RUSTC'):
   path=Path(os.environ[compiler]);self.assertTrue(path.is_absolute() and path.is_file() and os.access(path,os.X_OK),compiler+' must select an explicit executable')
  units,blocks=generate_units(*(path.read_text() for path in paths),(FIXTURES/'observations.c.in').read_text(),(FIXTURES/'rust.rs.in').read_text())
  binding={'sources':{str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},'generated_unit_sha256':{n:hashlib.sha256(t.encode()).hexdigest() for n,t in units.items()}}
  if 'M15_IKC_RECEIPT_DIR' in os.environ:receipt=Path(os.environ['M15_IKC_RECEIPT_DIR'])
  else:
   temporary=tempfile.TemporaryDirectory(prefix='m15-ikc-formatter-allocations-');self.addCleanup(temporary.cleanup);receipt=Path(temporary.name)
  receipt.mkdir(parents=True,exist_ok=True);work=receipt/'work';work.mkdir(exist_ok=True)
  for name,text in units.items():(work/name).write_text(text)
  (receipt/'SOURCE-BINDING.json').write_text(json.dumps(binding,indent=2)+'\n')
  (receipt/'EXTRACTED-BLOCKS.json').write_text(json.dumps(blocks,indent=2)+'\n');rows=[]
  commands=command_plan(work,os.environ['CC'],os.environ['RUSTC'],['-I'+str(ROOT/'ihk/linux/include'),'-I'+str(ROOT/'ihk/linux/include/ihk/arch/x86_64')])
  languages=(os.environ['M15_IKC_LANGUAGE'],) if 'M15_IKC_LANGUAGE' in os.environ else ('c','rust')
  self.assertTrue(all(language in ('c','rust') for language in languages),'Select c or rust')
  labels={'c':('c-candidate-compile','c-candidate-run'),'rust':('observer-compile','rust-candidate-compile','rust-candidate-run')};plan=dict(commands)
  for label,payload in [(label,plan[label]) for language in languages for label in labels[language]]:
   argv=profile(label,payload,receipt);environment=os.environ.copy();environment.pop('M15_IKC_BASELINE_ONLY',None)
   with (receipt/(label+'.stdout')).open('xb') as stdout,(receipt/(label+'.stderr')).open('xb') as stderr:
    child=subprocess.Popen(argv,cwd=ROOT,env=environment,stdout=stdout,stderr=stderr)
    try:start=Path('/proc/'+str(child.pid)+'/stat').read_text().rsplit(')',1)[1].split()[19]
    except FileNotFoundError:start=None
    finally:status=child.wait()
   rows.append({'label':label,'argv':argv,'pid':child.pid,'proc_start_ticks':start,'returncode':status,'direct_wait_joined':True});(receipt/'COMMANDS.json').write_text(json.dumps(rows,indent=2)+'\n')
   (receipt/'ARTIFACTS.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in work.iterdir() if p.is_file()},indent=2)+'\n')
   stdout=(receipt/(label+'.stdout')).read_text();stderr=(receipt/(label+'.stderr')).read_text();self.assertEqual(status,0,label+'\n'+stdout+stderr);self.assertEqual(stderr,'',label+' unexpected diagnostics')
   if label.endswith('-run'):
    self.assertEqual(stdout.count('CASE initial-malloc-fail='),7)
    summary='candidate IKC cases=7 scratch-failures-NULL=5 initial-failure-NULL=1 correct-success=1 all-owned-freed-once live=0 realloc-calls=0\n'
    self.assertTrue(stdout.endswith(summary))
  (receipt/'RESULT.json').write_text(json.dumps({'status':'PASS_CANDIDATE_IKC_FORMATTER_FAILURE_OWNERSHIP','cases_per_language':7,'languages':list(languages),'all_direct_waits_joined':True,'commands':rows,'source_binding':binding,'reallocation_failure_device_backend_native_executed':False},indent=2)+'\n')


if __name__=='__main__':unittest.main()
