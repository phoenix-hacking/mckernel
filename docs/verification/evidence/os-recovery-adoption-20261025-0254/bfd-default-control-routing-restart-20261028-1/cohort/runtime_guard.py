"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
BFD-only adapter. Actual Root successor and independent review must exist first.
"""
from pathlib import Path
import hashlib, importlib.util, json
D=Path(__file__).resolve().parent
OPERATION='bfd-current-default-two-tools'
# Disjoint copied source, never shared082b or frozen CURRENT116 code mutation.
GUARD_SHA='9eefd1469edc42a837d0fa4238475af5d07a1ecca631e9dba987a99cefafdb38'

def ref(path):
 path=Path(path);raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def subjects():
 p=json.loads((D/'PROFILE.SOURCE-ONLY.json').read_bytes())
 result={'BFD_profile':ref(D/'PROFILE.SOURCE-ONLY.json'),
         'BFD_request':ref(D/'REQUEST.SOURCE-ONLY.json'),
         'BFD_contract':ref(D/'CONTRACT.json'),
         'BFD_current_source_plan':p['inputs']['source_export_plan'],
         'actual_BFD_Root_adoption':p['actual_source_adoption'],
         'new_actual_Root61_or_latest_ledger':p.get('actual_root_ledger') or p['source_preparation_boundary']['ledger'],
         'new_actual_currentfree':p.get('native_custody_clearance') or p['source_preparation_boundary']['current_free']}
 for path in sorted(D.glob('*.py')):result['consumer:'+path.name]=ref(path)
 return result

def module():
 path=D/'operation_window_guard.py'
 if ref(path)['sha256']!=GUARD_SHA:raise ValueError('disjoint BFD window guard source bytes')
 spec=importlib.util.spec_from_file_location('bfd_disjoint_operation_window',path)
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 return m

def guard():
 m=module();binding=m.decode((D/'ROOT-OPERATION-BINDINGS.json').read_bytes())
 m.need(binding['author']=='/root' and binding['operation']==OPERATION,'actual Root BFD binding')
 expected=subjects();m.need(binding['expected_subjects']==expected,'exact BFD consumer cohort')
 return m.guard(OPERATION,binding['successor'],binding['independent_review'],expected)
