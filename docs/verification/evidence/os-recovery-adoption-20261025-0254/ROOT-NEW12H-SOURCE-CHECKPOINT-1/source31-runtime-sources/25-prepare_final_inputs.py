"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-invoked ordinary preparation only; no clock, compiler, container or grant.
"""
from pathlib import Path
import argparse,hashlib,json,os,re,stat
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import final_contract as mc

def write(path,raw):
 with Path(path).open('xb') as f:f.write(raw)
 os.chmod(path,0o600)
def copy_pinned(row,target):
 source=Path(row['source']['path']);mc.regular(source);before=source.stat();raw=source.read_bytes();after=source.stat()
 mc.need((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns),'source identity changed')
 mc.need(len(raw)==row['source']['bytes'] and mc.sha(raw)==row['source']['sha256'],'source digest differs')
 parent=mc.MIRROR
 for part in target.relative_to(mc.MIRROR).parts[:-1]:
  parent=parent/part
  if not parent.exists():parent.mkdir(mode=0o700)
  mc.need(parent.is_dir() and not parent.is_symlink() and mc.node(parent)['mode']==0o700,'private source directory')
 write(target,raw);os.chmod(target,row['mode'])

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--nonce',required=True);args=p.parse_args();nonce=args.nonce
 mc.need(os.getuid()==os.geteuid()==os.getgid()==os.getegid()==1000,'ordinary UID1000 preparation')
 mc.need(re.fullmatch('[0-9a-f]{32}',nonce) is not None,'Root fresh32hex nonce')
 ledger=json.loads(Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER25.json').read_bytes())
 mc.need(nonce not in ledger['consumed_nonces']+ledger['reserved_abandoned_unconsumed_nonces'],'fresh nonce excludes consumed/abandoned namespaces')
 mc.need(not mc.MIRROR.exists(),'source mirror already prepared; preserve and do not overwrite')
 for name in ['ADOPT-REQUEST.json','STATIC-INPUTS-PREPARED.NOT-RELEASED.json','OWNER-CAPTURE']:
  mc.need(not os.path.lexists(mc.HERE/name),'static preparation already exists; preserve '+name)
 if not mc.OUTPUT_PARENT.exists():mc.OUTPUT_PARENT.mkdir(mode=0o700)
 mc.need(mc.node(mc.OUTPUT_PARENT)['mode']==0o700,'private workspace mode')
 candidate=mc.OUTPUT_PARENT/('native-running-modules-candidate-'+nonce);evidence=mc.OUTPUT_PARENT/('native-running-modules-owner-'+nonce);admission=mc.OUTPUT_PARENT/('native-running-modules-admission-'+nonce);prepdir=mc.OUTPUT_PARENT/('preparation-'+nonce)
 for path in [candidate,evidence,admission,prepdir]:mc.need(not os.path.lexists(path),'fresh operation namespace required')
 mc.MIRROR.mkdir(mode=0o700)
 for row in mc.PREP['source_files']:copy_pinned(row,mc.MIRROR/row['relative'])
 (mc.MIRROR/mc.PREP['fixture_output_relative']).mkdir(mode=0o700)
 mc.verify_mirror(mc.MIRROR)
 candidate.mkdir(mode=0o700);(candidate/'fixture-output').mkdir(mode=0o700);prepdir.mkdir(mode=0o700)
 write(prepdir/'PREPARATION.SOURCE-ONLY.json',mc.PREPARATION.read_bytes())
 write(prepdir/'RETAINED-INPUTS.SOURCE-ONLY.json',(mc.HERE/'RETAINED-INPUTS.SOURCE-ONLY.json').read_bytes())
 fixture_identity=mc.node(candidate/'fixture-output')
 binding=dict(schema='mckernel.daemon-mock.precreated-output.v1',path=mc.PREP['container_output'],nonce=nonce,device=fixture_identity['device'],inode=fixture_identity['inode'],uid=1000,gid=1000,mode=0o700)
 write(prepdir/'OUTPUT-BINDING.ACTUAL.json',mc.canonical(binding))
 scratch=Path('/home/holden/mckernel-work/scratch');backing=scratch.parent/'scratch.ext4';st=backing.stat();bindingref=mc.ref(prepdir/'OUTPUT-BINDING.ACTUAL.json')
 request=dict(schema='mckernel.daemon-pinned-helper-suffix64-request.v1',candidate_sha=mc.CANDIDATE,image_id=mc.PREP['tool_image'],nonce=nonce,request_path=str(mc.HERE/'ADOPT-REQUEST.json'),preparation=dict(path=str(mc.PREPARATION),sha256=mc.PREPARATION_SHA),driver=dict(path=str(mc.DRIVER),sha256=mc.sha(mc.DRIVER.read_bytes())),input_root=str(mc.MIRROR),candidate_root=str(candidate),owner_evidence_root=str(evidence),lease_path=str(scratch/'native-running-external-modules.lease.json'),common_exclusion_path=str(scratch/'native-running-external-modules-operational-exclusion.json'),basis_identity=mc.node(scratch/'mckernel-exact-candidate-scratch-22-authority3-output'),candidate_identity=mc.node(candidate),input_identity=mc.node(mc.MIRROR),boot_id=mc.BOOT,timeout=mc.PREP['timeout'],disk_budget_bytes=mc.PREP['output_budget_bytes'],capture_budget_bytes=mc.PREP['capture_budget_bytes'],terminal_policy='remove-owned-terminal',output_parent_identity=mc.node(mc.OUTPUT_PARENT),backing_identity=dict(mc.node(backing),size=st.st_size,nlink=st.st_nlink),fixture_output_identity=fixture_identity,runtime_preparation_identity=mc.node(prepdir),output_binding={k:bindingref[k] for k in ('path','sha256')})
 mc.verify_request_inputs(request);write(mc.HERE/'ADOPT-REQUEST.json',mc.canonical(request))
 (mc.HERE/'OWNER-CAPTURE').mkdir(mode=0o700)
 result=dict(status='SAME_BYTE_STATIC_INPUTS_PREPARED_NOT_RELEASED',request=mc.ref(mc.HERE/'ADOPT-REQUEST.json'),source_tree=mc.PREP['source_tree_sha256'],source_mirror_identity=mc.node(mc.MIRROR),work_identity=mc.node(candidate),fixture_output_identity=fixture_identity,runtime_preparation_identity=mc.node(prepdir),compiler_commands=0,container_calls=0,runtime_authority=None)
 write(mc.HERE/'STATIC-INPUTS-PREPARED.NOT-RELEASED.json',mc.canonical(result));print(json.dumps(result))
if __name__=='__main__':main()
