"""Actual metadata-only guard-entry regression; no compiler/Docker/root."""
from pathlib import Path
import copy,importlib.util,json
H=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('fresh_full_guard',H/'native_exact_scratch22_authority3_image_guard_corrected.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
r=json.loads((H/'review-target-release-payload.json').read_bytes());q=json.loads(Path(r['request']['path']).read_bytes());o=json.loads(Path(r['prerequisites']['ordinary']['path']).read_bytes());a=json.loads(Path(r['ordinary_result_acceptance']['path']).read_bytes());identity=r['live_admission_required']['source_identity']
def check(accepted,release):g.require_actual_ordinary(q,r['request']['sha256'],release,o,accepted,identity)
check(a,r);labels=[]
for key in ('actual_request','actual_result','driver','owner','actual_consumer_receipt'):
 for field in ('path','sha256','bytes'):
  v=copy.deepcopy(a);v[key][field]=0 if field=='bytes' else 'CHANGED'
  try:check(v,r)
  except (RuntimeError,FileNotFoundError):labels.append(key+'.'+field)
  else:raise AssertionError('changed accepted metadata ref accepted')
v=copy.deepcopy(a);v['actual_stages'][1]['direct_child_joined']=False
try:check(v,r)
except RuntimeError:labels.append('consumer-directjoin')
else:raise AssertionError('unjoined consumer accepted')
print(json.dumps(dict(status='PASS_ACTUAL_FRESH_FULL_METADATA_GUARD_JOINS_ONLY',positive=1,negative=len(labels),compiler_or_root_container=False)))
