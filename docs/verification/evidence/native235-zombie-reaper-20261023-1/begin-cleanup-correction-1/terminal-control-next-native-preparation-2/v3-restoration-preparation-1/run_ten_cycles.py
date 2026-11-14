"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Straight caller for existing reviewed batch+ProductionHooks; no embedded release.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os
HERE=Path(__file__).resolve().parent
RUNTIME=HERE/'reviewed-ten-cycle-successor'
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--spec',required=True);p.add_argument('--release',required=True);p.add_argument('--release-sha256',required=True);p.add_argument('--binding',required=True);p.add_argument('--binding-sha256',required=True);p.add_argument('--output',required=True);a=p.parse_args(argv)
 assert os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={7}
 batch=load('exact_zombie_batch',RUNTIME/'native_diagnostic_batch.py');hooks=load('exact_zombie_hooks',RUNTIME/'production_hooks.py')
 spec=json.loads(Path(a.spec).read_text());profile,cases=batch.validate_spec(spec);assert len(cases)==10
 # Existing ProductionHooks authenticates release/hash/source/exact ordered
 # operations/profile+tuple proof wrappers before its first admit/native call.
 adapter=hooks.ProductionHooks(batch,profile,cases,dict(path=a.release,sha256=a.release_sha256),dict(path=a.binding,sha256=a.binding_sha256),a.output)
 result=batch.run_batch(a.spec,a.output,hooks=adapter);print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
