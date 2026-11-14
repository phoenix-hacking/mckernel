"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite ordinary Root composition proposal. No compiler, subprocess, guard, lease or guest.
Root source adoption and reviewed ordinary grant required before calling this CLI.
"""
import contextlib,copy,gzip,hashlib,json,types,argparse
from pathlib import Path
D=Path(__file__).resolve().parent

def digest(b):return hashlib.sha256(b).hexdigest()
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),size=len(b),sha256=digest(b),mode=p.stat().st_mode)
def checked(r):
 p=Path(r['path']);assert not p.is_symlink() and p.resolve(strict=True)==p
 b=p.read_bytes();assert ref(p)==r,r['path'];return b

def module(r,name):
 b=checked(r);m=types.ModuleType(name);m.__file__=r['path'];exec(compile(b,r['path'],'exec'),m.__dict__);return m

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--plan-sha256',required=True);a=ap.parse_args()
 raw=(D/'MATCHING235-CURRENT115-PLAN.NOT-RELEASED.json').read_bytes();assert digest(raw)==a.plan_sha256;p=json.loads(raw)
 ov=module(p['overlay_helper'],'literal235_overlay');der=module(p['record_deriver'],'literal_image_record_deriver')
 old=json.loads(checked(p['accepted235_manifest']));oldreceipt=json.loads(checked(p['accepted235_overlay_receipt']))
 checked(p['accepted235_fullmap_review']);checked(p['new_image'])
 assert old['artifacts']['mckernel_image']==p['old_image'] and old['payload']==p['original_payload_contract']
 out=Path(p['planned_output_parent']);assert not out.exists() and out.parent==D
 refs=[p['base'],p['new_image'],old['artifacts']['payload'],old['staging']['collector'],old['artifacts']['mcexec']]
 with contextlib.ExitStack() as stack:
  ss=[ov._Source(r['path'],stack) for r in refs]
  for s,r in zip(ss,refs):assert s.sha256==r['sha256'] and s.identity['st_size']==r['size']
  base=gzip.decompress(ss[0].data);assert digest(base)==p['base_raw_sha256'] and len(base)==p['base_raw_size']
  before=ov._manifest(ov._replay_records(ov.parse_newc(base)[0]));assert before['images/mckernel.img']['sha256']==p['old_image']['sha256']
  derived,proof=der.derive_base_payloads(ov,base,{'images/mckernel.img':(ss[1].data,p['old_image']['sha256'])})
  after=ov._manifest(ov._replay_records(ov.parse_newc(derived)[0]));assert set(before)==set(after) and [k for k in before if before[k]!=after[k]]==['images/mckernel.img']
  for s in ss:s.verify()
  out.mkdir(mode=0o700);basepath=out/'current115-process235-base.cpio.gz';der.write(basepath,ov._gzip(derived));br=ref(basepath)
  archive=out/'current115-process235-overlay.cpio.gz'
  receipt=ov.build_overlay(str(basepath),refs[2]['path'],refs[3]['path'],refs[4]['path'],str(archive),collector_sha256=refs[3]['sha256'],mcexec_sha256=refs[4]['sha256'],payload_sha256=refs[2]['sha256'],base_sha256=br['sha256'],base_size=br['size'],base_cpio_sha256=digest(derived),base_cpio_size=len(derived))
  prior=oldreceipt['final_map'];final=receipt['final_map'];assert set(prior)==set(final) and [k for k in prior if prior[k]!=final[k]]==['images/mckernel.img']
  assert final['images/mckernel.img']['sha256']==p['new_image']['sha256']
  rp=out/'overlay.json';der.js(rp,receipt)
  m=copy.deepcopy(old);m['artifacts']['mckernel_image']=p['new_image'];m['artifacts']['initramfs']=br;m['artifacts']['root_base']=br;m['staging']['base_initramfs']=br;m['staging']['derived_initramfs']=ref(archive);m['staging']['overlay_manifest']=ref(rp)
  assert m['payload']==old['payload'] and m['modules']==old['modules'] and m['cleanup_profile']==old['cleanup_profile']
  der.js(out/'manifest.HOST-STATIC.json',m)
  for s in ss:s.verify()
  result=dict(scope=p['scope'],status='OFFLINE_IMAGE_ONLY_MATCHING235_NOT_NATIVE_RELEASE',image=p['new_image'],base=br,manifest=ref(out/'manifest.HOST-STATIC.json'),overlay=ref(archive),overlay_receipt=ref(rp),raw_cpio_sha256=digest(derived),raw_header_proof=proof,changed_final_map_records=['images/mckernel.img'],source_authority=None,capability=None,nonce=None,current_ledger=None,current_free=None,native_release=None,native_acceptance=None)
  der.js(out/'COMPOSITION-RESULT.json',result);print(json.dumps(result))
if __name__=='__main__':main()
