from pathlib import Path
import copy,importlib.util,json
P=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('future_guard',P/'native_exact_scratch22_authority3_image_guard_corrected.py');g=importlib.util.module_from_spec(s);s.loader.exec_module(g)
r=json.loads((P/'review-target-release-payload.json').read_text());o=json.loads(Path(r['prerequisites']['ordinary']['path']).read_text());a=json.loads(Path(r['ordinary_result_acceptance']['path']).read_text());q=json.loads(Path(r['request']['path']).read_text());identity=r['live_admission_required']['source_identity']
def check(ordinary,accepted,release):g.require_actual_ordinary(q,r['request']['sha256'],release,ordinary,accepted,identity)
check(o,a,r);labels=[]
for key in ['actual_inner_result','request','toolchain','materialization_receipt']:
 for field in ['path','sha256','bytes']:
  z=copy.deepcopy(a);z[key][field]=0 if field=='bytes' else 'CHANGED'
  try:check(o,z,r)
  except (RuntimeError,FileNotFoundError):labels.append(key+'.'+field)
  else:raise AssertionError('changed actual acceptance pointer accepted')
z=copy.deepcopy(a);z['actual_stage_results'][3]['result']['direct_child_joined']=False
try:check(o,z,r)
except RuntimeError:labels.append('consumer-directjoin')
else:raise AssertionError('unjoined consumer accepted')
print(json.dumps(dict(status='PASS_REAL_ACTUAL_ORDINARY_GUARD_JOINS',positive=1,negative=len(labels),compiler_or_guest=False)))
