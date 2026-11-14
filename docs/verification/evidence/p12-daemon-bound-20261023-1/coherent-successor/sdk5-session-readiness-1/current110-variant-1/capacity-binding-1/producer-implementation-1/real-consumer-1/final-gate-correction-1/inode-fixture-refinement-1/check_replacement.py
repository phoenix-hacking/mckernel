# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import json,runpy,sys
D=Path(__file__).resolve().parent
sys.argv=[str(D.parent/'check_consumer.py'),'check']
ns=runpy.run_path(str(D.parent/'check_consumer.py'))
serial=(D/'wire-pure-replaced').read_text()
assert 'ND_PAIR_LONG_COMPLETE ' not in serial
root=D/'work/workspace-final-10'
assert sorted(x.name for x in (root/'two-app').iterdir())==['work0','work1']
old=(root/'retained-old-work0').stat();new=(root/'two-app/work0').stat()
assert old.st_ino!=new.st_ino and old.st_dev==new.st_dev
assert (old.st_mode,old.st_uid,old.st_gid,old.st_nlink)==(new.st_mode,new.st_uid,new.st_gid,new.st_nlink)
try:ns['checker'].check_long_session(ns['manifest'],{'serial':serial},pair_check=ns['native']._pair_body)
except (ValueError,RuntimeError) as error:
 print(json.dumps(dict(status='PASS_PURE_REPLACED_WORKSPACE_IDENTITY_REJECTED_BY_REAL_DEFAULT_CALLBACK_AND_UNCHANGED_FULL_CONSUMER',error=str(error),complete_present=False,two_app_contents=['work0','work1'],retained_old_inode=old.st_ino,replaced_inode=new.st_ino,native_acceptance=False)))
else:raise AssertionError('unchanged full LONG consumer accepted pure inode replacement')

serial=(D/'wire-final-deadline').read_text()
assert 'ND_PAIR_LONG_COMPLETE 'not in serial
try:ns['checker'].check_long_session(ns['manifest'],{'serial':serial},pair_check=ns['native']._pair_body)
except (ValueError,RuntimeError) as error:print(json.dumps(dict(status='PASS_ACTUAL_FINAL_DEADLINE_GATE_UNCHANGED_FULL_CONSUMER_REJECTS',error=str(error),complete_present=False,native_acceptance=False)))
else:raise AssertionError('accepted final deadline')
