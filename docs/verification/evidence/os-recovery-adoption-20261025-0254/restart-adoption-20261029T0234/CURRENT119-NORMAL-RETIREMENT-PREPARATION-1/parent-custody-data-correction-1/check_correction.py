"""Functional OS pure real-metadata correction checks; no security testing/effects."""
from pathlib import Path
import ast,json,copy
D=Path(__file__).resolve().parent;OLD=D.parent
ns={'__file__':str(D/'prepare_correction.py'),'__name__':'pure_parent_binding'};exec(compile((D/'prepare_correction.py').read_text(),'pure_parent_binding','exec'),ns)
proof=json.loads((D/'PARENT-PROOF-BINDING.json').read_text());row=ns['validate_parent_proof'](proof['accepted_free'],proof['raw_parent_join']);assert row==proof['appended_actor']and row['group']is None and row['pid']==2540830 and row['start']==110130087
old=json.loads((OLD/'BINDINGS.json').read_text());new=json.loads((D/'BINDINGS.json').read_text());assert len(old['prior_actors'])==167 and len(new['prior_actors'])==168;assert new['prior_actors'][:-1]==old['prior_actors']and new['prior_actors'][-1]==row;assert sum(x['pid']==2540830 for x in new['prior_actors'])==1;assert new['new_known_actors']==old['new_known_actors']
for key,value in old.items():
 if key not in ['prior_actors','actor_evidence','packet','protected','output_root_parent']:assert new[key]==value,key
assert new['actor_evidence']==old['actor_evidence']+[proof['raw_parent_join']]
# A genuine but unrelated Root119 holder-tool-join cannot stand in for capture parent.
try:ns['validate_parent_proof'](proof['accepted_free'],old['parent_tool_join'])
except ValueError:pass
else:raise AssertionError('unmatched genuine parent receipt accepted')
bad=copy.deepcopy(proof['raw_parent_join']);bad['sha256']='0'*64
try:ns['validate_parent_proof'](proof['accepted_free'],bad)
except ValueError:pass
else:raise AssertionError('mismatched parent hash accepted')
a=ast.parse((OLD/'retire_exact_current119_stopped_container.py').read_text());b=ast.parse((D/'retire_exact_current119_stopped_container.py').read_text())
def remove_pin(t):return ast.Module(body=[n for n in t.body if not(isinstance(n,ast.Assign)and any(isinstance(x,ast.Name)and x.id=='BINDINGS_SHA'for x in n.targets))],type_ignores=[])
assert ast.dump(remove_pin(a),include_attributes=False)==ast.dump(remove_pin(b),include_attributes=False)
oldfiles=json.loads((OLD/'RUNTIME-FILES.json').read_text());files=json.loads((D/'RUNTIME-FILES.json').read_text());assert len(files)==len(oldfiles)==12;assert {k for k in files if files[k]!=oldfiles[k]}=={'executor','bindings','packet','protected'}
module={'__file__':str(D/'retire_exact_current119_stopped_container.py'),'__name__':'pure_retained119'};exec(compile((D/'retire_exact_current119_stopped_container.py').read_text(),'pure_retained119','exec'),module);assert module['bindings']()==new;module['validate_retained'](new)
checks=['genuine immutable free8104 parent projection matches raw17959641 pid/birth, groupNone','old167 retained ordered exact, outerparent appended once gives168; builder identities unchanged','unrelated genuine parent ref and mismatched parent hash refused','executor AST identical except BINDINGS_SHA, no algorithm/schema change','runtime12 only executor/bindings/packet/protected refs propagate','actual corrected pure validate_retained passes, no guard/process/Docker call']
(D/'PURE-CORRECTION.json').write_text(json.dumps(dict(status='PASS_SOURCE_DATA_PARENT_CUSTODY_CORRECTION',checks=checks,prior_frontier=168,live_effects=False),indent=2)+'\n');print('PASS',len(checks),'focused correction groups')
