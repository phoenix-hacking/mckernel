"""Four candidate whole-main FUNCTION unknown-action cases, no CRT/device claim.

Set explicit actual CC/RUSTC, qualified M15_UNKNOWN_CONFIG and genuine HOST
M15_UNKNOWN_LIBRARY. Current repository source is captured dynamically; no old
baseline/sourceproof/object is needed. Invoke only under fresh HOST admission.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import tempfile
import unittest
from test_m15_ihkosctl_intr import generate_c_unit,validate_hooks as validate
HERE=Path(__file__).resolve().parent
ROOT=Path(os.environ.get('M15_REPO',str(HERE.parents[1])))
FIXTURES=HERE/'fixtures/m15-unknown-action'

def generate_rust_unit(source):
 marker=re.search(r'#\[no_mangle\](?=\s*pub unsafe extern "C" fn main\()',source)
 if marker is None:raise ValueError('One actual main export required')
 source=source[:marker.start()]+'#[export_name="observed_main"]'+source[marker.end():]
 start=re.search(r'extern "C"\s*\{',source).start();end=source.index('\n}',start);declarations=source[start:end]
 for name in ('open','ioctl','close'):
  marker='fn '+name+'('
  if declarations.count(marker)!=1:raise ValueError('One actual CLI FFI declaration required: '+name)
  declarations=declarations.replace(marker,'#[link_name="observation_'+name+'"] '+marker)
 return source[:start]+declarations+source[end:]

def profile(label,payload,receipt):
 return ['/usr/bin/taskset','-c','7','/usr/bin/timeout','--signal=TERM','--kill-after=2s','58s','/usr/bin/prlimit','--as=1073741824:1073741824','--cpu=45:45','--fsize=67108864:67108864','--core=0:0','--','/usr/bin/time','-v','-o',str(receipt/(label+'.metrics'))]+payload

def command_plan(work,cc,rustc,config,library,proof):
 includes=['-I'+str(config.parent),'-I'+str(ROOT/'ihk/linux/include'),'-I'+str(ROOT/'ihk/linux/include/ihk/arch/x86_64')]
 rows=[('observer-compile',[cc,'-std=gnu11','-Wall','-Wextra','-Werror',*includes,'-c',str(work/'observer.c'),'-o',str(work/'observer.o')])];objects={}
 for key in proof['sources']:
  tool,lang,mode=key.split('-');objects[key]=Path(proof['reused_objects'][key]['path']) if key in proof['reused_objects'] else work/(key+'.o')
  if key in proof['reused_objects']:continue
  if lang=='C':payload=[cc,'-std=gnu11','-O2','-fPIE',*includes,'-Dmain=observed_main','-c',str(work/(key+'.c')),'-o',str(objects[key])]
  else:
   payload=[rustc,'--crate-name',tool,'--crate-type=lib','--edition=2021','-C','panic=abort','-C','opt-level=2','-C','debuginfo=1','-C','relocation-model=pic','-C','force-unwind-tables=no','--emit=obj='+str(objects[key])]
   if tool=='ihkosctl':payload+=['--cfg','ihkosctl_memdump']
   payload.append(str(work/(key+'.rs')))
  rows.append((key+'-compile',payload))
 rows.append(('all-object-hook-gates',['/usr/bin/nm','-g',*(str(x) for x in objects.values())]))
 for key,path in objects.items():rows.append((key+'-link',[cc,'-fPIE','-pie',str(work/'observer.o'),str(path),'-Wl,--no-as-needed',str(library),'-Wl,-rpath,'+str(library.parent),'-o',str(work/key)]))
 for key in objects:
  tool,lang,mode=key.split('-');rows.append((key+'-run',[str(work/key),tool,str(int(mode=='candidate')),str(work/key)]))
 return rows,objects

def hook_groups(output,objects):
 groups={};current=None;expected={str(path) for path in objects.values()}
 for line in output.splitlines():
  if line.endswith(':') and line[:-1] in expected:current=line[:-1];groups[current]=[]
  elif line.strip():
   if current is None:raise ValueError('Expected explicit nm object header before symbols: '+line)
   groups[current].append(line)
 if set(groups)!=expected:raise ValueError('Missing or unexpected nm object groups')
 return {key:{'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'called_validator':validate('\n'.join(groups[str(path)]))} for key,path in objects.items()}

class M15UnknownActionMainTests(unittest.TestCase):
 def test_current_unknown_action_raw_result_and_usage(self):
  selected={name:Path(os.environ[name]) for name in ('CC','RUSTC','M15_UNKNOWN_CONFIG','M15_UNKNOWN_LIBRARY')}
  for name,path in selected.items():
   self.assertTrue(path.is_absolute() and path.is_file(),name+' requires an explicit actual absolute file')
   if name in ('CC','RUSTC'):self.assertTrue(os.access(path,os.X_OK))
  sources={}
  for tool in ('ihkconfig','ihkosctl'):
   for language in ('C','Rust'):
    path=ROOT/('ihk/linux/user/'+('rust/' if language=='Rust' else '')+tool+('.c' if language=='C' else '.rs'));sources[tool+'-'+language+'-candidate']={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
  units={key+('.c' if '-C-' in key else '.rs'):generate_c_unit(Path(binding['path']).read_text()) if '-C-' in key else generate_rust_unit(Path(binding['path']).read_text()) for key,binding in sources.items()};units['observer.c']=(FIXTURES/'observer.c').read_text()
  proof={'sources':sources,'generated_unit_sha256':{name:hashlib.sha256(text.encode()).hexdigest() for name,text in units.items()},'reused_objects':{},'expected_stderr_bytes':{'ihkconfig':292,'ihkosctl':499},'profile_sha256':{name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in selected.items()}}
  if os.environ.get('M15_UNKNOWN_EXPECTED_PROOF'):
   expected=json.loads(Path(os.environ['M15_UNKNOWN_EXPECTED_PROOF']).read_text());self.assertEqual(proof['generated_unit_sha256'],{name:expected['generated_unit_sha256'][name] for name in units})
  if os.environ.get('M15_UNKNOWN_RECEIPT_DIR'):receipt=Path(os.environ['M15_UNKNOWN_RECEIPT_DIR'])
  else:
   temporary=tempfile.TemporaryDirectory(prefix='m15-unknown-action-');self.addCleanup(temporary.cleanup);receipt=Path(temporary.name)
  receipt.mkdir(parents=True,exist_ok=True);work=receipt/'work';work.mkdir(exist_ok=True)
  for name,text in units.items():(work/name).write_text(text)
  (receipt/'SOURCE-BINDING.json').write_text(json.dumps(proof,indent=2)+'\n')
  config=selected['M15_UNKNOWN_CONFIG'];library=selected['M15_UNKNOWN_LIBRARY'];header=config.read_text();self.assertRegex(header,r'(?m)^#define\s+ENABLE_MEMDUMP\s+1\s*$');ids=re.findall(r'^#define\s+BUILDID\s+"([A-Za-z0-9._+\-]+)"\s*$',header,re.M);self.assertEqual(len(ids),1)
  environment={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C','PYTHONDONTWRITEBYTECODE':'1','IHKCONFIG_BUILDID':ids[0],'IHKOSCTL_BUILDID':ids[0]}
  commands,objects=command_plan(work,str(selected['CC']),str(selected['RUSTC']),config,library,proof);rows=[];gates={}
  for label,payload in commands:
   if label.endswith(('-link','-run')):self.assertEqual(set(gates),set(objects),'All4 actual object validators must pass BEFORE any link/runtime')
   argv=profile(label,payload,receipt)
   with (receipt/(label+'.stdout')).open('xb') as stdout,(receipt/(label+'.stderr')).open('xb') as stderr:
    child=subprocess.Popen(argv,cwd=ROOT,env=environment,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
    try:
     try:birth=Path('/proc/'+str(child.pid)+'/stat').read_text().rsplit(')',1)[1].split()[19]
     except FileNotFoundError:birth=None
     rows.append({'label':label,'argv':argv,'environment':environment,'pid':child.pid,'proc_start_ticks':birth,'returncode':None,'direct_wait_joined':False});(receipt/'COMMANDS.json').write_text(json.dumps(rows,indent=2)+'\n')
    finally:status=child.wait()
   rows[-1].update({'returncode':status,'direct_wait_joined':True});(receipt/'COMMANDS.json').write_text(json.dumps(rows,indent=2)+'\n');stdout=(receipt/(label+'.stdout')).read_text();stderr=(receipt/(label+'.stderr')).read_text();self.assertEqual(status,0,label+'\n'+stdout+stderr);self.assertEqual(stderr,'',label+' unexpected diagnostics')
   if label=='all-object-hook-gates':gates=hook_groups(stdout,objects);(receipt/'OBJECT-GATES.json').write_text(json.dumps(gates,indent=2)+'\n')
   elif label.endswith('-run'):
    key=label[:-4];tool,language,mode=key.split('-');self.assertEqual(mode,'candidate');expected='unknown-action mainFUNCTION tool='+tool+' argv=0,qurey raw-main=1 opens=1 ioctl=0 closes=1 EBADF=1 stdout-bytes=0 stderr-bytes='+str(proof['expected_stderr_bytes'][tool])+' exact-usage=1 inputs-unchanged=1 fd-restored=1 no-CRT-exit-claim=1\n';self.assertEqual(stdout,expected);self.assertEqual((work/(key+'.main.stdout')).read_bytes(),b'');self.assertEqual(len((work/(key+'.main.stderr')).read_bytes()),proof['expected_stderr_bytes'][tool])
   else:self.assertEqual(stdout,'',label+' unexpected stdout')
  (receipt/'ARTIFACTS.json').write_text(json.dumps({str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in work.iterdir() if path.is_file()},indent=2)+'\n');(receipt/'RESULT.json').write_text(json.dumps({'status':'PASS_CANDIDATE_FULL_MAIN_FUNCTION_UNKNOWN_ACTION','candidate_cases':4,'raw_candidate':1,'genuine_anonymous_FD_onceclose_EBADF':4,'ioctl_calls':0,'exact_raw_main_stdio_retained':True,'all4_actual_object_called_gates_before_any_link_runtime':True,'all_direct_waits_joined':True,'commands':rows,'source_binding':proof,'claim':'Actual whole mainFUNCTION only; no CRT processstatus/installedCLI/device/backend/native or new provider qualification'},indent=2)+'\n')
if __name__=='__main__':unittest.main()
