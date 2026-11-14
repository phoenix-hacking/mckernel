"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual create-argv destination coverage model; no Docker/container/guest observation.
"""
from pathlib import Path
import ast,hashlib,importlib.util,json,os,sys
D=Path(__file__).resolve().parent;S=D/'source'
OLD=Path('/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/capsule-successor-preparation-1/coherent-source-successor-1')
MODEL=Path('/home/holden/mckernel-work/host-preparation/m07-current-final-used-state-join-20261023-1/typed-runtime-successor-1/mount-destination-coverage-1/test_mount_destinations.py')
assert sys.executable=='/home/holden/anaconda3/bin/python3' and sys.version_info[:3]==(3,9,12) and os.getuid()==1000
raw=MODEL.read_bytes();assert hashlib.sha256(raw).hexdigest()=='5bf700e3e09d687b7de6cf69104e1ac15b02edccfc5b589d5b594c91b75c6fb2'
ns=dict(Path=Path,json=json);tree=ast.parse(raw);exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('parse','visible')],type_ignores=[]),str(MODEL),'exec'),ns);parse=ns['parse'];visible=ns['visible']
def load(p,n):
 spec=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
owner=load(S/'native_diagnostic_container_owner.py','corrected_mount_owner');old=load(OLD/'source/native_diagnostic_container_owner.py','failed_mount_owner')
def obj(o):
 x=object.__new__(o.DiagnosticOwner);x.parent=Path('/home/holden/mckernel-work/native-runs/l12b1/p');x.manifest_path='/home/holden/mckernel-work/scratch/p12s5l2/m.json';x.manifest_sha256='0c0c6e3bb3744665c5b4dddbfdd0977be39db25b78ca19392e5a380f7f0502f6';x.owner_sha=hashlib.sha256(Path(o.SELF).read_bytes()).hexdigest();x.nonce='TESTONLY_NO_LAUNCH';x.name='TESTONLY_NO_LAUNCH';x.label='TESTONLY_NO_LAUNCH';x.long_requested=True;x.long_release='/TESTONLY/UNPUBLISHED.json';x.long_release_sha='0'*64;return x
x=obj(owner);argv=x._create_argv();routes=parse(argv);priorroutes=parse(obj(old)._create_argv());diag,manifest=owner.bound_manifest(x.manifest_path,x.manifest_sha256)
inputs=set(owner.SOURCE_HASHES)|{owner.SELF,owner.RUNNER,x.manifest_path,*[str(p) for p in S.glob('*.py')]}
for section in ('artifacts','staging'):
 inputs.update(v['path'] for v in manifest[section].values())
inputs.update(v['path'] for v in manifest['modules']);inputs.update(manifest['cleanup_profile'][k]['path'] for k in ('consumer','provider'))
legacy='/home/holden/mckernel-work/host-preparation/p12-sdk5-session-successor-20261023-1'
historical=[p for p in owner.SOURCE_HASHES if Path(legacy) in Path(p).parents];assert historical
assert all(visible(p,priorroutes) is None for p in historical)
rows=[]
for p in sorted(inputs):
 route=visible(p,routes);assert route is not None,('missing or shadowed',p);rows.append(dict(path=p,effective_route=route))
assert len(owner.SOURCE_HASHES)==len(old.SOURCE_HASHES)==156
normalized={k.replace(str(D),str(OLD)):v for k,v in owner.SOURCE_HASHES.items()};changed=[k for k,v in old.SOURCE_HASHES.items() if normalized[k]!=v];assert all(k.startswith(str(OLD/'source')+'/') for k in changed)
# Full real loader above checks every retained historical digest; no bulk rehash in our fixture.
assert owner.EXTRA_READONLY[:-1]==[p.replace(str(OLD),str(D)) for p in old.EXTRA_READONLY] and owner.EXTRA_READONLY[-1]==legacy
inside=x._inside_args();assert inside[1]==owner.SELF and inside[inside.index('--owner-sha256')+1]==x.owner_sha
victim=historical[0];root=str(Path(victim).parent)
for shadow in [dict(src=None,dst=root,readonly=False,directory=True),dict(src=str(S),dst=root,readonly=True,directory=True),dict(src=victim,dst=victim,readonly=False,directory=False)]:assert visible(victim,routes+[shadow]) is None
assert visible(victim,[r for r in routes if r['dst']!=legacy]) is None
# No production function/control-flow AST changes except path/hash literal rebinding.
def nonconstants(p):
 t=ast.parse(p.read_text())
 class Strip(ast.NodeTransformer):
  def visit_Constant(self,n):return ast.copy_location(ast.Constant(value='LITERAL'),n)
 return {n.name:ast.dump(Strip().visit(n),include_attributes=False) for n in t.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
assert nonconstants(S/'native_diagnostic_container_owner.py')==nonconstants(OLD/'source/native_diagnostic_container_owner.py')
for name in ('canonical','digest','validate_release'):
 def f(p):return ast.dump(next(n for n in ast.parse(p.read_text()).body if isinstance(n,ast.FunctionDef) and n.name==name),include_attributes=False)
 assert f(S/'long_transport.py')==f(OLD/'source/long_transport.py')
result=dict(scope=__doc__,status='PASS_ACTUAL_CORRECTED_CREATEARGV_DESTINATION_COVERAGE_AND_STRICT_HOST_LOADER',owner_sha256=x.owner_sha,source_pins=156,historical_pins_restored=len(historical),required_paths=len(inputs),readonly_roots=len(owner.EXTRA_READONLY),actual_create_argv=argv,effective_routes=rows,changed_selected_source_hash_refs=changed,negative_controls=['failed_original_historical_root_uncovered','restored_root_removal_rejected','tmpfs_ancestor_shadow_rejected','foreign_readonly_ancestor_shadow_rejected','writable_child_shadow_rejected'],production_guard_AST_unchanged_except_literals=True,canonical_digest_validate_release_AST_identical=True,full_host_bound_manifest_pass=True,mount_namespace_execution=None,container_execution=None,guest_execution=None,release=None,runtime_parent_freshness=None,current_live_postjoin=None,limitations=['Destination model uses actual source create argv, not actual Docker namespace visibility.','Prior dfbb nonce/parent retained only for regression inputs; no fresh runtime/release is prepared or authorized.','Historical156 source guard map retained; changed selected cohort refs rebound mechanically.'])
with (D/'ACTUAL-MOUNT-COVERAGE-RESULT.json').open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('actual_create_argv','effective_routes')}))
