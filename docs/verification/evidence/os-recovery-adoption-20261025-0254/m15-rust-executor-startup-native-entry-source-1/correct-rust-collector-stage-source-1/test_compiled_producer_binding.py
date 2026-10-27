"""Functional OS only; no security testing. Pure data negative controls, no workloads."""
import copy,hashlib,importlib.util,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('proposed_correct_startup_data_binder',HERE/'bind_correct_collector.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
p,f,c,d,o=b.source_check();m=p['manifest_template'];good=dict(collector_sha256=p['collector']['sha256'],sources={'collector':dict(path=p['collector']['path'],sha256=p['collector']['sha256'])},final_map={'init':dict(sha256=p['collector']['sha256'],size=p['collector']['size'],mode=0o100755)})
b.check_collector(m,good,p,f,c);checks=['qualified startup producer artifact/profile/argv/env/cwd/oracle/limits joins PASS']
def reject(label,mutate):
 mm,rr,ff,cc=map(copy.deepcopy,(m,good,f,c));mutate(mm,rr,ff,cc)
 try:b.check_collector(mm,rr,p,ff,cc)
 except ValueError:checks.append(label);return
 raise AssertionError('accepted '+label)
reject('old c020 collector rejected',lambda m,r,f,c:m['staging']['collector'].update(sha256='c020a8e0ab43e222caf901d92bfecb2a8d8cf20ea0b539910a17a578f1fd12fc'))
reject('old noargs actual argv rejected',lambda m,r,f,c:m['payload'].update(argv=['/bin/mcexec','-t','1','0','/apps/app']))
reject('empty argument dropped rejected',lambda m,r,f,c:m['payload']['argv'].pop(6))
reject('compiled profile mismatch rejected',lambda m,r,f,c:c['argv'].pop(6))
reject('incorrect /init producer rejected',lambda m,r,f,c:r['final_map']['init'].update(sha256='0'*64))
reject('wrong compiled qualification artifact rejected',lambda m,r,f,c:f['actual_collector_artifact'].update(sha256='0'*64))
reject('weak stream quota rejected',lambda m,r,f,c:m['payload'].update(stdout_limit_bytes=2048))
reject('changed original oracle rejected',lambda m,r,f,c:m['payload']['oracle'].update(exit_code=41))
reject('different boot profile rejected',lambda m,r,f,c:c.update(startup_boot_argv=['/bin/native-boot','hidos','allow_oversubscribe']))
reject('incomplete HOST test qualification rejected',lambda m,r,f,c:f.update(actual_test_count=15))
result=dict(status='PASS_COMPILED_PRODUCER_SOURCE_BINDING_AND10_NEGATIVE_CONTROLS',checks=checks,actual_source_check=True,actual_composition=False,actual_owner_entry=False,current_free=None,runtime_authority=None)
with (HERE/'PURE-RESULT.json').open('x') as out:json.dump(result,out,indent=2,sort_keys=True);out.write('\n')
print(json.dumps(dict(status=result['status'],controls=len(checks),result_sha256=hashlib.sha256((HERE/'PURE-RESULT.json').read_bytes()).hexdigest())))
