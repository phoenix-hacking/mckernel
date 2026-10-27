"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only ordinary preparation candidate. No compiler, root, guest or subprocess.
Reuse existing image-record derivation and original235 overlay/manifest consumers.
"""
import argparse,contextlib,copy,gzip,hashlib,json,os,types
from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD='10972f87277e8429e2badd238d3ac53e451b8a2351a8ebf013941e1dfb95e1e2'
NEW='685ace3f1536a959198343d7c965e027dfd91f00b17b36e4d6906a177873087f'
PAIR=['887dc3567e6035c921588e61b45b41a8ef32a972d142fe2ba82ec48442353b12','57546af5110c0674b307e5ac5a328228abbe784f890f69521db5f594f21f6ae8']
def sha(raw):return hashlib.sha256(raw).hexdigest()
def need(ok,why):
 if not ok:raise ValueError(why)
def pinned(ref):
 p=Path(ref['path']);need(p.is_absolute() and p.resolve(strict=True)==p and not p.is_symlink(),'canonical input');raw=p.read_bytes();need(len(raw)==ref['size'] and sha(raw)==ref['sha256'] and p.stat().st_mode==ref['mode'],'exact source '+str(p));return raw
def module(ref,name):
 raw=pinned(ref);m=types.ModuleType(name);m.__file__=ref['path'];exec(compile(raw,ref['path'],'exec'),m.__dict__);return m

def prepare(path,digest):
 need(os.getuid()==os.geteuid()==1000,'ordinary UID1000 only')
 raw=Path(path).read_bytes();need(sha(raw)==digest,'exact input packet');d=json.loads(raw)
 out=HERE/'offline-preparation-1';need(d['output_directory']==str(out) and not os.path.lexists(out),'fresh exact private output')
 need(d.get('current_image_link_qualification') is not None,'new F03/F06 image qualification must be explicitly bound before materialization')
 for key in ['two_module_stage_receipt','two_module_stage_independent_acceptance','source_cohort_relation','scope_gap_decision','current_image_link_qualification','owner']:pinned(d[key])
 old=json.loads(pinned(d['inherited_strict235_manifest']));need(old['artifacts']['mckernel_image']==d['original_image'] and d['original_image']['sha256']==OLD,'preserve original10972 binding')
 need(d['new_image']['sha256']==NEW and [r['sha256'] for r in d['modules'][1:]]==PAIR,'explicit current290 and RustMM tuple')
 need(old['payload']['oracle']['exit_code']==0 and old['payload']['oracle']['stderr_hex']=='' and len(bytes.fromhex(old['payload']['oracle']['stdout_hex']))==235,'unchanged235 oracle')
 ov=module(d['overlay_module'],'existing_exact_overlay');p=module(d['record_deriver'],'existing_exact_record_deriver');nd=module(d['diagnostic_module'],'existing_exact_manifest_validator')
 with contextlib.ExitStack() as stack:
  sources={name:ov._Source(d[name]['path'],stack) for name in ['accepted_MM_base','new_image','payload','collector','launcher']}
  modules=[ov._Source(r['path'],stack) for r in d['modules']]
  for name,source in sources.items():need(source.sha256==d[name]['sha256'] and source.identity['st_size']==d[name]['size'],'FD-pinned source '+name)
  for source,reference in zip(modules,d['modules']):need(source.sha256==reference['sha256'] and source.identity['st_size']==reference['size'],'FD-pinned module')
  original_raw=gzip.decompress(sources['accepted_MM_base'].data);need(sha(original_raw)==d['accepted_MM_base_cpio']['sha256'] and len(original_raw)==d['accepted_MM_base_cpio']['size'],'accepted e62de6 cpio')
  before=ov._manifest(ov._replay_records(ov.parse_newc(original_raw)[0]));need(before['images/mckernel.img']['sha256']==OLD,'old image still in genuine MM base')
  for name,source in zip(['modules/ihk.ko','modules/ihk-smp-x86_64.ko','modules/mcctrl.ko'],modules):need(before[name]['sha256']==source.sha256,'MM base module tuple')
  derived,proof=p.derive_base_payloads(ov,original_raw,{'images/mckernel.img':(sources['new_image'].data,OLD)})
  after=ov._manifest(ov._replay_records(ov.parse_newc(derived)[0]));need(set(before)==set(after) and [k for k in before if before[k]!=after[k]]==['images/mckernel.img'],'only image record changes')
  need(after['images/mckernel.img']['sha256']==NEW,'current image selected')
  for source in list(sources.values())+modules:source.verify()
  out.mkdir(mode=0o700);runtime=out/'runtime-inputs';runtime.mkdir(mode=0o700)
  refs=[d['modules'][0]]
  for name,source in zip(['ihk-smp-x86_64.ko','mcctrl.ko'],modules[1:]):
   target=runtime/name;p.write(target,source.data);os.chmod(target,0o644);refs.append(p.ref(target))
  base=out/'f03-f06-current290-mm-base.cpio.gz';p.write(base,ov._gzip(derived));baseref=p.ref(base)
  overlay=out/'strict235.cpio.gz'
  receipt=ov.build_overlay(str(base),d['payload']['path'],d['collector']['path'],d['launcher']['path'],str(overlay),collector_sha256=d['collector']['sha256'],mcexec_sha256=d['launcher']['sha256'],payload_sha256=d['payload']['sha256'],base_sha256=baseref['sha256'],base_size=baseref['size'],base_cpio_sha256=sha(derived),base_cpio_size=len(derived))
  receiptpath=out/'strict235-overlay.json';p.js(receiptpath,receipt)
  m=copy.deepcopy(old);m['modules']=refs;m['cleanup_profile']['modules']=refs;m['artifacts']['mckernel_image']=d['new_image'];m['artifacts']['initramfs']=baseref;m['artifacts']['root_base']=baseref
  m['staging']=dict(base_initramfs=baseref,derived_initramfs=p.ref(overlay),collector=d['collector'],overlay_source=d['overlay_module'],overlay_manifest=p.ref(receiptpath))
  need(m['profile']==d['retained_guest_profile'] and m['payload']==old['payload'],'profile/payload oracle unchanged')
  nd._validate_manifest(m);p.js(out/'manifest.HOST-STATIC.json',m)
  for source in list(sources.values())+modules:source.verify()
  command=['/usr/bin/taskset','--cpu-list','6','/usr/bin/prlimit','--as=536870912','--cpu=30','--core=0','--fsize=134217728','--nofile=256','--','/usr/bin/python3','-I','-B',d['overlay_module']['path'],str(base),d['payload']['path'],d['collector']['path'],d['launcher']['path'],str(overlay),'--collector-sha256',d['collector']['sha256'],'--mcexec-sha256',d['launcher']['sha256'],'--payload-sha256',d['payload']['sha256'],'--base-sha256',baseref['sha256'],'--base-size',str(baseref['size']),'--base-cpio-sha256',sha(derived),'--base-cpio-size',str(len(derived))]
  result=dict(scope=__doc__.splitlines()[0],status='OFFLINE_F03_F06_IMAGE685ACE_RUSTMM_STRICT235_CANDIDATE_ONLY',old10972_MM_base=d['accepted_MM_base'],current_image=d['new_image'],changed_base_records=['images/mckernel.img'],raw_header_proof=proof,all_other_base_records_identical=True,modules=refs,original235_payload=d['payload'],collector=d['collector'],manifest=p.ref(out/'manifest.HOST-STATIC.json'),base=baseref,base_cpio_sha256=sha(derived),base_cpio_size=len(derived),overlay=p.ref(overlay),existing_overlay_equivalent_argv=command,already_materialized=True,do_not_replay_equivalent_argv=True,module_builds=0,image_builds=0,guest_runs=0,native_MM_changed_path_acceptance=False,current_physical=None,independent_execution_release=None,runtime_authority=None)
  p.js(out/'OFFLINE-PREPARATION-RESULT.json',result);print(json.dumps(result));return 0
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--inputs',required=True);parser.add_argument('--inputs-sha256',required=True);args=parser.parse_args();raise SystemExit(prepare(args.inputs,args.inputs_sha256))
