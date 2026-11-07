"""Twelve candidate whole-main FUNCTION intr cases; no CRT/device/IRQ claim.

Requires explicit absolute CC,RUSTC,M15_INTR_CLI_CONFIG (qualified config.h) and
M15_INTR_CLI_LIBRARY (genuine qualified HOST shared project library). Current
whole sources retain their bodies; actual config/adapter/providers are reused.
Invoke only under fresh ordinary HOST aggregate admission. Fresh object imports
are validated by actual function calls before any link or runtime.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from test_m15_ihkmond_active_workers import profile

HERE=Path(__file__).resolve().parent
ROOT=Path(os.environ.get('M15_REPO',Path(__file__).resolve().parents[2]))
FIXTURES=HERE/'fixtures/m15-ihkosctl-intr'
_spec=importlib.util.spec_from_file_location('intr_cli_hook_validator',FIXTURES/'validate_hooks.py')
_validator=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_validator)
validate_hooks=_validator.validate


def generate_c_unit(source):
 headers=re.findall(r'^#include[^\n]+$',source,re.M)
 if not headers:raise ValueError('Actual C CLI headers required')
 block='''
/* Fixture ABI bindings only, after all genuine selected source headers. */
extern int observation_open(const char *, int, ...);
extern int observation_ioctl(int, unsigned long, ...);
extern int observation_close(int);
#define open observation_open
#define ioctl observation_ioctl
#define close observation_close
'''
 prelude='/* All original selected includes, before fixture macro bindings.\n * ENABLE_MEMDUMP=1 is unchanged from the qualified actual config. */\n'+'\n'.join(headers)+'\n'+block+'\n'
 return prelude+source


def generate_rust_unit(source):
 marker='#[no_mangle]pub unsafe extern "C" fn main('
 if source.count(marker)!=1:raise ValueError('One actual CLI main export required')
 source=source.replace(marker,'#[export_name="observed_main"]pub unsafe extern "C" fn main(')
 start=source.index('extern "C"{');end=source.index('\n}\n#[panic_handler]',start);declarations=source[start:end]
 for name in ('open','ioctl','close'):
  marker='fn '+name+'('
  if declarations.count(marker)!=1:raise ValueError('One actual CLI FFI declaration required: '+name)
  declarations=declarations.replace(marker,'#[link_name="observation_'+name+'"] '+marker)
 return source[:start]+declarations+source[end:]


def expected_output():
 output=''
 for shape,scalar in enumerate((0xf1,0xf2,0x2f3)):
  for fail in (0,1):output+=f'CASE shape={shape} scalar=0x{scalar:x} request=0x122a00 ioctl={-fail} raw-main={-fail} opens=1 calls=1 closes=1 EBADF=1 stderr-bytes={19 if fail else 0} fd-restored=1\n'
 return output+'intr-cli whole-main-function cases=6 baseline=0 false-successes=0 genuine-memfd-close=6 no-CRT-exit-claim=1\n'


class M15IhkosctlIntrTests(unittest.TestCase):
 def test_current_whole_main_function_intr_candidates(self):
  selected={name:Path(os.environ[name]) for name in ('CC','RUSTC','M15_INTR_CLI_CONFIG','M15_INTR_CLI_LIBRARY')}
  for name,path in selected.items():
   self.assertTrue(path.is_absolute() and path.is_file(),name+' requires an explicit absolute actual file')
   if name in ('CC','RUSTC'):self.assertTrue(os.access(path,os.X_OK))
  config=selected['M15_INTR_CLI_CONFIG'];library=selected['M15_INTR_CLI_LIBRARY'];self.assertEqual(config.name,'config.h')
  self.assertRegex(config.read_text(),r'(?m)^#define\s+ENABLE_MEMDUMP\s+1\s*$','Preserve the qualified complete CLI profile')
  helper=ROOT/'ihk/linux/user/rust/build_ihkosctl.py'
  sources={'C':ROOT/'ihk/linux/user/ihkosctl.c','Rust':ROOT/'ihk/linux/user/rust/ihkosctl.rs','observer':FIXTURES/'observer.c','validator':FIXTURES/'validate_hooks.py','config':config,'adapter':helper,'library':library}
  units={'candidate.c':generate_c_unit(sources['C'].read_text()),'candidate.rs':generate_rust_unit(sources['Rust'].read_text()),'observer.c':sources['observer'].read_text()}
  with tempfile.TemporaryDirectory(prefix='m15-intr-cli-',dir=os.environ.get('TMPDIR')) as directory:
   work=Path(directory);receipt=Path(os.environ['M15_INTR_CLI_RECEIPT_DIR']) if 'M15_INTR_CLI_RECEIPT_DIR' in os.environ else work/'receipt';receipt.mkdir(parents=True,exist_ok=False)
   for name,text in units.items():(work/name).write_text(text)
   (receipt/'source-binding.json').write_text(json.dumps({name:{'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()} for name,path in sources.items()},indent=2)+'\n')
   includes=['-I'+str(config.parent),'-I'+str(ROOT/'ihk/linux/include'),'-I'+str(ROOT/'ihk/linux/include/ihk/arch/x86_64')]
   commands=[('observer-compile',[str(selected['CC']),'-std=gnu11','-Wall','-Wextra','-Werror',*includes,'-c',str(work/'observer.c'),'-o',str(work/'observer.o')]),('candidate-C-compile',[str(selected['CC']),'-std=gnu11','-O2','-fPIE',*includes,'-Dmain=observed_main','-c',str(work/'candidate.c'),'-o',str(work/'candidate-C.o')]),('candidate-Rust-compile',['/usr/bin/python3','-B',str(helper),'--rustc',str(selected['RUSTC']),'--source',str(work/'candidate.rs'),'--output',str(work/'candidate-Rust.o'),'--config',str(config)])]
   for language in ('C','Rust'):commands.append(('candidate-'+language+'-hooks',['/usr/bin/nm','-g',str(work/('candidate-'+language+'.o'))]))
   for language in ('C','Rust'):commands.append(('candidate-'+language+'-link',[str(selected['CC']),'-fPIE','-pie',str(work/'observer.o'),str(work/('candidate-'+language+'.o')),'-Wl,--no-as-needed',str(library),'-Wl,-rpath,'+str(library.parent),'-o',str(work/('candidate-'+language))]))
   for language in ('C','Rust'):commands.append(('candidate-'+language+'-run',[str(work/('candidate-'+language)),'0']))
   environment={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C','PYTHONDONTWRITEBYTECODE':'1'};rows=[];gates={}
   for label,payload in commands:
    if label.endswith(('-link','-run')):self.assertEqual(set(gates),{'C','Rust'},'Both fresh object validators must pass before any link/runtime')
    argv=profile(payload,receipt/(label+'.metrics'));row={'label':label,'argv':argv,'environment':environment,'returncode':None,'direct_wait_joined':False}
    with (receipt/(label+'.stdout')).open('xb') as stdout,(receipt/(label+'.stderr')).open('xb') as stderr:
     child=subprocess.Popen(argv,cwd=ROOT,env=environment,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr);row['pid']=child.pid
     try:
      try:row['proc_start_ticks']=int(Path('/proc/'+str(child.pid)+'/stat').read_bytes().decode('utf-8','replace').rsplit(')',1)[1].split()[19])
      except OSError as error:row['birth_observation_error']=type(error).__name__
      rows.append(row);(receipt/'commands.json').write_text(json.dumps(rows,indent=2)+'\n')
     finally:status=child.wait()
    row['returncode']=status;row['direct_wait_joined']=True;(receipt/'commands.json').write_text(json.dumps(rows,indent=2)+'\n')
    stdout=(receipt/(label+'.stdout')).read_text();stderr=(receipt/(label+'.stderr')).read_text();self.assertEqual(status,0,label+'\n'+stdout+stderr);self.assertEqual(stderr,'',label+' unexpected diagnostics')
    if label.endswith('-hooks'):
     decision=validate_hooks(stdout);language=label.split('-')[1];artifact=work/('candidate-'+language+'.o');gates[language]={'object_sha256':hashlib.sha256(artifact.read_bytes()).hexdigest(),'actual_called_validator':decision};(receipt/'gates.json').write_text(json.dumps(gates,indent=2)+'\n')
    else:self.assertEqual(stdout,expected_output() if label.endswith('-run') else '')
    artifacts={}
    for artifact in [*(work/name for name in units),work/'observer.o',*(work/('candidate-'+language+suffix) for language in ('C','Rust') for suffix in ('.o',''))]:
     if artifact.is_file():shutil.copyfile(artifact,receipt/artifact.name);artifacts[artifact.name]=hashlib.sha256(artifact.read_bytes()).hexdigest()
    (receipt/'artifacts.json').write_text(json.dumps(artifacts,indent=2)+'\n')


if __name__=='__main__':unittest.main()
