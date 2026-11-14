"""Actual current LAST shared known-kind reader; source-only positive/refusals."""
from pathlib import Path
import importlib.util
import json
import sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('m02_actual_current_LAST_source_consumer',P/'root_manual_snapshot_m03.py')
last=importlib.util.module_from_spec(spec);spec.loader.exec_module(last)
reader=last.m02_contract()
context=json.loads((P/'CURRENT-SOURCE-CONTEXT.json').read_bytes())
data=reader.checked(context['case_data'])
result=reader.read_source(data,context['stage_acceptance'],context['normalization_acceptance'])
assert result['source_acceptance']['current_owner']==data['current_owner']
# Full-reference refusal through exactly the real shared reader.
bad=dict(data,actual_source_closure_acceptance=dict(data['actual_source_closure_acceptance'],sha256='0'*64))
try:reader.read_source(bad,context['stage_acceptance'],context['normalization_acceptance'])
except ValueError as e:assert str(e)=='full reference drift'
else:raise AssertionError('changed current source descriptor accepted')
# Exercise exact kind predicate with one retained genuine object changed only in schema.
wrong=dict(result['source_acceptance'],schema='wrong-kind')
try:reader.kind(wrong,reader.SOURCE_KIND)
except ValueError as e:assert str(e)=='wrong genuine evidence kind'
else:raise AssertionError('wrong current source kind accepted')
# Source-only result cannot stand in for missing actual fresh-parent record.
try:reader.read(context['case_data'],None,context['stage_acceptance'],context['normalization_acceptance'])
except (TypeError,ValueError):pass
else:raise AssertionError('missing actual fresh-parent result accepted')
print(json.dumps(dict(status='PASS_ACTUAL_CURRENT_LAST_SHARED_SOURCE_READER_ONLY',positive_genuine7c_S5stage_normalization_b934=True,
    changed_fullref_refused=True,wrong_kind_refused=True,absent_actual_parent_refused=True,
    actual_fresh_parent=False,generated19=False,LAST_static_joins=False,native_timeout_acceptance=False)))
