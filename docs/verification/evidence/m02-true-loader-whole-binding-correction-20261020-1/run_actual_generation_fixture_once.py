"""Actual corrected generation bodies, isolated fixture outputs, no native authority."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
SOURCE=HERE/'current-sources'
FIXTURE=HERE/'actual-full-fixture-1'
SETTINGS=json.loads((HERE/'FIXTURE-SETTINGS.json').read_bytes())

def need(ok,why):
    if not ok:raise ValueError(why)
def ref(path):
    p=Path(path);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),mode=p.stat().st_mode)
def write(path,value):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as f:json.dump(value,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def run(argv,role,expected,timeout):
    out=FIXTURE/(role+'.stdout');err=FIXTURE/(role+'.stderr');begin=time.monotonic()
    with out.open('xb') as stdout,err.open('xb') as stderr:
        child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)  # Inherit owned session/group.
        st=Path('/proc/%d/stat'%child.pid).read_text();tail=st[st.rfind(')')+2:].split()
        identity=dict(pid=child.pid,start=int(tail[19]),pgid=int(tail[2]),sid=int(tail[3]))
        need(identity['pgid']==os.getpgrp() and identity['sid']==os.getsid(0),'nested child escaped owned group')
        try:rc=child.wait(timeout=timeout)
        except BaseException:
            if child.poll() is None:child.kill()
            child.wait(timeout=2);raise
    record=dict(argv=argv,identity=identity,returncode=rc,direct_joined=True,seconds=time.monotonic()-begin,stdout=ref(out),stderr=ref(err))
    write(FIXTURE/(role+'.json'),record)
    need(rc==expected,'unexpected nested command result '+role)
    return record

need(sys.executable=='/usr/bin/python3' and sys.version_info[:2]==(3,8),'frozen interpreter3.8')
need(os.sched_getaffinity(0)=={6},'reviewed CPU6')
# Exercise true production sibling loaders before any generated fixture output.
# Binder is the actual nested entry below; no source or loader object is replaced.
loader_rows=[]
for name in ('current_m02_contract.py','materialize_current_m02_once.py','root_manual_snapshot_m03.py','review_final_205_release.py','machine_assembly_caller.py'):
    path=SOURCE/name
    spec=importlib.util.spec_from_file_location('current_contract_real_loader_'+path.stem,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    need(Path(module.__file__).resolve()==path,'true production sibling loader path')
    loader_rows.append(ref(path))
    if name=='root_manual_snapshot_m03.py':
        loaded=module.m02_contract()
        need(Path(loaded.__file__).resolve()==SOURCE/'current_m02_contract.py','actual LAST production pinned sibling loader')
        need(ref(Path(loaded.__file__))==ref(SOURCE/'current_m02_contract.py'),'exact production contract source identity')
path=HERE/'prepare_current_parent_once.py'
spec=importlib.util.spec_from_file_location('current_contract_real_parent_loader',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
need(Path(module.__file__).resolve()==path,'true parent loader path');loader_rows.append(ref(path))
need(not os.path.lexists(FIXTURE),'fresh isolated fixture namespace')
need(not os.path.lexists(SETTINGS['parent_base']),'fresh isolated fixture scratch parent')
FIXTURE.mkdir(mode=0o700);fs=FIXTURE/'current-sources';fs.mkdir(mode=0o700)
for name in ['current_m02_contract.py','root_manual_snapshot_m03.py','review_final_205_release.py','machine_assembly_caller.py','bind_m03_handshake_native_packet.py','materialize_current_m02_once.py']:
    shutil.copyfile(SOURCE/name,fs/name);os.chmod(fs/name,0o600)
shutil.copyfile(HERE/'prepare_current_parent_once.py',FIXTURE/'prepare_current_parent_once.py');os.chmod(FIXTURE/'prepare_current_parent_once.py',0o600)
data=json.loads((HERE/'CURRENT-CASE-DATA.reader-bound.json').read_bytes());oldparent=data['binding']['attempt_parent'];oldnonce=data['binding']['nonce'];parent=SETTINGS['parent'];nonce=SETTINGS['nonce'];oldq=Path(data['output_namespace']);q=FIXTURE/'native-control-packet-fixture'
def argv(values):return [v.replace(oldparent,parent).replace(oldnonce,nonce) for v in values]
data.update(fixture_only=True,purpose='ISOLATED_ACTUAL_GENERATION_FIXTURE_NOT_PRODUCTION',binding=dict(data['binding'],attempt_parent=parent,nonce=nonce),prospective_parent=parent,prospective_attempt=parent+'/attempt-'+nonce,prospective_owner_evidence=parent+'.owner-'+nonce,output_namespace=str(q),QMP=dict(path=parent+'/attempt-'+nonce+'/qmp.sock',encoded_bytes=99,limit_bytes=107),prospective_full_argv={k:argv(v) for k,v in data['prospective_full_argv'].items()},prospective_root_owner_argv=argv(data['prospective_root_owner_argv']),final19_outputs=[str(q/Path(v).relative_to(oldq)) for v in data['final19_outputs']],capture_paths=[str(q/Path(v).relative_to(oldq)) for v in data['capture_paths']])
need(len(os.fsencode(data['QMP']['path']))==99,'fixture QMP99')
write(FIXTURE/'CURRENT-CASE-DATA.reader-bound.json',data)
context=json.loads((SOURCE/'CURRENT-SOURCE-CONTEXT.json').read_bytes());context.update(fixture_only=True,case_data=ref(FIXTURE/'CURRENT-CASE-DATA.reader-bound.json'),output_namespace=str(q),input_namespace=str(FIXTURE/'actual-current-inputs-1'),fresh_metadata_result=str(FIXTURE/'ACTUAL-FRESH-PARENT-AND-FULL-PREFLIGHT.json'),parent_metadata_entry=ref(FIXTURE/'prepare_current_parent_once.py'))
write(fs/'CURRENT-SOURCE-CONTEXT.json',context)
entry=FIXTURE/'invoke_actual_fixture_materializer.py'
entry.write_text("from pathlib import Path\nimport importlib.util,json,sys\nsys.dont_write_bytecode=True\np=Path(__file__).resolve().parent/'current-sources'\ns=importlib.util.spec_from_file_location('actual_fixture_materializer',p/'materialize_current_m02_once.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)\nc=json.loads((p/'CURRENT-SOURCE-CONTEXT.json').read_bytes())\nm.materialize(c,dict(path=None,sha256=None,bytes=None),None,True)\n")
positive=run(['/usr/bin/python3','-I','-B',str(entry)],'positive-full-generation',0,25)
need(positive['stderr']['bytes']==0,'positive fixture stderr')
need(not (q/'FINAL-SEVEN-ROOT-CALL-DATA.PENDING.json').exists(),'original missing-seed regression must not be papered over')
need(all(Path(v).is_file() for v in data['final19_outputs']),'all19 actual fixture files')
seven=json.loads((q/'FINAL-SEVEN-ROOT-CALL-DATA.json').read_bytes())
need(seven['fresh_capture_and_actual_command_paths']==data['capture_paths'],'actual whole49 fixture equality')
need(all(not os.path.lexists(v) for v in data['capture_paths']),'root capture namespace unexecuted')
whole=json.loads((FIXTURE/'ACTUAL-CURRENT-M02-NINETEEN-WHOLE-RESULT.json').read_bytes())
need(whole['fixture_only'] is True and whole['generated_LAST_static_joins'] is True,'actual fixture join body')
# All source code bytes used by the fixture equal the corrected production source.
for name in ('current_m02_contract.py','root_manual_snapshot_m03.py','review_final_205_release.py','machine_assembly_caller.py','bind_m03_handshake_native_packet.py','materialize_current_m02_once.py'):
    need((fs/name).read_bytes()==(SOURCE/name).read_bytes(),'fixture code identity '+name)
need((FIXTURE/'prepare_current_parent_once.py').read_bytes()==(HERE/'prepare_current_parent_once.py').read_bytes(),'fixture parent code identity')
bindings=json.loads((q/'ROOT-SNAPSHOT-BINDINGS.json').read_bytes())
lastspec=importlib.util.spec_from_file_location('actual_generated_fixture_LAST_terminal',fs/'root_manual_snapshot_m03.py')
last=importlib.util.module_from_spec(lastspec);lastspec.loader.exec_module(last)
loaded=last.m02_contract();need(Path(loaded.__file__).resolve()==fs/'current_m02_contract.py','actual fixture LAST pinned sibling loader')
last.terminal_joins(json.loads(Path(bindings['physical_review']['path']).read_bytes()),bindings)
need(bindings['physical_projection_source']['path']==data['failed_native_reader_candidate']['path'],'current failed physical decoder retained')
for row in bindings['source_pins']:
    need(hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['sha256'],'generated actual source-pin identity')
# Exact current LAST code against actual stale contract bytes: same full static join body.
stale=FIXTURE/'stale-contract-sources';stale.mkdir(mode=0o700)
for name in ('root_manual_snapshot_m03.py','CURRENT-SOURCE-CONTEXT.json'):
    shutil.copyfile(fs/name,stale/name)
old=Path('/home/holden/mckernel-work/host-preparation/phase5-exit7-accepted-timeout-preparation-20261020-1/runtime-data-preparation-1/correction-1/current-sources/current_m02_contract.py')
need(hashlib.sha256(old.read_bytes()).hexdigest()=='dfe26bad11ab24b0c8a6ec9865ad07e3691d9891a611393cd0b88d9d49be8ceb','genuine retained stale contract source')
shutil.copyfile(old,stale/'current_m02_contract.py')
stale_entry=FIXTURE/'stale-contract-refusal.py'
stale_entry.write_text("from pathlib import Path\nimport importlib.util,json,sys\nsys.dont_write_bytecode=True\np=Path(__file__).resolve().parent\ns=importlib.util.spec_from_file_location('exact_stale_contract_full_LAST',p/'stale-contract-sources/root_manual_snapshot_m03.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)\nb=json.loads((p/'native-control-packet-fixture/ROOT-SNAPSHOT-BINDINGS.json').read_bytes())\nm.fixture_static_joins(b)\n")
stale_result=run(['/usr/bin/python3','-I','-B',str(stale_entry)],'stale-contract-refusal',1,5)
need(b'AssertionError' in Path(stale_result['stderr']['path']).read_bytes() and b'm02_contract' in Path(stale_result['stderr']['path']).read_bytes(),'actual stale contract loader refusal')
# Genuine complete generated binding with a changed contract source hash must refuse.
identity_entry=FIXTURE/'source-identity-refusal.py'
identity_entry.write_text("from pathlib import Path\nimport importlib.util,json,sys\nsys.dont_write_bytecode=True\np=Path(__file__).resolve().parent\ns=importlib.util.spec_from_file_location('exact_source_identity_full_LAST',p/'current-sources/root_manual_snapshot_m03.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)\nb=json.loads((p/'native-control-packet-fixture/ROOT-SNAPSHOT-BINDINGS.json').read_bytes())\nrow=next(r for r in b['source_pins'] if r['path']==str(p/'current-sources/current_m02_contract.py'));row['sha256']='0'*64\nm.fixture_static_joins(b)\n")
identity_result=run(['/usr/bin/python3','-I','-B',str(identity_entry)],'source-identity-refusal',1,5)
need(b'frozen source' in Path(identity_result['stderr']['path']).read_bytes(),'actual source-identity refusal')
# Real production-role refusal using the same actual generated bindings and production wrapper.
prod=FIXTURE/'production-role-refusal.py'
prod.write_text("from pathlib import Path\nimport importlib.util,json,sys\nsys.dont_write_bytecode=True\np=Path(__file__).resolve().parent\ns=importlib.util.spec_from_file_location('fixture_must_not_be_production',p/'current-sources/root_manual_snapshot_m03.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)\nb=json.loads((p/'native-control-packet-fixture/ROOT-SNAPSHOT-BINDINGS.json').read_bytes())\nm.static_joins(b)\n")
production=run(['/usr/bin/python3','-I','-B',str(prod)],'production-role-refusal',1,5)
need(b'explicit fixture context boundary' in Path(production['stderr']['path']).read_bytes(),'exact production-role refusal')
# Actual binder full path with changed genuine seed reference. No missing local file is manufactured.
rs=FIXTURE/'refusal-sources';rs.mkdir(mode=0o700)
for f in fs.iterdir():
    if f.is_file() and f.name!='CURRENT-SOURCE-CONTEXT.json':shutil.copyfile(f,rs/f.name)
wrong=dict(context,seed_seven_data=dict(context['seed_seven_data'],sha256='0'*64),output_namespace=str(FIXTURE/'refused-output'))
write(rs/'CURRENT-SOURCE-CONTEXT.json',wrong)
a=data['actual_source_closure_acceptance'];physical=data['latest_exclusive_physical']
refusal=run(['/usr/bin/python3','-I','-B',str(rs/'bind_m03_handshake_native_packet.py'),a['path'],a['sha256'],physical['path'],physical['sha256']],'changed-seed-refusal',1,20)
need(b'full reference drift' in Path(refusal['stderr']['path']).read_bytes(),'exact changed seed descriptor refusal')
need(not (FIXTURE/'refused-output').exists(),'seed refusal before output writes')
write(FIXTURE/'FIXTURE-WHOLE.json',dict(status='PASS_ACTUAL_GENERATION_FIXTURE_ONLY',fixture_only=True,interpreter=sys.version,positive=positive,production_loader_rows=loader_rows,fixture_code_identity=True,current_failed_terminal_join=True,stale_contract_refusal=stale_result,source_identity_refusal=identity_result,production_role_refusal=production,changed_seed_refusal=refusal,final19=[ref(Path(v)) for v in data['final19_outputs']],capture_paths=data['capture_paths'],local_pending_seed_absent=True,actual_generated_LAST_fixture_join_body=True,production_parent_acceptance=False,fetched_source_proof=None,root_approval=None,runtime_release=None))
print(json.dumps(dict(status='PASS_ACTUAL_GENERATION_FIXTURE_ONLY',final19=19,captures=49,local_pending_seed_absent=True,production_role_refused=True,changed_seed_refused=True,production_parent=False,fetched_source_proof=None,runtime_release=None)))
