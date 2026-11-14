"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact UID1000 metadata publication and actual inherited full consumer/builders; no owner/backend invocation.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,stat,sys,time
D=Path(__file__).resolve().parent;S=D/'source'
M=Path('/home/holden/mckernel-work/scratch/p12s5l2/m.json');P=Path('/home/holden/mckernel-work/native-runs/l12b1/p')
MSHA='0c0c6e3bb3744665c5b4dddbfdd0977be39db25b78ca19392e5a380f7f0502f6'
assert sys.executable=='/home/holden/anaconda3/bin/python3' and sys.version_info[:3]==(3,9,12) and os.getuid()==os.geteuid()==1000
raw=(D.parent/'actual-stage-1/manifest.json').read_bytes();assert len(raw)==12903 and hashlib.sha256(raw).hexdigest()==MSHA
assert Path('/home/holden/mckernel-work/scratch').stat().st_dev==1828
# Already-published exact inodes are read back; never recreate/overwrite.
receipt=json.loads((D/'ACTUAL-METADATA-PUBLICATION.json').read_text())
assert receipt['status']=='PASS_EXCLUSIVE_METADATA_PUBLICATION' and M.read_bytes()==raw
for item in receipt['created_identities']:
 p=Path(item['path']);st=p.lstat()
 assert (st.st_dev,st.st_ino,st.st_uid,st.st_gid,oct(st.st_mode))==(item['dev'],item['inode'],item['uid'],item['gid'],item['mode'])
assert M.stat().st_nlink==1 and P.is_dir() and not P.is_symlink()
def load(p,name):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
cohort=json.loads((D/'COHORT-BINDINGS.json').read_bytes());o=load(S/'native_diagnostic_container_owner.py','actual_corrected_LONG_owner');g=o._long_transport();runner=load(S/'native_diagnostic_runner.py','actual_corrected_LONG_runner')
owner_sha=hashlib.sha256(Path(o.SELF).read_bytes()).hexdigest();assert owner_sha==cohort['native_diagnostic_container_owner.py']['sha256'] and o.SELF==str(S/'native_diagnostic_container_owner.py') and o.RUNNER==str(S/'native_diagnostic_runner.py')
diag,manifest=o.bound_manifest(str(M),MSHA)
assert Path(diag.__file__)==S/'native_diagnostic.py' and manifest['pair_long_session']==g.PROFILE
assert manifest['staging']['collector']['sha256']=='cb3bfbcd065e0cccf36d13afa4e0d09b45319fbb99ab36c2b088c136ecad192f'
rdiag,backend=runner._runtime();assert Path(rdiag.__file__)==S/'native_diagnostic.py' and Path(backend.__file__)==S/'native_diagnostic_backend.py'
parent=o.private_parent(str(P),True,fresh=True);assert parent==(P.stat().st_dev,P.stat().st_ino)
try:o._manifest_outside_writable_parent(str(M),str(M.parent))
except (ValueError,RuntimeError):pass
else:raise AssertionError('manifest inside writableparent accepted')
obj=object.__new__(o.DiagnosticOwner);obj.owner_sha=owner_sha;obj.manifest_path=str(M);obj.manifest_sha256=MSHA;obj.parent=P;obj.nonce=json.loads((D/'LONG-RELEASE.PROTOTYPE.NOT-EXECUTABLE.json').read_bytes())['nonce'];obj.name='nd-'+obj.nonce;obj.label='mckernel.native-diagnostic.owner='+obj.nonce;obj.long_requested=True;obj.long_release='/TESTONLY/unpublished-release.json';obj.long_release_sha='0'*64
inside=obj._inside_args();create=obj._create_argv();assert inside[1]==o.SELF and inside[inside.index('--owner-sha256')+1]==owner_sha
assert '--log-driver=none' in create and '--cpuset-cpus=2-5' in create and '--memory=12g' in create and str(S) in str(create)
# Actual production functions, canonical LF included; no authored execution grant.
prototype=json.loads((D/'LONG-RELEASE.PROTOTYPE.NOT-EXECUTABLE.json').read_bytes());canonical=g.canonical({k:v for k,v in prototype.items() if k!='independent_review'});assert canonical.endswith(b'\n') and g.digest(canonical)==hashlib.sha256(canonical).hexdigest()
assert prototype['status'] is None and prototype['expires_unix'] is None and prototype['independent_review'] is None
result=dict(scope=__doc__,status='PASS_ACTUAL_COHERENT_PUBLISHED_MANIFEST_OWNER_RUNNER_AND_BUILDERS',manifest_sha256=MSHA,collector_sha256=manifest['staging']['collector']['sha256'],source_rows=len(o.SOURCE_HASHES),readonly_roots=len(o.EXTRA_READONLY),owner_sha256=owner_sha,diagnostic_source_path=str(diag.__file__),inside_argv=inside,create_argv=create,canonical_prototype_payload_sha256=g.digest(canonical),canonical_LF=True,production_validate_release_realclock=None,release_published=False,actual_metadata_publication=receipt,backend_calls=0,root=0,Docker=0,workload=0,native_acceptance=False)
with (D/'ACTUAL-COHERENT-CONSUMER-RESULT.json').open('x') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('inside_argv','create_argv','actual_metadata_publication')}))
