"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Eight actual source-authority/selection observations; no cpio/stage/root execution.
"""
from pathlib import Path
import copy,importlib.util,json
D=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('zombie_p05_stager',D/'stage_m05_two_generation.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
b=m.load_binding();old=m.authorities(b);assert len(old)==62;m.validate_selection(b['replacements'],old,b)
observations=['actual accepted zombie SDK and snapshot/62member baseline join','strict five-member selection/57 unchanged original members']
def refuses(label,change,selection=False):
 wrong=copy.deepcopy(b);change(wrong)
 try:m.validate_selection(wrong['replacements'],old,wrong)if selection else m.authorities(wrong)
 except ValueError:observations.append(label)
 else:raise AssertionError(label+' accepted')
refuses('wrong mixed mcctrl snapshot rejected',lambda q:q['replacements']['modules/mcctrl.ko'].update(sha256='0'*64))
refuses('wrong unchanged ihk-smp snapshot rejected',lambda q:q['replacements']['modules/ihk-smp-x86_64.ko'].update(sha256='0'*64))
refuses('changed SDK authority digest rejected',lambda q:q['authority']['current_SDK_acceptance'].update(sha256='0'*64))
refuses('unknown authority profile rejected',lambda q:q.update(authority_profile='unknown'))
refuses('strict40B workload oracle drift rejected',lambda q:q['payload_contract']['oracle'].update(stdout_hex=''),True)
refuses('missing launcher descriptor rejected',lambda q:q['replacements']['bin/mcexec'].update(sha256=None),True)
assert len(observations)==8
r=dict(scope=__doc__.splitlines()[0],status='PASS_8_ACTUAL_AUTHORITY_AND_SELECTION_OBSERVATIONS_NO_STAGE',observations=observations,stages=0,cpio_transformations=0,root_compiler_guest_operations=0)
(D/'AUTHORITY-ONLY-CHECK-RECEIPT.json').write_text(json.dumps(r,indent=2,sort_keys=True)+'\n');print(json.dumps(r))
