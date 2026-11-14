"""Actual fixed driver body; real retained command/ELF parsers, modeled make/filesystem boundary."""
from pathlib import PosixPath as RealPath
import contextlib,copy,hashlib,importlib.util,io,json,os,pathlib,runpy,shlex,subprocess,sys,unittest.mock,resource
resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3));resource.setrlimit(resource.RLIMIT_CPU,(30,30))
R=RealPath(__file__).resolve().parent
A=json.loads((R/'module-source-authority.json').read_text())
ORIGINAL=RealPath('/home/holden/mckernel-work/scratch/nsd-c-acc3b42f42e5dc087ce8ac605f8f4961/modules')
raw=(ORIGINAL/'.ihk.o.cmd').read_text();first=raw.splitlines()[0]
assert first.startswith('savedcmd_/candidate/modules/ihk.o := ') and len(first.split(';'))==2
strict=' '.join(shlex.quote(x) for x in ['/accepted-tool/objtool-after',*A['toolflags'],'/candidate/modules/ihk.o'])
base=raw.replace(first,first.split(';')[0]+'; '+strict,1)
SOURCE={x['path']:RealPath(x['published_path']) for x in A['source_files']}
original_spec=importlib.util.spec_from_file_location
class Boundary:
 def __init__(self,label,mutator):
  self.after=False;self.label=label;self.text=mutator(base);self.calls=[];self.root=R/'actual-body-evidence'/label
 def physical(self,p):
  name=str(p)
  if name=='/accepted-tool/objtool-after':return RealPath(A['tool']['path'])
  if name=='/strict-consumer.py':return RealPath(A['reference_driver']['path'])
  if name.startswith('/candidate/evidence'):return self.root/name.removeprefix('/candidate/evidence').lstrip('/')
  if name.startswith('/candidate/modules/'):
   rel=name[len('/candidate/modules/'):]
   if not self.after and rel in SOURCE:return SOURCE[rel]
   return ORIGINAL/rel
  return RealPath(name)
 def make(self,argv,**kw):
  assert argv==A['make_argv'] and kw['cwd']=='/out/build' and kw['env']==A['environment']
  assert 'CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST=n' in argv and 'CONFIG_MCKERNEL_MCCTRL_RUST=n' in argv
  assert 'objtool=/accepted-tool/objtool-after' in argv and 'objtool-args='+' '.join(A['toolflags']) in argv
  self.calls.append(argv);self.after=True
  return subprocess.CompletedProcess(argv,0)
def case(driver,label,mutator=lambda x:x):
 b=Boundary(label,mutator)
 class VPath(pathlib.PosixPath):
  def __new__(cls,*args):return cls._from_parts(args)
  def read_text(self,*a,**kw):
   if str(self)=='/candidate/modules/.ihk.o.cmd':return b.text
   if str(self)=='/candidate/modules/modules.order':return '/candidate/modules/ihk.o\n'
   return b.physical(self).read_text(*a,**kw)
  def read_bytes(self):return b.physical(self).read_bytes()
  def stat(self,*a,**kw):return b.physical(self).stat(*a,**kw)
  def lstat(self,*a,**kw):return b.physical(self).lstat(*a,**kw)
  def is_dir(self):return b.physical(self).is_dir()
  def is_symlink(self):return b.physical(self).is_symlink()
  def exists(self):return b.physical(self).exists()
  def mkdir(self,*a,**kw):b.root.parent.mkdir(exist_ok=True);return b.physical(self).mkdir(*a,**kw)
  def open(self,*a,**kw):return b.physical(self).open(*a,**kw)
  def write_text(self,*a,**kw):return b.physical(self).write_text(*a,**kw)
  def rglob(self,pat):
   if str(self)=='/candidate/modules':return iter(VPath('/candidate/modules')/x for x in SOURCE)
   return super().rglob(pat)
  def glob(self,pat):
   if str(self)=='/candidate/modules' and pat=='*.ko':return iter([self/'ihk.ko'])
   return super().glob(pat)
 def spec(name,path,*args,**kw):return original_spec(name,str(b.physical(path)),*args,**kw)
 stream=io.StringIO();failure=None
 with unittest.mock.patch('pathlib.Path',VPath),unittest.mock.patch('os.sched_getaffinity',return_value={2,3,4,5}),unittest.mock.patch('subprocess.run',side_effect=b.make),unittest.mock.patch('importlib.util.spec_from_file_location',side_effect=spec),unittest.mock.patch.object(sys,'argv',[str(driver),'--execute']),contextlib.redirect_stdout(stream):
  try:runpy.run_path(str(driver),run_name='__main__')
  except BaseException as e:failure=str(e)
 receipt=json.loads((b.root/'receipt.json').read_text())
 assert len(b.calls)==1
 return {'case':label,'accepted':failure is None,'error':failure,'receipt_status':receipt['status'],'driver_stdout':stream.getvalue(),'make_mocked':True,'ELF_modinfo_parser':'actual frozen consumer on real retained ihk.ko','compiler_command':'actual retained .ihk.o.cmd except declared accepted-tool/strictflags delta'}
def mutate_rust(text,replacement):
 lines=text.splitlines();left,right=lines[0].split(';');lines[0]=left.split(':=')[0]+':= '+replacement+' ;'+right;return '\n'.join(lines)+'\n'
CASES=[('positive',lambda s:s,True),('wrong-tool',lambda s:s.replace('/accepted-tool/objtool-after','/wrong-tool/objtool'),False),('missing-werror',lambda s:s.replace(' --werror',''),False),('extra-candidate-source',lambda s:s+'  /candidate/modules/extra.rs \\\n',False),('noncompiler-rust-command',lambda s:mutate_rust(s,'/bin/true -Dwarnings /candidate/modules/ihk.rs'),False),('wrong-crate-name',lambda s:s.replace('--crate-name ihk ','--crate-name wrong '),False),('wrong-emit-object',lambda s:s.replace('--emit=obj=/candidate/modules/ihk.o ','--emit=obj=/candidate/modules/wrong.o '),False),('wrong-savedcmd-target',lambda s:s.replace('savedcmd_/candidate/modules/ihk.o :=','savedcmd_/candidate/modules/wrong.o :='),False),('wrong-source-assignment',lambda s:s.replace('source_/candidate/modules/ihk.o := /candidate/modules/ihk.rs','source_/candidate/modules/ihk.o := /candidate/modules/wrong.rs'),False),('foreign-out-dependency',lambda s:s+'  /out/source/drivers/misc/mckernel/old.rs \\\n',False),('missing-deps-header',lambda s:s.replace('deps_/candidate/modules/ihk.o :=','notdeps_/candidate/modules/ihk.o :='),False)]
if __name__=='__main__':
 driver=RealPath(sys.argv[1]) if len(sys.argv)>1 else R/'ihk_objtool_consumer.py';prefix=sys.argv[2] if len(sys.argv)>2 else 'corrected'
 results=[]
 for name,mutation,want in CASES:
  got=case(driver,prefix+'-'+name,mutation);got['expected_acceptance']=want;got['matches_expectation']=got['accepted']==want;results.append(got)
 report={'status':'PASS' if all(x['matches_expectation'] for x in results) else 'GAPS_REPRODUCED','cases':results,'count':len(results),'mismatches':[x['case'] for x in results if not x['matches_expectation']],'actual_driver':str(driver),'driver_sha256':hashlib.sha256(driver.read_bytes()).hexdigest(),'physical_runtime':False,'compiler_Docker_root':False,'sourcecopy':False,'modeled_boundary':'make result, private candidate filesystem routing, one-module modules.order, container affinity; actual driver/parser/modinfo code unmodified'}
 (R/(prefix+'-actual-body-result.json')).write_text(json.dumps(report,sort_keys=True,indent=2)+'\n');print(json.dumps({'status':report['status'],'cases':len(results),'mismatches':report['mismatches']}))
