"""One final-stop init-only stage using pinned existing CPIO transform/parser only."""
import argparse,contextlib,hashlib,importlib.util,json,os,resource,stat
from pathlib import Path
ENGINE=Path('/home/holden/mckernel-work/host-preparation/current-host-rust-pair-native-20261019-1/module_span_engine_cap16.py')
ENGINE_SHA='04e308a5bd8a3b6d80480763bcee6e629d61d815c618a6ae7cf89043575e8a1f'
CAP=64*1024**2

def need(value,label):
    if not value:raise ValueError(label)
def sha(value):return hashlib.sha256(value).hexdigest()
def stage(binding,expected):
    need(os.getuid()==1000 and os.sched_getaffinity(0)=={7},'UID1000/CPU7')
    need(0<resource.getrlimit(resource.RLIMIT_AS)[0]<=1073741824,'1GiBAS')
    need(sha(ENGINE.read_bytes())==ENGINE_SHA,'existing transform identity')
    spec=importlib.util.spec_from_file_location('cycle_existing_metadata_transform',ENGINE)
    e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e);ov=e.parser()
    with contextlib.ExitStack() as stack:
        src=ov._Source(binding,stack);need(src.sha256==expected,'whole binding')
        b=json.loads(src.data);need(b['schema']=='mckernel.current-pair-final-public-release-stage.v1','fixed stage schema')
        refs={}
        for key,r in b['inputs'].items():
            need(set(r)=={'path','sha256','bytes'},'whole ref3')
            obj=ov._Source(r['path'],stack);need(obj.sha256==r['sha256'] and len(obj.data)==r['bytes'],'whole input '+key);refs[key]=obj
        need(refs['recipe'].sha256=='8fa7b5587d928be1453d9755a585ab1040ede0e50b814721659787b0a89fbd4e','accepted recipe')
        need(refs['modules'].sha256=='e3d8c75acf0e691386415590a6982868bc868b898ae6f1a781e3d1f6081b0e56','all3 matched modules')
        need(refs['native'].sha256=='880f1f11d8587a3e56190014c1bd8c683cd41ef6d48603000444db328433289a','exact current native')
        native=json.loads(refs['native'].data);meta=json.loads(refs['meta'].data)
        ov._check_collector(refs['collector'].data)
        need(refs['final_consumer'].sha256=='112d41f52587f342659f94905edc1fc20c94aeb76d035e2d3bb75ddbb625bd32','frozen final-stop consumer')
        base=e.inflate(refs['base'].data);overlay=e.inflate(refs['overlay'].data)
        need(overlay.startswith(base) and sha(base)==meta['base_cpio_sha256'] and len(base)==meta['base_cpio_size'],'exact archive geometry')
        need(refs['base'].sha256==meta['base_sha256'] and refs['overlay'].sha256==meta['output_sha256'],'compressed input identities')
        suffix=overlay[len(base):];need(sha(suffix)==meta['overlay_sha256'],'suffix digest')
        old=ov._manifest(ov._replay_records(ov.parse_newc(overlay)[0]));need(old==meta['final_map'],'whole old replay map')
        member='bin/native-resource-release-probe';need(old[member]['sha256']=='e914699243b4440f31b58921c10c74252c4bea1ded7929bea129c69c348a3345' and old[member]['mode']==0o100755,'unchanged existing public-release helper')
        need(old['bin/native-lifecycle-probe']['sha256']=='d8132525b6126ee93fc5de4f59ac06eb83ffeb90f85225da585d89060dfb1248','existing strictstop helper')
        changed,proof=e.transform(suffix,refs['collector'].data,old['init'],ov,'init')
        output_raw=base+changed;need(len(output_raw)<=CAP,'same64MiBraw cap')
        new=ov._manifest(ov._replay_records(ov.parse_newc(output_raw)[0]))
        need(set(new)==set(old),'init-only unchanged member set')
        for name,row in old.items():
            omit={'size','sha256'} if name=='init' else set()
            need({k:v for k,v in row.items() if k not in omit}=={k:v for k,v in new[name].items() if k not in omit},'preserved final metadata '+name)
        compressed=ov._gzip(output_raw)
        need(len(compressed)+len(refs['collector'].data)+len(refs['final_consumer'].data)<CAP-2*1024**2,'same total64MiB output cap')
        for root,floor,growth in [('/home/holden',16*1024**3,8*1024**2),('/home/holden/mckernel-work/scratch',12*1024**3,CAP)]:
            v=os.statvfs(root);need(v.f_bavail*v.f_frsize>=floor+growth+640*1024**2,'capacity+growth+reserve')
        target=Path(b['output_root']);need(target.is_absolute() and target.parent.resolve()==target.parent,'canonical private parent')
        edge=ov._Path(str(target));stack.callback(edge.close)
        try:edge.lstat()
        except FileNotFoundError:pass
        else:raise ValueError('fresh output required')
        for obj in [src,*refs.values()]:obj.verify()
        edge.verify();os.mkdir(edge.name,0o700,dir_fd=edge.parent)
        fd=os.open(edge.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=edge.parent);stack.callback(os.close,fd);parent=os.fstat(fd);total=0
        def write(name,data,mode=0o600):
            nonlocal total
            need('/' not in name and total+len(data)<=CAP,'bounded output')
            f=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,mode,dir_fd=fd)
            with os.fdopen(f,'wb') as stream:os.fchmod(stream.fileno(),mode);stream.write(data);stream.flush();os.fsync(stream.fileno())
            total+=len(data)
        write('init',refs['collector'].data,0o755);write('final_release_capture.py',refs['final_consumer'].data);write('lifecycle.cpio.gz',compressed)
        collector_ref=dict(path=str(target/'init'),sha256=refs['collector'].sha256,size=len(refs['collector'].data),mode=0o100755)
        overlay_ref=dict(path=str(target/'lifecycle.cpio.gz'),sha256=sha(compressed),size=len(compressed),mode=0o100600)
        updated=dict(meta);updated.update(collector_sha256=refs['collector'].sha256,overlay_sha256=sha(changed),output_sha256=sha(compressed),size=len(compressed),final_map=new,output_identity=ov._identity(os.stat('lifecycle.cpio.gz',dir_fd=fd,follow_symlinks=False)))
        updated['sources']=dict(meta['sources']);updated['sources']['collector']=dict(path=collector_ref['path'],sha256=collector_ref['sha256'],identity=ov._identity(os.stat('init',dir_fd=fd,follow_symlinks=False)))
        mb=(json.dumps(updated,indent=2)+'\n').encode()
        native['staging']['collector']=collector_ref;native['staging']['derived_initramfs']=overlay_ref
        source=refs['stager_source'];need(source.path.path==str(Path(__file__).resolve()),'actual consumed stager source')
        write('stage_final_release.py',source.data)
        native['staging']['overlay_source']=dict(path=str(target/'stage_final_release.py'),sha256=source.sha256,size=len(source.data),mode=0o100600)
        native['staging']['overlay_manifest']=dict(path=str(target/'overlay-manifest.json'),sha256=sha(mb),size=len(mb),mode=0o100600)
        receipt=dict(status='PASS_SOURCE_BOUND_FINAL_PUBLIC_RELEASE_INIT_ONLY_STAGE_ONLY',native_acceptance=False,module_changes=[],base_bytes_preserved=True,unchanged_base_ref=b['inputs']['base'],init_header_proof=proof,added_member=None,changed_roles=['init'],second_stop_protocol_prepared=True,final_public_release_protocol_prepared=True,full_restoration_verified=False,input_refs=b['inputs'],binding_sha256=src.sha256)
        write('overlay-manifest.json',mb);write('native-manifest.json',(json.dumps(native,indent=2)+'\n').encode());write('stage-receipt.json',(json.dumps(receipt,indent=2)+'\n').encode())
        for obj in [src,source,*refs.values()]:obj.verify()
        edge.verify();need((edge.lstat().st_dev,edge.lstat().st_ino)==(parent.st_dev,parent.st_ino),'stable output');os.fsync(fd)
        return receipt
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--binding',required=True);p.add_argument('--binding-sha256',required=True);args=p.parse_args();r=stage(args.binding,args.binding_sha256);print(json.dumps({k:r[k] for k in ('status','native_acceptance','added_member','changed_roles')}))
