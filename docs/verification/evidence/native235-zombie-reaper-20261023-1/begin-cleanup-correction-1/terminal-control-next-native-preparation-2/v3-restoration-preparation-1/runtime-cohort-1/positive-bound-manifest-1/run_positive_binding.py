"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast,hashlib,json,os,resource
D=Path(__file__).resolve().parent
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
raw=H.read_bytes();assert hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
tree=ast.parse(raw,str(H));nodes=[]
for node in tree.body:
 nodes.append(node)
 if isinstance(node,ast.FunctionDef) and node.name=='owned_capture':break
ns={'__file__':str(H)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(H),'exec'),ns)
command={'argv':['/home/holden/anaconda3/bin/python3','-I','-B',str(D/'test_positive_binding.py'),'--manifest','/home/holden/mckernel-work/scratch/nm05p5a1/m.json','--manifest-sha256','8c03e5570b98a99db009f74f6dea9bf27ad9f046abeeea44d66ec561cbe708d7'],'purpose':__doc__,'shell':False}
ns['write'](D/'command.json',command)
os.sched_setaffinity(0,{6})
for key,val in ((resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,30),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)):resource.setrlimit(key,(val,val))
result=ns['owned_capture'](command,D,60,lambda:None)
ns['write'](D/'capture-result.json',result)
print(json.dumps(result,sort_keys=True))
