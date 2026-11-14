"""Candidate-only scoped C and full selected Rust dump parent-path tests.

Defaults read current repository sources and relative fixtures; set explicit
actual CC/RUSTC and qualified MCKERNEL_DUMP_ABI_RS. No historical baseline runs.

BFD fopen always fails locally. No file, BFD object, real ioctl or NMI exists.
The two C buffers retained by existing cleanup are observed and reclaimed only
AFTER return; this parent-path correction does not claim C leak-free cleanup.
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
FIXTURES=HERE/'fixtures/m15-dump-root-parent'

def function(source,marker):
 start=source.index(marker);brace=source.index('{',start);depth=0
 for offset in range(brace,len(source)):
  if source[offset]=='{':depth+=1
  elif source[offset]=='}':
   depth-=1
   if depth==0:return source[start:offset+1]+'\n'
 raise ValueError(marker)

def generate_units(c_source,rust_source,observer):
 units={'observer.c':observer};blocks={}
 for mode,c,rust in (('candidate',c_source,rust_source),):
  body=function(c,'int ihk_os_makedumpfile(');start=body.index('\n\tok = bfd_set_format(');end=body.rindex('\n out:');prefix=body[:start];tail=body[end:];skipped=body[start:end]
  macros=c[c.index('#else\n#define dnprintk(')+len('#else\n'):c.index('\n#endif',c.index('#else\n#define dnprintk('))]+'\n'
  name_macro=re.search(r'^#define PHYSMEM_NAME_SIZE[^\n]*',c,re.M).group(0)+'\n'
  aliases='\n'+''.join('#define '+a+' '+b+'\n' for a,b in [('ihklib_os_open','observation_os_open'),('ihk_os_get_status','observation_status'),('ioctl','observation_ioctl'),('close','observation_close'),('malloc','observation_malloc'),('free','observation_free'),('access','observation_access'),('bfd_init','observation_bfd_init'),('bfd_fopen','observation_bfd_fopen'),('bfd_close','observation_bfd_close')])
  # Exact never-reached BFD-success region is bound separately, not translated
  # against modern HOST BFD headers. The boundary guard must never execute.
  units['c-'+mode+'.c']=observer+aliases+macros+name_macro+prefix+'\n abort(); /* harness: fopen must have returned NULL */\n'+tail+'\nint main(void){return observation_run(ihk_os_makedumpfile,'+str(int(mode=='baseline'))+',1);}\n'
  external={'ihklib_os_open':'observation_os_open','ihk_os_get_status':'observation_status','ioctl':'observation_ioctl','close':'observation_close','malloc':'observation_malloc','free':'observation_free','access':'observation_access'}
  for name in ('bfd_init','bfd_fopen','bfd_close','bfd_set_format','bfd_make_section_anyway','bfd_set_section_size','bfd_set_section_flags','bfd_get_section_by_name','bfd_set_section_contents'):external[name]='observation_'+name
  changed=rust
  for name,target in external.items():
   marker='    fn '+name+'(';assert changed.count(marker)==1,name;changed=changed.replace(marker,'    #[link_name="'+target+'"]\n'+marker)
  units['rust-'+mode+'.rs']=changed+'\nfn main(){std::process::exit(unsafe{observation_run(ihk_os_makedumpfile,'+str(int(mode=='baseline'))+',0)});}\n'
  marker='unsafe extern "C" {';where=units['rust-'+mode+'.rs'].index(marker)+len(marker)
  units['rust-'+mode+'.rs']=units['rust-'+mode+'.rs'][:where]+'\n    fn observation_run(dump:unsafe extern "C" fn(c_int,*mut c_char,c_int,c_int)->c_int,baseline:c_int,is_c:c_int)->c_int;'+units['rust-'+mode+'.rs'][where:]
  blocks[mode]={'C_scope':'Exact production function prefix through failed bfd_fopen, harness unreachable abort guard, exact production out-tail. NO full C BFD-success-body claim.','C_prefix':prefix,'C_tail':tail,'C_skipped_unreachable_BFD_success_region_sha256':hashlib.sha256(skipped.encode()).hexdigest(),'C_skipped_unreachable_BFD_success_region_bytes':len(skipped),'C_macros':macros,'C_name_macro':name_macro,'Rust_scope':'Entire actual selected module body unchanged; only explicit extern link-name attributes and harness entry/declaration added','Rust_actual_source_sha256':hashlib.sha256(rust.encode()).hexdigest(),'Rust_external_link_bindings':external}
 return units,blocks

def profile(label,payload,receipt):
 return ['/usr/bin/taskset','-c','7','/usr/bin/timeout','--signal=TERM','--kill-after=2s','58s','/usr/bin/prlimit','--as=1073741824:1073741824','--cpu=45:45','--fsize=67108864:67108864','--core=0:0','--','/usr/bin/time','-v','-o',str(receipt/(label+'.metrics'))]+payload

def command_plan(work,cc,rustc,includes):
 rows=[('observer-compile',[cc,'-std=gnu11','-Wall','-Wextra','-Werror',*includes,'-c',str(work/'observer.c'),'-o',str(work/'observer.o')])]
 for mode in ('candidate',):rows.append(('c-'+mode+'-compile',[cc,'-std=gnu11','-DPAGE_SIZE=4096','-DENABLE_MEMDUMP=1','-Wall','-Werror','-Wno-unused-variable','-Wno-unused-but-set-variable',*includes,str(work/('c-'+mode+'.c')),'-o',str(work/('c-'+mode))]))
 for mode in ('candidate',):rows.append(('rust-'+mode+'-compile',[rustc,'--edition=2021','-Dwarnings',str(work/('rust-'+mode+'.rs')),'-C','link-arg='+str(work/'observer.o'),'-o',str(work/('rust-'+mode))]))
 for kind in ('c','rust'):
  for mode in ('candidate',):rows.append((kind+'-'+mode+'-run',[str(work/(kind+'-'+mode))]))
 return rows

class M15DumpRootParentTests(unittest.TestCase):
 def test_safe_root_nested_relative_parent_paths(self):
  self.assertTrue(os.environ.get('CC') and os.environ.get('RUSTC') and os.environ.get('MCKERNEL_DUMP_ABI_RS'),'Set explicit actual CC/RUSTC and qualified MCKERNEL_DUMP_ABI_RS input')
  cpath=Path(os.environ.get('M15_DUMP_C_CANDIDATE',str(ROOT/'ihk/linux/user/ihklib.c')));rpath=Path(os.environ.get('M15_DUMP_RUST_CANDIDATE',str(ROOT/'ihk/linux/user/rust/whole70/ihklib_dump.rs')));abi=Path(os.environ['MCKERNEL_DUMP_ABI_RS'])
  units,blocks=generate_units(cpath.read_text(),rpath.read_text(),(FIXTURES/'observations.c.in').read_text())
  frozen={'source_sha256':{str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in (cpath,rpath,abi)},'generated_unit_sha256':{name:hashlib.sha256(text.encode()).hexdigest() for name,text in units.items()}}
  if os.environ.get('M15_DUMP_EXPECTED_PROOF'):
   expected=json.loads(Path(os.environ['M15_DUMP_EXPECTED_PROOF']).read_text());self.assertEqual(frozen['generated_unit_sha256'],{name:expected['generated_unit_sha256'][name] for name in units})
  if os.environ.get('M15_DUMP_RECEIPT_DIR'):receipt=Path(os.environ['M15_DUMP_RECEIPT_DIR'])
  else:
   temporary=tempfile.TemporaryDirectory(prefix='m15-dump-root-parent-');self.addCleanup(temporary.cleanup);receipt=Path(temporary.name)
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
   rows.append({'label':label,'argv':argv,'pid':child.pid,'proc_start_ticks':birth,'returncode':status,'direct_wait_joined':True});(receipt/'COMMANDS.json').write_text(json.dumps(rows,indent=2)+'\n');(receipt/'ARTIFACTS.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in work.iterdir() if p.is_file()},indent=2)+'\n')
   stdout=(receipt/(label+'.stdout')).read_text();stderr=(receipt/(label+'.stderr')).read_text();self.assertEqual(status,0,label+'\n'+stdout+stderr);self.assertEqual(stderr,'',label+' unexpecteddiagnostics')
   if label.endswith('-run'):
    mode='baseline' if '-baseline-' in label else 'candidate';language='C-scoped' if label.startswith('c-') else 'Rust-public';self.assertEqual(stdout.count('CASE language='),4);self.assertTrue(stdout.endswith('dump-parent cases=4 language='+language+' mode='+mode+' exact-path-and-error-order all-owned-allocations-reclaimed all-anonymous-FDs-once-closed no-real-BFD-object\n'))
  (receipt/'RESULT.json').write_text(json.dumps({'status':'PASS_SCOPED_C_AND_FULL_RUST_DUMP_PARENT_PATHS','candidate_C_cases':4,'candidate_Rust_cases':4,'C_preexisting_retained_owners_observed_then_reclaimed':8,'Rust_survivors':0,'C_scope':'Actual production prefix through local failedbfd_fopen+actualout-tail, unreachable BFDsuccessregion excluded/bound; no wholeCbody claim','Rust_scope':'Full actual selected publicdumpmodule with explicitlocalproviderlinkseams','all_direct_waits_joined':True,'commands':rows,'source_binding':frozen,'real_BFD_or_dump_device_NMI_or_native_executed':False},indent=2)+'\n')
if __name__=='__main__':unittest.main()
