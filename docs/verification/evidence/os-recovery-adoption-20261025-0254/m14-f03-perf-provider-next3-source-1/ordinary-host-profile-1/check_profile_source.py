"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Unrun pure source check. No guard, main, grant validation, limits or workload.
"""
from pathlib import Path
import ast,hashlib,importlib.util,json,os
D=Path(__file__).resolve().parent;P=D.parent;E=P.parent
B=E/'ordinary-host-new12h-runner-source-1'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(p.read_text())
assert ref(P/'SOURCE-READY.json')['sha256']=='4cecde9baa9d4b80c14cf4ceaec308c37744512e744497855ab55414c4f5546c'
assert ref(P/'FUTURE-HOST-COMMAND-PLAN.NOT-GRANTED.json')['sha256']=='aac12d508eae342fd788255453a0899b66ba073dd3b0dff1d5ac6f4881ed516d'
assert ref(B/'run_new12h_host.py')['sha256']=='6e98a1fbcbce2e822a815a05516287e7122cbd8e06d43277134b27b70cf3ad34'
spec=importlib.util.spec_from_file_location('retained_source_profile_API_only',B/'run_new12h_host.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
p=read(D/'PROFILE.NOT-GRANTED.json');m.validate_profile(p);m.verify(p['inputs']+[x['plan'] for x in p['leaves']])
old=read(P/'FUTURE-HOST-COMMAND-PLAN.NOT-GRANTED.json');leaf=read(D/'LEAF-PLAN.NOT-GRANTED.json');reserve=read(D/'FULL-OUTPUT-GROWTH-RESERVE.json')
assert len(p['commands'])==7 and p['leaves'][0]['first']==0 and p['leaves'][0]['last']==6
assert p['leaves'][0]['expected_stdout']==old['expected_stdout']
assert reserve['host_growth_reserve_bytes']==p['host_growth_reserve_bytes']==8*2**30
assert sum(c['bytes'] for c in reserve['components'])==5760*2**20
assert next(c for c in reserve['components'] if c['kind']=='outer_command_streams')['bytes']==14*64*2**20
assert reserve['host_free_required_bytes']==24*2**30 and reserve['scratch_floor_bytes']==12*2**30
for i,(now,original) in enumerate(zip(p['commands'],old['commands'])):
 argv=[a.replace(old['future_output_root'],str(D/'future-output-1')) for a in original['argv']]
 if 1<=i<=4:argv=[str(D/'real-header-selector-witness.c') if a==str(P/'selector-witness.c') else a for a in argv]
 if i<6:argv=['/usr/bin/env','TMPDIR='+str(D/'future-output-1')]+argv
 assert now['argv']==argv and now['cwd']==str(P)
 assert Path(now['argv'][0]).is_absolute()
 assert now['argv_compact_json_LF_sha256']==hashlib.sha256((json.dumps(argv,separators=(',',':'))+'\n').encode()).hexdigest()
assert not os.path.lexists(D/'future-output-1') and not os.path.lexists(D/'future-capture-1')
assert not os.path.lexists(D/'ROOT-GRANT.ACTUAL-1.json')
g=read(D/'ROOT-GRANT.SCHEMA.NOT-A-GRANT.json');assert g['authorized'] is False and g['nonce'] is None
assert g['profile_sha256']==ref(D/'PROFILE.NOT-GRANTED.json')['sha256']
for n in ['prepare_profile.py','check_profile_source.py','qualify_retained.py']:ast.parse((D/n).read_text(),filename=str(D/n))
print(json.dumps(dict(status='PASS_SOURCE_PROFILE_ONLY',commands=7,pinned_inputs=len(p['inputs']),growth_reserve_bytes=8*2**30,mock_pairs_UNRUN=872,mock_traces_UNRUN=1744,ABI_words_UNRUN=16,compilers=0,tests=0,guards=0,resources=0,runtime=0)))
