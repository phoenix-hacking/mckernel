"""Prepare only ordinary metadata/argv after genuine image retirement; never tools/copies."""
from pathlib import Path
import argparse,hashlib,json,os,re,stat
R=Path(__file__).resolve().parent.parent;H=R/'heavy-proposal-1'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(65536),b''):h.update(b)
 return h.hexdigest()
def load(p,want):
 assert sha(p)==want
 return json.loads(p.read_text())
def observe_both(p,cap,allow_empty=False):
 assert p.is_absolute() and p.resolve()==p
 fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 with os.fdopen(fd,'rb') as f:
  a=os.fstat(f.fileno());assert stat.S_ISREG(a.st_mode) and a.st_nlink==1 and a.st_uid==1000 and (0<=a.st_size if allow_empty else 0<a.st_size) and a.st_size<=cap
  h=hashlib.sha256()
  for b in iter(lambda:f.read(65536),b''):h.update(b)
  z=os.fstat(f.fileno());named=p.lstat();fields=('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
  assert all(getattr(a,k)==getattr(z,k)==getattr(named,k) for k in fields)
 copyrow=dict(path=str(p),sha256=h.hexdigest(),dev=a.st_dev,inode=a.st_ino,bytes=a.st_size,uid=a.st_uid,gid=a.st_gid,mode=stat.S_IMODE(a.st_mode),mtime_ns=a.st_mtime_ns,ctime_ns=a.st_ctime_ns)
 enginerow=dict(path=str(p),sha256=h.hexdigest(),device=a.st_dev,inode=a.st_ino,size=a.st_size,uid=a.st_uid,gid=a.st_gid,mode=oct(stat.S_IMODE(a.st_mode)),nlink=a.st_nlink,mtime_ns=a.st_mtime_ns,ctime_ns=a.st_ctime_ns)
 return copyrow,enginerow
def observe(p,cap):return observe_both(p,cap)[0]
def observe_engine_authority(p,cap):return observe_both(p,cap,True)[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--image-release-sha256',required=True);p.add_argument('--request-sha256',required=True);p.add_argument('--owner-sha256',required=True);p.add_argument('--guard-sha256',required=True);p.add_argument('--postjoin-sha256',required=True);a=p.parse_args()
 q=load(R/'image-request.json',a.request_sha256);d=load(H/'image-execution-release.json',a.image_release_sha256);assert d['request']==dict(path=str(R/'image-request.json'),sha256=a.request_sha256)
 ownerpath=Path(q['owner_evidence_root'])/'owner-receipt.json';guardpath=Path(d['guard_capture'])/'guard-result.json';postpath=H/'image-guard-postjoin-readback.json'
 owner=load(ownerpath,a.owner_sha256);guard=load(guardpath,a.guard_sha256);post=load(postpath,a.postjoin_sha256)
 assert owner['status']=='PASS' and owner['exit_code']==0 and owner['retired'] is True and owner['terminal_container_retained'] is True and owner['cleanup_separately_required'] is True
 cid=owner['container_id'];assert re.fullmatch('[0-9a-f]{64}',cid)
 assert guard['container_id']==cid and guard['retired'] is True and guard['retained_for_separate_cleanup'] is True and guard['owner_receipt_sha256']==a.owner_sha256
 assert post['guard_direct_joined'] is True and post['root27_4_reacquired_after_join'] is True and post['guard_result_sha256']==a.guard_sha256 and post['owner_receipt_sha256']==a.owner_sha256
 build=Path(q['output_root'])/'build';out=H/'postbuild-readonly-1';assert not out.exists()
 paths={'cpu':build/'kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/cpu.c.o','process':build/'kernel/CMakeFiles/mckernel.img.dir/process.c.o','rust':build/'kernel/rust/mckernel_rust.o','image':build/'kernel/mckernel.img'}
 rows={k:observe(v,32*2**20) for k,v in paths.items()};assert sum(x['bytes'] for x in rows.values())<=32*2**20
 for relative in ['release-fp-regs-production/selected-cpu.o','release-fp-regs-production/fallback-cpu.o','release-fp-regs-production/native-mckernel_rust.o','release-fp-regs-production/legacy-mckernel_rust.o','release-tid-production/selected-process.o','release-tid-production/fallback-process.o']:assert (build/relative).is_file()
 for filename in ['production-abi-checks.json','release-fp-regs-production-checks.json','release-tid-production-checks.json']:
  proof=json.loads((Path(q['evidence_root'])/filename).read_text());assert proof['status']=='PASS',filename
 # Only now map future placeholders onto genuinely produced artifact paths.
 original=(R/'postbuild-14-INPUTS.json').read_text();plan=json.loads(original.replace(str(R/'FUTURE-image-preparation'),str(R)));assert len(plan['operations'])==14
 assert all(not any(arg.startswith('--debug-dump') or arg=='-w' for arg in op['argv']) for op in plan['operations']),'historical fullDWARF decoder replay not allowed'
 plan['completion_contracts_required']='All14 declared statuses/directjoins/FDhashes must join; peroperation expectedexit/classification is independently bound in actual observationrelease. Historical fullDWARFgap remainsOPEN; current symbol/descriptor metadata is not alloriginal14 acceptance.'
 plan['facts_consumer_v2']=str(R/'postbuild-consumer-v2/postbuild_four_leaf_facts_v2.py')
 old=Path('/home/holden/mckernel-work/host-preparation/rust-fp-release-image-preparation-20261018-1/heavy-proposal-1/postbuild-first-stage-1')
 copyplan=json.loads((old/'exact-four-copy-command.json').read_text().replace(str(old),str(out)));copyplan['argv'][-1]='ACTUAL_ARTIFACTS_SHA256_FROM_GENERATED_METADATA'
 out.mkdir(mode=0o700)
 def put(n,x):
  with (out/n).open('x') as f:json.dump(x,f,sort_keys=True,indent=2);f.write('\n')
 put('actual-artifacts.json',rows);artifactsha=sha(out/'actual-artifacts.json');copyplan['argv'][-1]=artifactsha
 copyplan['immutable_inputs']=dict(path=str(out/'actual-artifacts.json'),sha256=artifactsha)
 code=copyplan['argv'][-2];copyplan['manual_inline_copy_source']=dict(bytes=len(code.encode()),sha256=hashlib.sha256(code.encode()).hexdigest())
 copyplan['total_artifact_bytes']=sum(row['bytes'] for row in rows.values())
 copyplan['status']='ACTUAL_ARTIFACT_COMMAND_INPUTS_PENDING_OBSERVATION_RELEASE'
 put('exact-four-copy-command.json',copyplan);put('exact-14-command-plan.json',plan)
 roles=json.loads((H/'terminal-preparation-1/roles-and-pending-identities.json').read_text())['ARTIFACT_PATHS']
 authority=[dict(kind=kind,action=role['action'],original=observe_engine_authority(Path(role['original']),64*1024**2),retained=role['retained'],retained_authority_pending=role['action']=='reuse') for kind,role in sorted(roles.items())]
 assert len(authority)==21 and all('device' in row['original'] and 'size' in row['original'] and isinstance(row['original']['mode'],str) for row in authority)
 put('retention21-original-engine-authorities.json',authority)
 put('actual-role-bindings.json',dict(status='ACTUAL_ARTIFACT_IDENTITIES_AND_COMMANDS_ONLY_NOT_EXECUTED',container_id=cid,owner_sha256=a.owner_sha256,guard_sha256=a.guard_sha256,postjoin_sha256=a.postjoin_sha256,request_sha256=a.request_sha256,artifacts_sha256=artifactsha,copy_members=4,inspection_commands=14,retention_members=21,actual_copies=0,tools_run=0,cleanup_authority=False,compiler_or_native=False))
 print('PASS actual retired-owner metadata mapped:4copy/14inspection/21retention inputs only; no execution')
if __name__=='__main__':main()
