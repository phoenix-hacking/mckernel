"""Functional McKernel source/data checks only; no security testing/runtime calls."""
from pathlib import Path
import ast,json
D=Path(__file__).resolve().parent;OLD=D.parent/'M14-PIPELINE-CONTROL-BINDING-PREPARATION-1/monotone-census-negative-facts-source-1';old=(OLD/'retire_exact_current118_stopped_container.py').read_text();new=(D/'retire_exact_current119_stopped_container.UNBOUND.py').read_text();normal=new.replace('CURRENT119','CURRENT118').replace('mckernel.current119-build','mckernel.current118-build').replace("parent['session_id']==b['parent_tool_session_id']","parent['session_id']==3240").replace("parent['actual_tool_response']['chunk_id']==b['parent_tool_chunk_id']","parent['actual_tool_response']['chunk_id']=='69d894'")
line=" need(r['billing_mode']=='included_only' and r['allow_prepaid_fallback'] is False and r['credit_metadata_only'] is True,'weekly only; historical credit is not spending authority')\n";assert normal.count(line)==1;normal=normal.replace(line,'')
start=normal.index(" build=ledger.get(b['ledger_key'],{});");end=normal.index(" source=authenticated(r['source_review'],True)",start)
oldstart=old.index(" build=ledger.get(b['ledger_key'],{});");oldend=old.index(" source=authenticated(r['source_review'],True)",oldstart)
normal=normal[:start]+old[oldstart:oldend]+normal[end:]
a=ast.parse(old);b=ast.parse(normal)
for x,y in zip(a.body,b.body):
 if isinstance(x,(ast.FunctionDef,ast.ClassDef)):assert ast.dump(x,include_attributes=False)==ast.dump(y,include_attributes=False),getattr(x,'name','unknown')
assert len(a.body)==len(b.body)
bind=json.loads((D/'BINDINGS.TEMPLATE.NOT-AUTHORITY.json').read_text());packet=json.loads((D/'NORMAL-RETIREMENT-PACKET.json').read_text());protected=json.loads((D/'PROTECTED-ORIGINALS.json').read_text());refs=packet['source_refs'];read=lambda r:json.loads(Path(r['path']).read_text());profile=read(refs['PROFILE.SOURCE-ONLY.json']);result=read(refs['worker_result']);plan=read(refs['output:plan.json']);terminal=read(refs['output:terminal.json'])
assert terminal['returncode']==terminal['state']['ExitCode']==0 and terminal['state']['Running']is False and terminal['state']['Pid']==0 and not terminal['state']['OOMKilled'];assert plan['commands']==profile['exact_commands']and len(result['commands'])==4
for n,(r,q)in enumerate(zip(result['commands'],plan['commands'])):assert r['index']==n and r['returncode']==0 and r['argv']==q['argv']and r['cwd']==q['cwd']
assert bind['parent_tool_join']is None and bind['parent_tool_chunk_id']is None and 'BINDINGS_SHA=None'in new
assert packet['native_custody_unchanged']is True and 'artifact_rejection'not in packet and protected['failed_source_evidence']==[]
assert len(packet['retained_actual_outputs'])==4 and all(any(p['path']==r['path']and p['sha256']==r['sha256']for p in protected['records'])for r in packet['retained_actual_outputs'])
assert any('UNKNOWN'in row['role']for row in bind['prior_actors']);assert len(bind['prior_actors'])==167;assert [x['pid']for x in bind['new_known_actors']]==[2549248,2550991]
assert "allowed=[['ps','-a'"in new and "['rm','--',self.b['cid']]"in new and "r['signals_allowed']==0 and r['records_released']==[]"in new
ns={'__file__':str(D/'retire_exact_current119_stopped_container.py')};exec(compile((D/'retire_exact_current119_stopped_container.py').read_text(),'actual119source','exec'),ns);actual=ns['bindings']();ns['validate_retained'](actual)
assert actual['parent_tool_session_id']==63230 and actual['parent_tool_chunk_id']=='3e3ef8'
ledger=json.loads(Path(actual['current_ledger']['path']).read_text());prior=json.loads(Path(actual['prior_ledger']['path']).read_text());entry=ledger['current119_build'];assert entry==actual['current_build_ledger_entry']and entry['container']==actual['cid']and entry['holder_tool_join']==actual['parent_tool_join'];assert ledger['consumed_nonces']==prior['consumed_nonces']+[actual['nonce']] and ledger['current_native_operation']==prior['current_native_operation']
assert entry['worker_result']==packet['source_refs']['worker_result'] and entry['container_terminal']==packet['source_refs']['output:terminal.json']and entry['actual_four_command_returncodes']==[0,0,0,0]
checks=['actual bound validate_retained pure API passes including genuine63230/3e3ef8 join; actual entire typed73nonce119entry exact','all predecessor function/class ASTs exact after declared119labels, parenttooldata, genuine119ledger schema and added included-only predicate normalization','actual exact4command profile/plan/results allrc0 and terminal stopped/Pid0/exit0/noOOM','all4actual hostoutput hashes protected and bindmount sources preserved','all accepted historical actors including UNKNOWN retained167 plus exact119holder/runner','no118artifactrejection imported as119fact, no records-release/signal authority','source remains UNBOUND pending genuine parent tool63230join/chunk; no live effect']
(D/'SOURCE-CHECKS.json').write_text(json.dumps(dict(status='PASS_SOURCE_DATA_BOUND_NOT_EXECUTION',checks=checks,no_actual_guard_or_proc_or_Docker=True),indent=2)+'\n');print('PASS',len(checks),'focused groups')
