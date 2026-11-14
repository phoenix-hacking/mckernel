"""Functional OS only; no security testing. Synthetic producer data controls, no qualification or workload."""
from pathlib import Path
import copy,hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'m15-rust-executor-startup-native-entry-source-1/correct-rust-collector-stage-source-1'
spec=importlib.util.spec_from_file_location('retirement_data_binder_mock_only',HERE/'bind_retirement_collector.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
p=json.loads((HERE/'STAGE-PLAN.NOT-RELEASED.json').read_text());old=json.loads((OLD/'STAGE-PLAN.NOT-RELEASED.json').read_text())
f=json.loads(Path(old['compiled_collector_binding_facts']['path']).read_text());c=json.loads(Path(old['compiled_collector_profile']['path']).read_text())
# MOCK identities/count only. These are not written into the actual source plan.
p['collector']=dict(path='/mock/never-qualified-new-retirement-collector',sha256='a'*64,size=123,mode=0o100700)
p['compiled_collector_profile']=dict(path='/mock/profile',sha256='b'*64,size=1,mode=0o100600);p['qualified_actual_test_count']=22
f['actual_collector_artifact']=dict(path=p['collector']['path'],sha256='a'*64,bytes=123);f['actual_test_count']=22;f['source_caseprofile']['sha256']='b'*64
m=copy.deepcopy(p['manifest_template']);m['staging']['collector']=copy.deepcopy(p['collector']);good=dict(collector_sha256='a'*64,sources={'collector':dict(path=p['collector']['path'],sha256='a'*64)},final_map={'init':dict(sha256='a'*64,size=123,mode=0o100755)})
b.check_collector(m,good,p,f,c);rows=['synthetic newproducer exact22 profile/8argv/emptyarg/2env/91B/10s1024 and/init joins']
def reject(label,mutate):
 mm,rr,pp,ff,cc=map(copy.deepcopy,(m,good,p,f,c));mutate(mm,rr,pp,ff,cc)
 try:b.check_collector(mm,rr,pp,ff,cc)
 except ValueError:rows.append(label);return
 raise AssertionError(label+' accepted')
reject('old d0bf collector identity refuses',lambda m,r,p,f,c:m['staging']['collector'].update(sha256='d0bf61dc45754e72d3ebab34853756c6ce5cce0c9e84ac1713122ba1cf8f0d5a'))
reject('wrong process profile noargs refuses',lambda m,r,p,f,c:m['payload'].update(argv=['/bin/mcexec','-t','1','0','/apps/app']))
reject('empty argument dropped refuses',lambda m,r,p,f,c:m['payload']['argv'].pop(6))
reject('incorrect init refuses',lambda m,r,p,f,c:r['final_map']['init'].update(sha256='0'*64))
reject('different qualification artifact refuses',lambda m,r,p,f,c:f['actual_collector_artifact'].update(sha256='0'*64))
reject('stream cap widened refuses',lambda m,r,p,f,c:m['payload'].update(stdout_limit_bytes=2048))
reject('oracle changed refuses',lambda m,r,p,f,c:m['payload']['oracle'].update(exit_code=41))
reject('boot profile changed refuses',lambda m,r,p,f,c:c.update(startup_boot_argv=['/bin/native-boot','hidos']))
reject('missing one qualified test refuses',lambda m,r,p,f,c:f.update(actual_test_count=21))
reject('excess unqualified count refuses',lambda m,r,p,f,c:f.update(actual_test_count=23))
reject('unknown qualification count refuses',lambda m,r,p,f,c:p.update(qualified_actual_test_count=None))
reject('boolean qualification count refuses',lambda m,r,p,f,c:p.update(qualified_actual_test_count=True))
(HERE/'PURE-MOCK-RESULT.json').write_text(json.dumps(dict(scope=__doc__,status='PASS_SYNTHETIC_PRODUCER_DATA_CONTROLS',count=len(rows),checks=rows,synthetic_test_count22_not_actual_qualification=True,actual_collector_qualification=False,composition=False,owner_import=False,runtime_authority=None),indent=2)+'\n')
print(json.dumps(dict(status='PASS_SYNTHETIC_PRODUCER_DATA_CONTROLS',count=len(rows))))
