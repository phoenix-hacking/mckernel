"""One finite metadata materialization from real M03 acceptance/fetched proof.
No root, owner, compiler, backend, snapshot or process/socket effect is invoked.
"""
from pathlib import Path
import ast,hashlib,json,os,sys
SOURCE=Path(__file__).resolve().parent
D=SOURCE.parent;Q=D/'native-control-packet-4'

def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def typed(p):
 p=Path(p);r=ref(p);return dict(path=r['path'],sha256=r['sha256'],size=r['bytes'],mode=p.lstat().st_mode)
def load(p):return json.loads(Path(p).read_bytes())
def write(p,v):
 with p.open('x') as f:os.fchmod(f.fileno(),0o600);json.dump(v,f,indent=2,sort_keys=True);f.write('\n')
 return ref(p)

def m03_contract():
 import importlib.util
 p=Path(__file__).resolve().parent/'m03_protection_normalization_contract.py'
 assert p.parent==Path('/home/holden/mckernel-work/host-preparation/phase5-m03-protection-grace-runtime-binding-20261020-1/positive-s5-runtime-successor-1/non-temporal-source-6') and p.resolve()==p
 assert hashlib.sha256(p.read_bytes()).hexdigest()=='2a90a35fff7480997996547cd16ddef61ccab1928a806aa7c68f7557d0fb1953'
 spec=importlib.util.spec_from_file_location('exact_m03_protection_contract',p)
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
 assert len(sys.argv)==5,'ACTUAL_NORMALIZATION_REVIEW SHA256 COMPLETE_FETCHED_PROOF SHA256'
 a=typed(sys.argv[1]);assert a['sha256']==sys.argv[2]
 proof=ref(sys.argv[3]);assert proof['sha256']==sys.argv[4]
 role=m03_contract().validate(a);accept=role['report'];pre=role['preflight'];binding=role['binding'];facts=role['facts']
 c=load(Q/'STATIC-M03-NONTEMPORAL-INPUTS.SCHEMA-CORRECTED.PENDING.json')
 assert c['actual_preparation_acceptance']==a and c['actual_stage_acceptance']==accept['actual_stage_acceptance']
 assert c['binding']==binding and c['whole_manifest']==load(binding['manifest']['path'])
 parent=Path(binding['attempt_parent']);ps=parent.lstat()
 assert not list(parent.iterdir()) and not os.path.lexists(pre['paths']['attempt'])
 assert all(getattr(ps,k)==v for k,v in facts['parent_nine_field_identity'].items())
 owner=Path(c['runtime_owner']['path']);tree=ast.parse(owner.read_bytes())
 hashes=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SOURCE_HASHES' for t in n.targets)))
 assert c['runtime_source_hashes']==hashes and pre['paths']['qmp_socket_bytes']<=107
 c.update(actual_binding_result=accept['actual_binding_result'],actual_full_preflight=accept['actual_full_preflight'],actual_preparation_acceptance=a,binding=binding,consumed_paths=pre['consumed_paths'],fetched_runtime_proof=proof,whole_manifest=binding['manifest'],parent_identity=pre['parent_identity'],parent_nine_field_identity=facts['parent_nine_field_identity'],root_owner_argv=['/usr/bin/sudo','-A','/home/holden/anaconda3/bin/python3']+pre['owner_argv'][1:],accepted_owner_argv=pre['owner_argv'],inside_argv=pre['inside_owner_argv'],container_create_argv=pre['container_create_argv'],qemu_argv=pre['qemu_argv'],AF_UNIX=[dict(option='-qmp',path=pre['paths']['qmp_socket'],encoded_bytes=pre['paths']['qmp_socket_bytes'])],readonly_roots=pre['readonly_roots'],final_guard=ref(SOURCE/'review_final_205_release.py'),source_only_adapter=ref(SOURCE/'root_manual_snapshot_m03.py'),criterion='P-M03-01 selected valid-protection slice only',status='GENUINE_NON_TEMPORAL_M03_INPUTS_FETCHED_SOURCE_PROOF_BOUND_PENDING_FINAL_MAPPING_REVIEW')
 c['runtime_source_refs']=[ref(r['path']) for r in c['runtime_source_refs']]
 cref=write(Q/'STATIC-M03-NONTEMPORAL-INPUTS.SCHEMA-CORRECTED.json',c)
 command=load(SOURCE/'FINAL19-CHILD-COMMAND.PENDING.json')
 assert command['argv'][4:6]==[a['path'],a['sha256']]
 command_ref=write(SOURCE/'FINAL19-CHILD-COMMAND.REVIEW-PENDING.json',command)
 p=load(D/'S6-Q6-SOURCE-SCAFFOLD-PROPOSAL.json')
 p.update(status='FROZEN_FINITE_FINAL19_PENDING_WHOLE_MAPPING_REVIEW_AND_ROOT_GRANT',actual_normalization_acceptance=a,fetched_source_proof=proof,child_command_template=command_ref,source_pins=[ref(q) for q in sorted(SOURCE.glob('*.py'))]+[command_ref,cref,ref(Q/'FINAL-SEVEN-ROOT-CALL-DATA.PENDING.json'),ref(Q/'MANUAL-READBACK-CONTRACT.json')],static_decision=None,root_grant=None,execution_review=None)
 pr=write(D/'S6-Q6-FINAL19-MATERIALIZED-PROPOSAL.json',p)
 print(json.dumps(dict(proposal=pr,static_inputs=cref,source_count=len(hashes),steps=len(load(Q/'FINAL-SEVEN-ROOT-CALL-DATA.PENDING.json')['steps']),expected_outputs=len(p['final19_outputs']),executions=0)))
if __name__=='__main__':main()
