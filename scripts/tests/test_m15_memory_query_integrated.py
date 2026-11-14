"""Reader/converter/public-query interaction using genuine ordinary HOST libc.

Source-bound local observations only; no sysfs, IHK device, backend or native proof.
The six cases per language are distinct interaction coverage, not a replay of the
isolated reader or all allocation-failure vectors.
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
FIXTURES=HERE/'fixtures/m15-memory-query-integrated'


def function(source,marker):
 start=source.index(marker);brace=source.index('{',start);depth=0
 for offset in range(brace,len(source)):
  if source[offset]=='{':depth+=1
  elif source[offset]=='}':
   depth-=1
   if depth==0:return source[start:offset+1]+'\n'
 raise ValueError('Unterminated actual source function: '+marker)


def generate_units(c,rust,parser,observer,template):
 loglevel=re.search(r'^int loglevel = [^;]+;',c,re.M).group(0);observer=observer.replace('__LOGLEVEL_DECL__',loglevel)
 macros=''
 for marker in ('#define eprintf(','#define CHKANDJUMP('):
  start=c.index(marker);macros+=c[start:c.index('\n\n',start)]+'\n'
 debug=''.join(re.search(r'^#define '+name+r'\(fmt, args\.\.\.\) do \{  \} while \(0\)$',c,re.M).group(0)+'\n' for name in ('dnprintk','dprintf','dprintk'))
 all_macro=re.search(r'^#define IHK_SMP_MEM_ALL[^\n]+',c,re.M).group(0)+'\n';kinds=re.search(r'const char \*ihklib_os_query_mem_type_str\[\]\s*=\s*\{.*?\n\};',c,re.S).group(0)+'\n'
 c_markers=['static long ihk_memparse(','static int mem_str2array(','int mem_str2count(','static int mem_str2chunks(','static int get_meminfo_path(','int ihklib_os_query_mem_sysfs(','static int ihklib_os_query_mem(','int ihk_os_query_total_mem(','int ihk_os_query_free_mem(']
 c_blocks={marker:function(c,marker) for marker in c_markers}
 if 'size_t line_len = 0;' not in c_blocks['int ihklib_os_query_mem_sysfs(']:raise ValueError('Initialized reviewed C EOF reader required')
 if 'free(line);' not in c_blocks['int ihklib_os_query_mem_sysfs(']:raise ValueError('Reviewed C terminal ownership required')
 aliases='\n#define stat(path,storage) observation_stat(path,storage)\n'+''.join('#define '+name+' '+target+'\n' for name,target in [('fopen','observation_fopen'),('fclose','observation_fclose'),('getline','observation_getline'),('calloc','observation_calloc'),('strdup','observation_strdup'),('free','observation_free'),('close','observation_close'),('ihklib_os_open','observation_open')])
 c_unit=observer+aliases+debug+macros+all_macro+kinds+''.join(c_blocks.values())+'\nint main(int argc,char **argv){assert(argc==2);return observation_run(ihk_os_query_total_mem,ihk_os_query_free_mem,argv[1]);}\n'
 parser_functions=''.join(function(parser,marker) for marker in ('unsafe fn is(','unsafe fn mem_parse(','pub(super) unsafe fn mem_array('))
 chunk_start=rust.index('#[repr(C)]');chunk_end=rust.index('// stat fields',chunk_start)
 stat_start=rust.index('#[repr(C,align(8))]');stat_end=rust.index('unsafe extern "C"',stat_start)
 query_start=rust.index('unsafe fn mem_chunks(');query_end=rust.index('#[cfg(ihklib_mcstat_fixture)]',query_start)
 values={'__STAT_STORAGE__':rust[stat_start:stat_end],'__PARSER__':parser_functions,'__MEM_CHUNK_TYPE__':rust[chunk_start:chunk_end],'__LOGGING__':function(rust,'unsafe fn log<'),'__STAT_PATH__':function(rust,'#[cfg(any(ihklib_stat_abi_stat,ihklib_stat_abi_xstat1))]\nunsafe fn stat_path('),'__MEM_PATH__':function(rust,'unsafe fn mem_path('),'__READER__':function(rust,'#[no_mangle]\npub unsafe extern "C" fn ihklib_os_query_mem_sysfs('),'__QUERY_AND_PUBLIC_WRAPPERS__':rust[query_start:query_end]}
 rust_unit=template
 for marker,body in values.items():rust_unit=rust_unit.replace(marker,body)
 if re.search(r'__[A-Z_]+__',rust_unit):raise ValueError('Unresolved source marker')
 return {'observer.c':observer,'c-integrated.c':c_unit,'rust-integrated.rs':rust_unit},{'C':c_blocks,'Rust':values}


def profile(label,payload,receipt):
 return ['/usr/bin/taskset','-c','6','/usr/bin/timeout','--signal=TERM','--kill-after=2s','58s','/usr/bin/prlimit','--as=1073741824:1073741824','--cpu=45:45','--fsize=67108864:67108864','--core=0:0','--','/usr/bin/time','-v','-o',str(receipt/(label+'.metrics'))]+payload


def command_plan(work,cc,rustc,includes,cfg):
 return [('observer-compile',[cc,'-std=gnu11','-Wall','-Wextra','-Werror',*includes,'-c',str(work/'observer.c'),'-o',str(work/'observer.o')]),('c-integrated-compile',[cc,'-std=gnu11','-Wall','-Werror',*includes,str(work/'c-integrated.c'),'-o',str(work/'c-integrated')]),('rust-integrated-compile',[rustc,'--edition=2021','-Dwarnings','--cfg',cfg,str(work/'rust-integrated.rs'),'-C','link-arg='+str(work/'observer.o'),'-o',str(work/'rust-integrated')]),('c-integrated-run',[str(work/'c-integrated'),str(work/'text-c')]),('rust-integrated-run',[str(work/'rust-integrated'),str(work/'text-rust')])]


class M15MemoryQueryIntegratedTests(unittest.TestCase):
 def test_reader_converter_public_query_interaction(self):
  operation=os.environ.get('M15_INTEGRATED_OPERATION_MODE')=='1'
  sources={
   'C':Path(os.environ['M15_INTEGRATED_C_SOURCE']) if operation else ROOT/'ihk/linux/user/ihklib.c',
   'Rust':Path(os.environ['M15_INTEGRATED_RUST_SOURCE']) if operation else ROOT/'ihk/linux/user/rust/whole70/ihklib_mcstat_memory_shared_parser.rs',
   'parser':Path(os.environ['M15_INTEGRATED_PARSER_SOURCE']) if operation else ROOT/'ihk/linux/user/rust/whole70/ihklib_cli_parsers_ikc_shared.rs'}
  for compiler in ('CC','RUSTC'):
   path=Path(os.environ[compiler]);self.assertTrue(path.is_absolute() and path.is_file() and os.access(path,os.X_OK),compiler+' must select an explicit executable')
  units,blocks=generate_units(*(sources[name].read_text() for name in ('C','Rust','parser')),(FIXTURES/'observations.c.in').read_text(),(FIXTURES/'rust.rs.in').read_text())
  binding={'sources':{str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in sources.values()},'generated_unit_sha256':{name:hashlib.sha256(text.encode()).hexdigest() for name,text in units.items()}}
  if operation:
   frozen=json.loads(Path(os.environ['M15_INTEGRATED_FROZEN_PROOF']).read_text());self.assertEqual(binding['generated_unit_sha256'],frozen['generated_unit_sha256'])
  if 'M15_INTEGRATED_RECEIPT_DIR' in os.environ:receipt=Path(os.environ['M15_INTEGRATED_RECEIPT_DIR'])
  else:
   temporary=tempfile.TemporaryDirectory(prefix='m15-memory-query-integrated-');self.addCleanup(temporary.cleanup);receipt=Path(temporary.name)
  receipt.mkdir(parents=True,exist_ok=True);work=receipt/'work';work.mkdir(exist_ok=True)
  for name,text in units.items():(work/name).write_text(text)
  (receipt/'SOURCE-BINDING.json').write_text(json.dumps(binding,indent=2)+'\n')
  (receipt/'EXTRACTED-BLOCKS.json').write_text(json.dumps(blocks,indent=2)+'\n')
  for language in ('c','rust'):(work/('text-'+language)).mkdir(exist_ok=True)
  cfg=Path(os.environ['M15_INTEGRATED_STAT_CFG']).read_text().strip();self.assertEqual(cfg,'ihklib_stat_abi_stat')
  commands=command_plan(work,os.environ['CC'],os.environ['RUSTC'],['-I'+str(ROOT/'ihk/linux/include'),'-I'+str(ROOT/'ihk/linux/include/ihk/arch/x86_64')],cfg);rows=[]
  languages=(os.environ['M15_INTEGRATED_LANGUAGE'],) if 'M15_INTEGRATED_LANGUAGE' in os.environ else ('c','rust')
  self.assertTrue(all(language in ('c','rust') for language in languages),'Select c or rust')
  labels={'c':('c-integrated-compile','c-integrated-run'),'rust':('observer-compile','rust-integrated-compile','rust-integrated-run')}
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
    self.assertEqual(stdout.count('CASE api='),6);self.assertEqual(stdout.count('FILE-CLOSE terminal-freed=1 entry-errno=11'),6);self.assertEqual(stdout.count('LINE generation='),16);self.assertEqual(stdout.count('LINE-FREE generation='),16)
    self.assertTrue(stdout.endswith('integrated cases=6 APIs=2 success=2 no-match-EINVAL=2 post-EOF-converter-ENOMEM=2 all-line-parser-FILE-FD-ownership-released\n'))
  (receipt/'RESULT.json').write_text(json.dumps({'status':'PASS_SOURCE_BOUND_READER_CONVERTER_PUBLIC_QUERY_INTERACTION','cases_per_language':6,'languages':list(languages),'all_direct_waits_joined':True,'commands':rows,'source_binding':binding,'actual_IHK_sysfs_device_native_backend_or_final_project_provider_claimed':False},indent=2)+'\n')


if __name__=='__main__':unittest.main()
