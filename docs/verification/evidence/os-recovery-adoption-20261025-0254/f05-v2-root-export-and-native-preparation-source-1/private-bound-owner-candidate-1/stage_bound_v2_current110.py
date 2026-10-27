"""Functional McKernel OS/apps and Rust migration only; no security testing.
Reuse complete retained stager; actual bound F05v2 data and unchanged-module reuse.
Actual composition requires separate Root grant; importing starts nothing.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent
SOURCE=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/f05-final-native-preparation-new12h-1/stage_current109_f05_specific.py')
SOURCE_SHA='53d9bca0a07775c97a55719e19a57b2eb5eec3f3cffc0f5a2acc24c1f6f30d93'
FROZEN_SHA='d41ea260caf431ceabb211da3281adeabc870d9d99292946efe31133a611b369'
CHANGES=[('CURRENT109', 'CURRENT110'), ('current109-f05-mm-base.cpio.gz', 'current110-f05-mm-base.cpio.gz'), ("out.mkdir(mode=0o700);runtime=out/'runtime-inputs';runtime.mkdir(mode=0o700);module_refs=[p['modules'][0]]\n        for name,s in zip(['ihk-smp-x86_64.ko','mcctrl.ko'],modules[1:]):\n            dest=runtime/name;der.write(dest,s.data);os.chmod(dest,0o644);module_refs.append(der.ref(dest))", "out.mkdir(mode=0o700);module_refs=copy.deepcopy(p['modules'])")]

def bound_adapter():
 raw=SOURCE.read_bytes();assert hashlib.sha256(raw).hexdigest()==SOURCE_SHA
 source=raw.decode()
 for old,new in CHANGES:
  assert old in source
  if old!='CURRENT109':assert source.count(old)==1
  source=source.replace(old,new)
 spec=importlib.util.spec_from_file_location('literal_retained_f05_current110_context',SOURCE)
 module=importlib.util.module_from_spec(spec)
 exec(compile(source,str(SOURCE),'exec'),module.__dict__)
 assert module.__file__==str(SOURCE) and module.__spec__.origin==str(SOURCE)
 module.HERE=HERE;module.FROZEN_SHA=FROZEN_SHA
 return module

if __name__=='__main__':
 p=argparse.ArgumentParser(allow_abbrev=False);p.add_argument('--inputs',required=True);p.add_argument('--inputs-sha256',required=True);a=p.parse_args()
 print(json.dumps(bound_adapter().stage(a.inputs,a.inputs_sha256)))
