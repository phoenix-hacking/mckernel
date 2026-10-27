"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact F05 owned-child payload composition using retained generic primitives.
No compiler, subprocess, guest, nonce, grant, clock or runtime authority.
Actual materialization requires a separately reviewed final CURRENT109 F05 packet and Root ordinary grant.
"""
from pathlib import Path
import argparse,contextlib,copy,gzip,hashlib,json,os,re,types
HERE=Path(__file__).resolve().parent
FROZEN_SHA='713354bb732c1be3424912cc55dbc08c6df3ad8889abc3e8090922718c3ede48'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def need(ok,why):
    if not ok:raise ValueError(why)
def valid_ref(r):
    need(type(r) is dict and set(r)=={'path','size','sha256','mode'},'exact artifact reference')
    need(type(r['path']) is str and '\0' not in r['path'] and Path(r['path']).is_absolute() and '..' not in Path(r['path']).parts,'canonical absolute artifact path')
    need(type(r['size']) is int and r['size']>0 and type(r['mode']) is int and r['mode']&0o170000==0o100000,'regular nonempty artifact')
    need(type(r['sha256']) is str and re.fullmatch('[0-9a-f]{64}',r['sha256']) is not None,'artifact digest')
def validate(cfg,d,final=False):
    need(type(d) is dict and set(d)=={'schema_version','scope','case_id','CURRENT109_image','image_qualification','stage_review','output_directory','protected','nonce','admission','runtime_authority'},'specific F05 packet keys')
    need(d['schema_version']==1 and type(d['schema_version']) is int and d['scope']==cfg['scope'] and d['case_id']==cfg['protected']['case_id'],'F05 packet identity')
    need(d['protected']==cfg['protected'],'frozen payload/module/path/oracle/profile/bootstrap/AVX/trace/cleanup contract')
    need(d['output_directory']==cfg['output_directory'],'exact fresh private output path')
    need(all(d[k] is None for k in ['nonce','admission','runtime_authority']),'offline data only; no nonce/admission/runtime authority')
    if d['CURRENT109_image'] is None:
        need(d['image_qualification'] is None and d['stage_review'] is None and not final,'CURRENT109 image and actual review bindings are still NULL')
        return 'UNBOUND_CURRENT109_SOURCE_ONLY'
    valid_ref(d['CURRENT109_image'])
    need(d['CURRENT109_image']['sha256']==cfg['required_image_sha256'],'exact accepted CURRENT109 image')
    need(d['CURRENT109_image']['sha256'] not in cfg['disallowed_image_sha256'],'historical/current685 image is not CURRENT109')
    q=d['image_qualification'];need(type(q) is dict and set(q)=={'record','image_sha256'},'actual CURRENT109 image qualification reference')
    valid_ref(q['record']);need(q['image_sha256']==d['CURRENT109_image']['sha256'],'qualification names exact CURRENT109 image')
    valid_ref(d['stage_review'])
    return 'FINAL_DATA_BINDINGS_REQUIRE_ACTUAL_PINNED_FILES_AND_REVIEW'
def pinned(ref):
    valid_ref(ref);p=Path(ref['path'])
    need(p.resolve(strict=True)==p and not p.is_symlink(),'canonical pinned input')
    raw=p.read_bytes();need(len(raw)==ref['size'] and sha(raw)==ref['sha256'] and p.stat().st_mode==ref['mode'],'unchanged pinned input '+str(p));return raw
def module(ref,name):
    raw=pinned(ref);m=types.ModuleType(name);m.__file__=ref['path'];exec(compile(raw,ref['path'],'exec'),m.__dict__);return m
def stage(path,digest):
    need(os.getuid()==os.geteuid()==1000,'ordinary UID1000 only')
    raw=Path(path).read_bytes();need(sha(raw)==digest,'exact reviewed final input packet')
    frozen=(HERE/'FROZEN-F05-COMPOSITION.json').read_bytes();need(sha(frozen)==FROZEN_SHA,'frozen composition contract')
    cfg=json.loads(frozen);d=json.loads(raw);validate(cfg,d,final=True);p=cfg['protected']
    out=Path(d['output_directory']);need(out.parent.resolve(strict=True)==HERE and not os.path.lexists(out),'fresh private materialization only')
    # Review references are pinned inputs, not executable policy or authority.
    # Root review must substantively qualify the exact final image/packet and
    # preserve the known bootstrap/compiler provenance limitation.
    pinned(d['image_qualification']['record']);pinned(d['stage_review'])
    for key in ['payload_source','frozen_oracle','expected_stdout','template_manifest','host_qualification']:
        pinned(p[key])
    for value in p['source_capability'].values():
        if type(value) is dict and set(value)=={'path','size','sha256','mode'}:pinned(value)
    ov=module(p['overlay_module'],'accepted_fp_overlay');der=module(p['record_deriver'],'accepted_fp_image_deriver');nd=module(p['diagnostic_module'],'accepted_fp_validator')
    old=json.loads(pinned(p['template_manifest']))
    need(old['profile']==p['profile'],'retained resource profile')
    need(old['cleanup_profile']['consumer']==p['cleanup_profile']['consumer'] and old['cleanup_profile']['provider']==p['cleanup_profile']['provider'],'retained BEGIN consumer/provider')
    oracle=json.loads(pinned(p['frozen_oracle']));expected=pinned(p['expected_stdout'])
    need(sha(expected)==oracle['expected_stdout']['sha256'] and len(expected)==204 and bytes.fromhex(p['payload_contract']['oracle']['stdout_hex'])==expected,'original204B F05 oracle')
    with contextlib.ExitStack() as stack:
        refs={k:p[k] for k in ['base','payload','collector','launcher']};refs['image']=d['CURRENT109_image']
        sources={k:ov._Source(r['path'],stack) for k,r in refs.items()}
        modules=[ov._Source(r['path'],stack) for r in p['modules']]
        for k,s in sources.items():need(s.sha256==refs[k]['sha256'] and s.identity['st_size']==refs[k]['size'],'FD-pinned '+k)
        for s,r in zip(modules,p['modules']):need(s.sha256==r['sha256'] and s.identity['st_size']==r['size'],'FD-pinned module')
        original=gzip.decompress(sources['base'].data)
        need(sha(original)==p['base_raw']['sha256'] and len(original)==p['base_raw']['size'],'accepted RustMM raw base')
        before=ov._manifest(ov._replay_records(ov.parse_newc(original)[0]))
        need(before['images/mckernel.img']['sha256']==p['original_image']['sha256'],'accepted base image identity')
        for name,s in zip(['modules/ihk.ko','modules/ihk-smp-x86_64.ko','modules/mcctrl.ko'],modules):need(before[name]['sha256']==s.sha256,'unchanged base module tuple')
        derived,proof=der.derive_base_payloads(ov,original,{'images/mckernel.img':(sources['image'].data,p['original_image']['sha256'])})
        after=ov._manifest(ov._replay_records(ov.parse_newc(derived)[0]))
        need(set(before)==set(after) and [n for n in before if before[n]!=after[n]]==['images/mckernel.img'],'only image record changes')
        need(after['images/mckernel.img']['sha256']==d['CURRENT109_image']['sha256'],'exact CURRENT109 image selected')
        for s in list(sources.values())+modules:s.verify()
        out.mkdir(mode=0o700);runtime=out/'runtime-inputs';runtime.mkdir(mode=0o700);module_refs=[p['modules'][0]]
        for name,s in zip(['ihk-smp-x86_64.ko','mcctrl.ko'],modules[1:]):
            dest=runtime/name;der.write(dest,s.data);os.chmod(dest,0o644);module_refs.append(der.ref(dest))
        base=out/'current109-f05-mm-base.cpio.gz';der.write(base,ov._gzip(derived));base_ref=der.ref(base)
        overlay=out/'owned-processvm-204B.cpio.gz'
        receipt=ov.build_overlay(str(base),p['payload']['path'],p['collector']['path'],p['launcher']['path'],str(overlay),collector_sha256=p['collector']['sha256'],mcexec_sha256=p['launcher']['sha256'],payload_sha256=p['payload']['sha256'],base_sha256=base_ref['sha256'],base_size=base_ref['size'],base_cpio_sha256=sha(derived),base_cpio_size=len(derived))
        receipt_path=out/'f05-overlay.json';der.js(receipt_path,receipt)
        m=copy.deepcopy(old);m['case_id']=p['case_id'];m['modules']=module_refs;m['cleanup_profile']=copy.deepcopy(p['cleanup_profile']);m['cleanup_profile']['modules']=module_refs
        m['artifacts'].update(mckernel_image=d['CURRENT109_image'],payload=p['payload'],mcexec=p['launcher'],initramfs=base_ref,root_base=base_ref)
        m['payload']=copy.deepcopy(p['payload_contract'])
        m['staging']=dict(base_initramfs=base_ref,derived_initramfs=der.ref(overlay),collector=p['collector'],overlay_source=p['overlay_module'],overlay_manifest=der.ref(receipt_path))
        nd._validate_manifest(m);need(m['payload']==p['payload_contract'],'unchanged F05 oracle/argv/1024B limits')
        der.js(out/'manifest.HOST-STATIC.json',m)
        for s in list(sources.values())+modules:s.verify()
        result=dict(scope=cfg['scope'],status='OFFLINE_CURRENT109_F05_DATA_COMPOSITION_ONLY',image=d['CURRENT109_image'],manifest=der.ref(out/'manifest.HOST-STATIC.json'),modules=module_refs,payload=p['payload'],frozen_oracle=p['frozen_oracle'],base=base_ref,raw_cpio_sha256=sha(derived),raw_header_proof=proof,changed_base_records=['images/mckernel.img'],overlay=der.ref(overlay),guest_runs=0,runtime_authority=None,nonce=None,native_value_acceptance=False,review_references={'image':d['image_qualification'],'stage':d['stage_review']},do_not_replay_materialization=True)
        der.js(out/'OFFLINE-COMPOSITION-RESULT.json',result);return result
if __name__=='__main__':
    ap=argparse.ArgumentParser(allow_abbrev=False);ap.add_argument('--inputs',required=True);ap.add_argument('--inputs-sha256',required=True);args=ap.parse_args();print(json.dumps(stage(args.inputs,args.inputs_sha256)))
