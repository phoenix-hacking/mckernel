"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Callable exact tested controller pre-effect AST consumer. Explicit TESTONLY root/profile scaffold; never rootprofile proof.
No mkdir/Popen/process factory or workload. FinalCLI reads the exact published requestbytes/hash.
"""
import ast,copy,hashlib,importlib.util,json,os,resource,sys,types
from pathlib import Path
D=Path(__file__).resolve().parent
seq=[0]
factory_calls=[]
def sha(b):return hashlib.sha256(b).hexdigest()

def load(p,name):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

class ReachedPreEffect(Exception):pass

class Environment:
 def __init__(self,real,values):self.real=real;self.values=values;self.calls=[]
 def __getattr__(self,k):
  if k in self.values:
   def value(*a):self.calls.append(k);return self.values[k](*a)
   return value
  return getattr(self.real,k)

def refused_factory(*a,**kw):factory_calls.append((a,kw));raise AssertionError('process factory forbidden')

def consume(controller,request_path,request_sha):
 m=load(controller,'actual_controller_'+str(seq[0]));tree=ast.parse(controller.read_bytes());main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main');body=[];boundary=None
 for n in main.body:
  if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and isinstance(n.value.func.value,ast.Name) and n.value.func.value.id=='out' and n.value.func.attr=='mkdir':boundary=n;break
  body.append(n)
 assert boundary is not None and len(body)>15
 original_prefix_AST=ast.dump(ast.Module(body=body,type_ignores=[]),include_attributes=False)
 extracted=copy.deepcopy(main);extracted.body=copy.deepcopy(body)+[ast.Raise(exc=ast.Call(func=ast.Name(id='ReachedPreEffect',ctx=ast.Load()),args=[],keywords=[]),cause=None)]
 assert ast.dump(ast.Module(body=extracted.body[:-1],type_ignores=[]),include_attributes=False)==original_prefix_AST
 o=Environment(os,dict(getuid=lambda:0,geteuid=lambda:0,sched_getaffinity=lambda pid:{7}));q=Environment(resource,dict(getrlimit=lambda key:(m.CAP,m.CAP) if key==resource.RLIMIT_FSIZE else (resource.RLIM_INFINITY,resource.RLIM_INFINITY) if key==resource.RLIMIT_CPU else (_ for _ in ()).throw(AssertionError('unexpected rootprofile requirement'))))
 m.os=o;m.resource=q;m.subprocess=types.SimpleNamespace(Popen=refused_factory,DEVNULL=__import__('subprocess').DEVNULL);m.ReachedPreEffect=ReachedPreEffect
 exec(compile(ast.fix_missing_locations(ast.Module(body=[extracted],type_ignores=[])),str(controller),'exec'),m.__dict__);prior=sys.argv;sys.argv=[str(controller),str(request_path),request_sha]
 try:m.main()
 finally:sys.argv=prior
 raise AssertionError('unexpectedreturn')

def main():
 assert len(sys.argv)==3 and os.getuid()==os.geteuid()==1000 and sys.executable=='/home/holden/anaconda3/bin/python3' and sys.version_info[:3]==(3,9,12),'exact ordinary Anaconda3.9.12 final consumer'
 request=D/'CAPTURE-REQUEST.json';controller=D/'capture_root_LONG.NOT-RELEASED.py'
 assert sys.argv[1]==str(request),'exact final published requestpath'
 m=load(controller,'exact_final_controller_pin');assert m.filepin(controller,65536)['sha256']=='f7445028a107d62355628f09b2bbcf438231ab2b2a0a5d7863e567468a17dfbe','reviewed exact final controller source'
 try:consume(controller,request,sys.argv[2])
 except ReachedPreEffect:pass
 else:raise AssertionError('actual prefix boundary not reached')
 assert not factory_calls
 print(json.dumps(dict(scope=__doc__,status='PASS_ACTUAL_FINAL_SERIALIZED_REQUEST_PRE_EFFECT_GUARDS',request_path=str(request),request_sha256=sys.argv[2],controller_sha256='f7445028a107d62355628f09b2bbcf438231ab2b2a0a5d7863e567468a17dfbe',actual_main_prefix_AST_identical=True,privileged_environment_scaffolding='getuid/geteuid0/affinity7; FSIZE384MiB/CPUunlimited; actualthreeenvironmentneeds evaluated, NOrootprofileproof',boundary='BEFOREout.mkdir and Popen',process_factory_calls=0,root=0,Docker=0,workload=0,execution_release=False,native_acceptance=False),sort_keys=True))
if __name__=='__main__':main()
