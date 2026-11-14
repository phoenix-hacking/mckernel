"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only P12 successor of the accepted M05 final-member stage transformer.
No extraction, compile, root operation, scratch write or runtime launch.
Execution requires completed independent producer/application/stage bindings.
"""
from pathlib import Path
from contextlib import ExitStack
import argparse,copy,hashlib,importlib.util,json,os,shutil
HERE=Path(__file__).resolve().parent
SDK={'images/mckernel.img','bin/mcexec','modules/ihk.ko','modules/ihk-smp-x86_64.ko','modules/mcctrl.ko'}
def need(ok,why):
    if not ok:raise ValueError(why)
def sha(data):return hashlib.sha256(data).hexdigest()
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def ref(path):
    s=path.stat();return dict(path=str(path),size=s.st_size,mode=s.st_mode,sha256=sha(path.read_bytes()))
def write(path,data):
    with path.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
def js(path,value):write(path,(json.dumps(value,indent=2)+'\n').encode())
def exact(row):
    data=Path(row['path']).read_bytes()
    need(sha(data)==row['sha256'] and len(data)==row.get('size',row.get('bytes')),'bound source '+row['path'])
    return data

def shifted_base_end(raw,old_end,selection,ov):
    """Count only final replaced records in the existing base prefix.
    The accepted rewrite body retains all other bytes/order/header metadata.
    """
    last={};pos=0
    while pos<len(raw):
        if raw[pos]==0:
            while pos<len(raw) and raw[pos]==0:pos+=1
            continue
        v=ov._fields(raw[pos:pos+110]);ne=pos+110+v[11]
        name=raw[pos+110:ne-1].decode('utf-8')
        if name.startswith('./'):name=name[2:]
        ds=(ne+3)&~3;end=(ds+v[6]+3)&~3
        if name in selection:last[name]=(pos,end,v[6])
        pos=end
    need(set(last)==set(selection),'all selected final records exist')
    growth=sum(((len(selection[name])+3)&~3)-((oldsize+3)&~3)
               for name,(begin,end,oldsize) in last.items() if end<=old_end)
    need(all(not(begin<old_end<end) for begin,end,size in last.values()),'base split is record aligned')
    return old_end+growth

def stage(b):
    need(b['status']=='READY_FOR_REVIEWED_HOST_STAGE','pending producer/payload/review binding; no candidate2 staging')
    need(b['producer_artifact'] is not None and b['producer_review'] is not None and
         b['application_review'] is not None and b['reviewed_stage_profile'] is not None,'complete actual review dependencies')
    for name in ('producer_review','application_review','reviewed_stage_profile'):exact(b[name])
    # Capacity values are selected externally by the dispatcher; never infer or
    # lower reserves from a capsule size or reuse fixture reserve values.
    need(all(type(b[k]) is int and b[k]>0 for k in ('host_stage_growth_bytes','host_floor_bytes','scratch_floor_bytes')),'reviewed HOST stage envelope')
    need(shutil.disk_usage(HERE).free>=b['host_floor_bytes']+b['host_stage_growth_bytes'],'fresh HOST floor plus full stage growth')
    need(shutil.disk_usage('/home/holden/mckernel-work/scratch').free>=b['scratch_floor_bytes'],'readonly scratch input floor')
    out=HERE/'actual-stage-1';need(not os.path.lexists(out),'fresh stage output')
    need(not any(p.is_symlink() for p in (HERE,*HERE.parents)),'canonical HOST output')
    exact(b['overlay_source']);ov=load('retained_p12_newc',b['overlay_source']['path'])
    exact(b['member_transformer']);helper=load('accepted_m05_final_record_transform',b['member_transformer']['path'])
    old_manifest=json.loads(exact(b['baseline_manifest']));old_om=json.loads(exact(b['baseline_overlay_manifest']));old=old_om['final_map']
    need(len(old)==62,'exact inherited pair membership')
    selected=dict(b['SDK5_replacements']);selected['init']=b['producer_artifact']
    need(set(selected)==SDK|{'init'},'six production tuple/init replacements')
    need(type(b['application_replacements']) is dict and set(b['application_replacements'])<={'apps/app0','apps/app1'},'only explicitly accepted payload variants')
    selected.update(b['application_replacements'])
    with ExitStack() as stack:
        source=ov._Source(b['baseline_capsule']['path'],stack)
        need(source.sha256==b['baseline_capsule']['sha256'],'exact old complete capsule')
        inputs={name:ov._Source(row['path'],stack) for name,row in selected.items()}
        for name,item in inputs.items():
            need(item.sha256==selected[name]['sha256'] and len(item.data)==selected[name]['size'],'replacement exact '+name)
        raw=ov._inflate(source.data,b['max_inflated_bytes'])
        need(ov._manifest(ov._replay_records(ov.parse_newc(raw)[0]))==old,'actual predecessor map')
        data={name:item.data for name,item in inputs.items()}
        helper.MEMBERS=set(data) # Data-only six/eight-member selection; unchanged accepted transformation body.
        patched=helper.rewrite_last_records(raw,data,ov)
        new_end=shifted_base_end(raw,old_om['base_cpio_size'],data,ov)
        final=ov._manifest(ov._replay_records(ov.parse_newc(patched)[0]))
        need(set(final)==set(old) and len(final)==62,'no member additions/removals')
        for name in old:
            expected=dict(old[name])
            if name in selected:expected.update(size=len(data[name]),sha256=sha(data[name]))
            need(final[name]==expected,'exact retained metadata/final payload '+name)
        need(len(patched)<=b['max_patched_bytes'],'reviewed raw capsule bound')
        os.umask(0o077);out.mkdir(mode=0o700)
        collector=out/'collector-long-0755';write(collector,data['init']);collector.chmod(0o755)
        base=out/'base-sdk5.cpio.gz';capsule=out/'lifecycle-long.cpio.gz'
        write(base,ov._gzip(patched[:new_end]));write(capsule,ov._gzip(patched))
        # Reuse complete inherited pair contract; only explicit payload refs may
        # change, and original functional output/exit oracles remain identical.
        m=copy.deepcopy(old_manifest);m.pop('pair_rounds',None);m['pair_long_session']=b['LONG_profile'];m['case_id']=b['case_id'];m['cleanup_profile']=b['cleanup_profile']
        m['modules']=[selected[n] for n in ('modules/ihk.ko','modules/ihk-smp-x86_64.ko','modules/mcctrl.ko')]
        m['artifacts']['mckernel_image']=selected['images/mckernel.img'];m['artifacts']['mcexec']=selected['bin/mcexec']
        for i,a in enumerate(m['pair']['apps']):
            member='apps/app'+str(i)
            if member in selected:a['payload']=selected[member]
            need(a['oracle']==old_manifest['pair']['apps'][i]['oracle'],'original app oracle preserved')
        m['artifacts']['payload']=m['pair']['apps'][0]['payload'];m['artifacts']['initramfs']=m['artifacts']['root_base']=ref(base)
        om=copy.deepcopy(old_om);om.update(base_cpio_sha256=sha(patched[:new_end]),base_cpio_size=new_end,base_sha256=ref(base)['sha256'],collector_sha256=sha(data['init']),mcexec_sha256=sha(data['bin/mcexec']),payload_sha256=m['artifacts']['payload']['sha256'],final_map=final,output_identity=ov._identity(capsule.stat()),output_sha256=ref(capsule)['sha256'],overlay_sha256=sha(patched[new_end:]),size=capsule.stat().st_size)
        om['sources']={name:{'path':row['path'],'sha256':row['sha256'],'identity':ov._identity(Path(row['path']).stat())} for name,row in {'base':ref(base),'collector':ref(collector),'payload':m['artifacts']['payload'],'mcexec':m['artifacts']['mcexec']}.items()}
        om_path=out/'overlay-manifest.json';js(om_path,om)
        m['staging'].update(base_initramfs=ref(base),derived_initramfs=ref(capsule),collector=ref(collector),overlay_manifest=ref(om_path),overlay_source=b['overlay_source'])
        manifest=out/'manifest.json';js(manifest,m)
        for item in (source,*inputs.values()):item.verify()
        exact(b['diagnostic_source']);nd=load('strict_current110_LONG',b['diagnostic_source']['path']);nd.load_manifest(str(manifest))
        used=sum(p.stat().st_size for p in out.iterdir());need(used<b['host_stage_growth_bytes']-(1<<20),'stage receipt/full output growth')
        result=dict(status='PASS_HOST_LONG_CAPSULE_STAGE_ONLY',manifest=ref(manifest),capsule=ref(capsule),base=ref(base),collector=ref(collector),overlay_manifest=ref(om_path),member_count=62,changed_members=sorted(selected),aggregate_bytes_before_receipt=used,scratch_writes=0,native_acceptance=False)
        js(out/'stage-result.json',result);return result
if __name__=='__main__':
    ap=argparse.ArgumentParser(allow_abbrev=False);ap.add_argument('--binding',required=True);args=ap.parse_args()
    print(json.dumps(stage(json.loads(Path(args.binding).read_text())),sort_keys=True))
