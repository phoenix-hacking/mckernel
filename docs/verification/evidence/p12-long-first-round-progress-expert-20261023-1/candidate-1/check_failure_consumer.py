# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import importlib.util,json,os
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('actualcheck',D/'check_consumer.py')
# Reuse only its exact source-bound manifest/module setup; check script itself
# is loaded with check mode for the preserved full positive and final negatives.
import sys
sys.argv=['check_consumer.py','check']
spec.loader.exec_module(m:=importlib.util.module_from_spec(spec))
a=D/os.environ.get('REAL_ATTEMPT','attempt-1')
positive=(a/'wire-final-0').read_text()
phase=(a/'bridge-0-work'/'controlled-phase-wire').read_text()
assert m.checker.check_long_session(m.manifest,{'serial':phase+positive},pair_check=m.native._pair_body)['successful_launches']==720
results=[]
for mode in range(6):
 serial=(a/('failure-'+str(mode)+'-work')/'wire').read_text()
 try:m.checker.check_long_session(m.manifest,{'serial':serial},pair_check=m.native._pair_body)
 except (ValueError,RuntimeError) as e:results.append({'mode':mode,'strict_consumer':'REJECTED','error':str(e)})
 else:raise AssertionError('accepted actual failure '+str(mode))
print(json.dumps({'healthy_phase_wire_full_consumer':'PASS','actual_error_wires':results,'native_acceptance':False}))
