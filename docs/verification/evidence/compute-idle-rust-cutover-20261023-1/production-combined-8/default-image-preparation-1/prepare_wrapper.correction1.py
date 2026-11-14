"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One bounded source wrapper-generation correction; no workload executed here.
"""
from pathlib import Path
import hashlib,json,ast
r=Path(__file__).resolve().parent
h=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1');b=h/'production-combined-7/default-image-preparation-1';n=h/'production-combined-8/default-image-preparation-1';d=n/'next-build-preparation-1';e=r/'next-build-preparation-1'
def sha(x):return hashlib.sha256(x).hexdigest()
def put(name,raw):
 for dest in (d,e):
  with (dest/name).open('xb') as f:f.write(raw)
oh=sha((d/'native_rust_exact_mckernel_image_container_owner.py').read_bytes());ph=sha((n/'native_rust_exact_build_offline.py').read_bytes());dh=sha((n/'native_rust_exact_mckernel_image_offline.py').read_bytes())
s=(b/'next-build-preparation-1/prepare_and_validate.py').read_text()
s=s.replace("B=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-6/default-image-preparation-1/next-build-preparation-1')",'B=Path('+repr(str(b/'next-build-preparation-1'))+')')
s=s.replace('095b20a82a3477519ba933babe21fe256fa73c2b69613b7d12f97e95cf58b39e','cc2ee651d75520825cb1d944664094b0154590682e066989d508e0f1ba51b165').replace('1ff94d6e48bb3b694d09ac467fc1dd630d471983fcc24335b2cd5c3c85aaf48b','550284bc2beba2db2221b16a61294034ec4cf1ada0d449b8b2f8fd70add74eb5').replace('6c600601097aa9ee053a8c6cb7350a5d11b17613e07bf1bf2cc9dad0d9178d0a',dh).replace('dbe2a604df56b4e90eaa11716ba290c5d23d3eaaf7da017be52620f29687bb7a',ph).replace('5d3224a0d01e3517af6bc4beee5e9a4bb77d697294d2dd4f4e980b08fc7d057b',oh).replace('os.sched_getaffinity(0)=={0}','os.sched_getaffinity(0)=={6}').replace('mem>=19*1073741824','mem>=7*1073741824').replace('candidate7','candidate8').replace('CANDIDATE7','CANDIDATE8')
s=s.replace('root_planning_reservation=19*1073741824)','root_planning_reservation=19*1073741824,remaining_nonheavy_reservation=7*1073741824,active_heavy_authority="Root LONGowner3769329/tool2203; current MemAvailable reflects liveallocation")')
ast.parse(s);vh=sha(s.encode());put('prepare_and_validate.py',s.encode())
runner=(b/'run_materialization_and_pure.py').read_text().replace('os.sched_getaffinity(0)=={0}','os.sched_getaffinity(0)=={6}').replace("'-c','0'","'-c','6'").replace("'/usr/bin/python3','-I','-B',str(materializer)","'/home/holden/anaconda3/bin/python3','-I','-B',str(materializer)")
runner=runner.replace('bbd3c6730edaf6a2db66d4d647c1ba10432432ca1e08b40931360198e77de971','e50b76983d641ea71bc340a5972e9d99e1c491abf0419971b790f644c940f78d').replace('771d4b1b1c26702ecb4c906bdaf32e09cca6c6d4ee8fb7ec93492655c72473e4',vh).replace('1ff94d6e48bb3b694d09ac467fc1dd630d471983fcc24335b2cd5c3c85aaf48b','550284bc2beba2db2221b16a61294034ec4cf1ada0d449b8b2f8fd70add74eb5').replace('mem>=19*1073741824','mem>=7*1073741824').replace('candidate6','candidate8').replace('candidate7','candidate8')
runner=runner.replace('root_reserved_memory=19*1073741824)','root_reserved_memory=19*1073741824,remaining_nonheavy_reservation=7*1073741824,active_heavy_authority="Root LONGowner3769329/tool2203; current MemAvailable reflects liveallocation")')
ast.parse(runner)
for dest in (r,n):
 with (dest/'run_materialization_and_pure.py').open('x') as f:f.write(runner)
launch={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','runner_sha256':sha(runner.encode()),'owner_sha256':oh,'validator_sha256':vh,'helper_sha256':'990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8','argv':['/usr/bin/taskset','-c','6','/usr/bin/prlimit','--as=2147483648:2147483648','--cpu=60:60','--fsize=33554432:33554432','--nofile=256:256','--core=0:0','--','/home/holden/anaconda3/bin/python3','-I','-B',str(n/'run_materialization_and_pure.py')],'shared_wall_seconds':90,'retirement_seconds':6,'active_heavy_root_authority':'LONGowner3769329/tool2203','root_declared_aggregate_GiB':19,'remaining_nonheavy_reserved_GiB':7,'actual_result':None,'compiler_build_native':None,'bounded_metadata_generation_history':['producer recipe newline syntax: initialfailedsource retained; correction1parsed/executedmetadataonly','wrapper generator unmatchedclosingparenthesis atASTparse beforevalidatorwrite/runtime: one boundedliteralcorrection here; no runtime retry']}
raw=(json.dumps(launch,indent=2,sort_keys=True)+'\n').encode()
for dest in (r,n):
 with (dest/'ACTUAL-COMBINED-LAUNCH.json').open('xb') as f:f.write(raw)
print(json.dumps({'launch_sha256':sha(raw),'owner':oh,'validator':vh},sort_keys=True))
