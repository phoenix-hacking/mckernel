"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure metadata/fixture tests only, no live guard or physical observation.
"""
import ast,copy,importlib.util,json
from pathlib import Path
source=Path(__file__).with_name('observe_current119_native_resources.py')
spec=importlib.util.spec_from_file_location('candidate',source);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
checker=m.load(m.CHECKER,'test_current119_metadata_only');capture=m.read(m.CAPTURE);parent=m.read(m.PARENT)
free=json.loads(Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/CURRENT119-POSTJOIN-CURRENTFREE-PREPARATION-1/actual-acceptance-1/CURRENT-FREE.ACTUAL.json').read_bytes())
actors=m.frontier(checker,free,capture,parent)
ledgerpath=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/ROOT68-CURRENT119-ADOPTION-1/ROOT68-NONCE-LEDGER.ACTUAL.json');boundarypath=ledgerpath.with_name('ROOT68-CURRENT-BOUNDARY.ACTUAL.json')
ledger=m.read(m.ref(ledgerpath));boundary=m.read(m.ref(boundarypath));m.validate_adoption(ledger,boundary,m.ref(ledgerpath),m.ACCEPTED_FREE,free,actors)
assert len(actors)==199 and len({(x['pid'],x['start']) for x in actors})==194
assert actors[-1]['pid']==2569587 and actors[-1]['group'] is None and actors[-2]['pid']==2569588 and actors[-2]['group']==2569588
for key,value in [('current_free',False),('independent',False),('implementation_ownership',True),('Root67',{}),('capture_positive_join',{}),('old_readonly_client_status','known')]:
 bad=copy.deepcopy(free);bad[key]=value
 try:m.frontier(checker,bad,capture,parent)
 except (ValueError,AssertionError):continue
 raise SystemExit('not refused '+key)
for key,value in [('positive_wait4_join',False),('process_group_absent',False),('signals_sent',1)]:
 bad=copy.deepcopy(parent);bad[key]=value
 try:m.frontier(checker,free,capture,bad)
 except (ValueError,AssertionError):continue
 raise SystemExit('not refused parent '+key)
tree=ast.parse(source.read_bytes());names={n.name for n in tree.body if isinstance(n,ast.FunctionDef)}
assert {'frontier','validate_route','observe'}<=names
assert 'validate_candidate(' not in source.read_text() and 'physical.configure(binding[\'physical_history_binding\'])' in source.read_text()
assert 'checker.BASE.validate_absence_reports([report],actors)' in source.read_text()
print('PASS actual accepted free, Root68 ledger/boundary and retained frontier 199 rows/194 identities; 9 negative synthetic refs and joins; no physical or guard invocation')
