"""Functional OS only; no security testing. Synthetic original235 producer data controls, no workloads."""
from pathlib import Path
import copy,importlib.util,json
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('original235_data_binder_mock',HERE/'bind_process235_collector.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
p=json.loads((HERE/'STAGE-PLAN.NOT-RELEASED.json').read_text());c=json.loads(Path(p['compiled_collector_profile']['path']).read_text());p['collector']=dict(path='/mock/unqualified-process235-collector',sha256='a'*64,size=123,mode=0o100700);p['qualified_actual_test_count']=26
f=dict(case_id=c['case_id'],payload_argv=c['argv'],payload_cwd=c['cwd'],payload_env=c['env'],oracle=c['oracle'],actual_test_count=26,ignored=0,filtered=0,source_caseprofile=dict(sha256=p['compiled_collector_profile']['sha256']),actual_collector_artifact=dict(path=p['collector']['path'],sha256='a'*64,bytes=123),startup_boot_argv=c['startup_boot_argv'],limits={k:c[k] for k in ['stdout_limit_bytes','stderr_limit_bytes','payload_timeout_ms','post_reap_retirement_ms']})
m=copy.deepcopy(p['manifest_template']);m['staging']['collector']=copy.deepcopy(p['collector']);r=dict(collector_sha256='a'*64,sources={'collector':dict(path=p['collector']['path'],sha256='a'*64)},final_map={'init':dict(sha256='a'*64,size=123,mode=0o100755)})
b.check_collector(m,r,p,f,c);cases=['synthetic235 exactargv5/boot3/235B/env2/10s1024/5s compiled producer join']
def reject(label,mutate):
 mm,rr,pp,ff,cc=map(copy.deepcopy,(m,r,p,f,c));mutate(mm,rr,pp,ff,cc)
 try:b.check_collector(mm,rr,pp,ff,cc)
 except ValueError:cases.append(label);return
 raise AssertionError(label+' accepted')
reject('startup8argv crossuse refuses',lambda m,r,p,f,c:m['payload'].update(argv=['/bin/mcexec','-t','1','0','app','A','','B']))
reject('defaultonly startupboot refuses',lambda m,r,p,f,c:c.update(startup_boot_argv=['/bin/native-boot']))
reject('oldC020 identity refuses',lambda m,r,p,f,c:m['staging']['collector'].update(sha256='c020a8e0ab43e222caf901d92bfecb2a8d8cf20ea0b539910a17a578f1fd12fc'))
reject('newstartup33c identity refuses',lambda m,r,p,f,c:m['staging']['collector'].update(sha256='33c11bb60d337a2a8dd99fbb3b5d4cf9522f44996d3b36080dfd534f38dc6144'))
reject('F05908f identity refuses',lambda m,r,p,f,c:m['staging']['collector'].update(sha256='908f147ef0a61959becc20820d6e889aaf5eb4418adda0c99f13b3c3e6cf72a1'))
reject('wrong init hash refuses',lambda m,r,p,f,c:r['final_map']['init'].update(sha256='0'*64))
reject('oracle change refuses',lambda m,r,p,f,c:m['payload']['oracle'].update(exit_code=41))
reject('stream widening refuses',lambda m,r,p,f,c:m['payload'].update(stdout_limit_bytes=2048))
reject('incomplete actual controls refuses',lambda m,r,p,f,c:f.update(actual_test_count=25))
reject('unknown actual count refuses',lambda m,r,p,f,c:p.update(qualified_actual_test_count=None))
# Schema mistakes that blocked earlier wrappers remain explicitly rejected as data contracts.
stage=json.loads((HERE/'STAGING-RECEIPT.TEMPLATE.NOT-ACTUAL.json').read_text());assert isinstance(stage['source_manifest'],dict) and isinstance(stage['scratch_manifest'],dict) and stage['nonce'] is None and 'planned_attempt_parent' in stage
seq=json.loads((HERE/'NATIVE-PUBLICATION-AND-ENTRY-SEQUENCE.NOT-RELEASED.json').read_text());assert isinstance(seq['publication_template']['files'],list) and seq['publication_template']['status'] is None
cases+=['typedref staging schema/nonceNULL/plannedparent preserved','publication files flatlist and unknownactualstatus preserved']
(HERE/'PURE-MOCK-RESULT.json').write_text(json.dumps(dict(scope=__doc__,status='PASS_SYNTHETIC235_AND_DATA_SCHEMA_CONTROLS',count=len(cases),cases=cases,sourceprepared26_not_actualqualification=True,actualcompiler_compose_guard_query_native_calls=0,runtime_authority=None),indent=2)+'\n')
print(json.dumps(dict(status='PASS_SYNTHETIC235_AND_DATA_SCHEMA_CONTROLS',count=len(cases))))
