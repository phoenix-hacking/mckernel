"""Finite two-app derivative of the retained overlay/staging path; never runs guests."""
from pathlib import Path
import argparse,copy,gzip,hashlib,importlib.util,json,os,stat
R=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def ref(path):
    p=Path(path);s=p.stat();return {'path':str(p),'sha256':sha(p.read_bytes()),'size':s.st_size,'mode':s.st_mode}
def exact(r):
    if ref(r['path'])!=r:raise ValueError('changed source '+r['path'])
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def write(p,b):
    with p.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
def js(p,v):write(p,(json.dumps(v,indent=2)+'\n').encode())
def derive_base_payloads(ov,base_raw,replacements):
    # Accepted retained-header replacement, extended only to the repaired image.
    pos=0;matches=[];parts=[]
    while pos<len(base_raw):
        if base_raw[pos]==0:
            end=pos+1
            while end<len(base_raw) and base_raw[end]==0:end+=1
            parts.append(base_raw[pos:end]);pos=end;continue
        header=base_raw[pos:pos+110];values=ov._fields(header)
        name=base_raw[pos+110:pos+110+values[11]-1].decode()
        if name.startswith('./'):name=name[2:]
        start=(pos+110+values[11]+3)&~3;end=(start+values[6]+3)&~3
        if name in replacements:
            data,expected_old_sha=replacements[name]
            if sha(base_raw[start:start+values[6]])!=expected_old_sha:raise ValueError('selected original BASE payload '+name)
            h=bytearray(header);h[54:62]=('%08x'%len(data)).encode()
            if header[:6]==b'070702':h[102:110]=('%08x'%(sum(data)&0xffffffff)).encode()
            parts.append(bytes(h)+base_raw[pos+110:start]+data+b'\0'*(-len(data)%4))
            matches.append({'name':name,'old_header_hex':header.hex(),'new_header_hex':bytes(h).hex()})
        else:parts.append(base_raw[pos:end])
        pos=end
    if sorted(row['name'] for row in matches)!=sorted(replacements):raise ValueError('exact image+boot replacements once')
    derived=b''.join(parts);before,_=ov.parse_newc(base_raw);after,_=ov.parse_newc(derived)
    if len(before)!=len(after):raise ValueError('all original BASE records')
    for old,new in zip(before,after):
        omit={'data','size','sha256'} if old['name'] in replacements else set()
        if {k:v for k,v in old.items() if k not in omit}!={k:v for k,v in new.items() if k not in omit}:raise ValueError('original BASE order/metadata '+old['name'])
    return derived,matches
def check_kernel_elf(data):
    # IHK smp-driver load_file: ELF table fits first page; PT_LOAD uses high VAs.
    import struct
    if len(data)<64 or data[:7]!=b'\x7fELF\x02\x01\x01':raise ValueError('kernel ELF64 little endian')
    h=struct.unpack_from('<16sHHIQQQIHHHHHH',data)
    if h[1:4]!=(2,62,1) or h[8]!=64 or h[9]!=56:raise ValueError('kernel executable x86_64 header')
    entry,off,count=h[4],h[5],h[10]
    if off<64 or off%8 or not count or off+56*count>min(4096,len(data)):raise ValueError('kernel loader program table')
    loads=[]
    for i in range(count):
        kind,flags,pos,va,pa,filesz,memsz,align=struct.unpack_from('<IIQQQQQQ',data,off+56*i)
        if pos>len(data) or filesz>len(data)-pos:raise ValueError('kernel segment file range')
        if flags&~7 or (align>1 and align&(align-1)):raise ValueError('kernel segment flags/alignment')
        if kind==3:raise ValueError('kernel interpreter')
        if kind!=1:continue
        if not memsz or filesz>memsz or memsz>(1<<64)-va:raise ValueError('kernel LOAD memory range')
        if va%4096!=pos%4096 or (align>1 and va%align!=pos%align):raise ValueError('kernel LOAD congruence')
        loads.append((va,filesz,flags))
    if not loads or not any(flags&1 and va<=entry<va+size for va,size,flags in loads):raise ValueError('kernel executable entry')
    return dict(load_count=len(loads),entry=entry,program_table_end=off+56*count)

def stage(inputs,out):
    # Exact command/profile admission remains external to this file transformer.
    required={'base_manifest','authority','app0','app1','collector','native_boot','overlay_module','diagnostic_module','expected0','expected1','repaired_image'}
    if set(inputs)!=required:raise ValueError('stage exact inputs')
    if any(value is None for value in inputs.values()):raise ValueError('PENDING genuine NEW205 repaired image/canonical authority inputs; no stage effects')
    for r in inputs.values():exact(r)
    nd=load('pair_stage_diagnostic',inputs['diagnostic_module']['path'])
    ov=load('pair_stage_overlay',inputs['overlay_module']['path'])
    inherited=json.loads(Path(inputs['base_manifest']['path']).read_text())
    old=nd._one_validate_manifest(inherited)
    if old['artifacts']['mckernel_image']['sha256']!='1e7a1f689f565e3ba35def32d4f8c9ae729f0e5945c4fbeadee4eb523738a4a2':raise ValueError('exact inherited FP BASE')
    authority=load('new205_authority',R/'repaired_image_authority.py')
    authority.validate(json.loads(Path(inputs['authority']['path']).read_text()),inputs['repaired_image'])
    for r in old['artifacts'].values():exact(r)
    for r in old['modules']:exact(r)
    out=Path(out);out.mkdir(mode=0o700)
    original_base=old['artifacts']['initramfs'];original_raw=gzip.decompress(Path(original_base['path']).read_bytes())
    boot_data=Path(inputs['native_boot']['path']).read_bytes();ov._check_collector(boot_data)
    image_data=Path(inputs['repaired_image']['path']).read_bytes();check_kernel_elf(image_data)
    base_raw,header_proof=derive_base_payloads(ov,original_raw,{'bin/native-boot':(boot_data,old['artifacts']['native_boot']['sha256']),'images/mckernel.img':(image_data,old['artifacts']['mckernel_image']['sha256'])})
    base_path=out/'base.cpio.gz';write(base_path,ov._gzip(base_raw));base=ref(base_path)
    if gzip.decompress(base_path.read_bytes())!=base_raw:raise ValueError('derived base reread')
    layer=out/'pair-layer1.cpio.gz'
    om=ov.build_overlay(base['path'],inputs['app0']['path'],inputs['collector']['path'],old['artifacts']['mcexec']['path'],str(layer),
        collector_sha256=inputs['collector']['sha256'],mcexec_sha256=old['artifacts']['mcexec']['sha256'],payload_sha256=inputs['app0']['sha256'],
        base_sha256=base['sha256'],base_size=base['size'],base_cpio_sha256=sha(base_raw),base_cpio_size=len(base_raw))
    mid=gzip.decompress(layer.read_bytes())
    if not mid.startswith(base_raw):raise ValueError('retained original base prefix')
    for k in ('app0','app1'):ov._check_collector(Path(inputs[k]['path']).read_bytes())
    extra=ov._archive((n,Path(inputs[k]['path']).read_bytes(),stat.S_IFREG|0o755) for n,k in
        [('apps/app0','app0'),('apps/app1','app1')])
    raw=mid+extra;records,_=ov.parse_newc(raw);final=ov._manifest(ov._replay_records(records))
    old_rows=ov._manifest(ov._replay_records(ov.parse_newc(base_raw)[0]))
    if {k:v for k,v in final['bin/native-boot'].items() if k not in {'sha256','size'}}!={k:v for k,v in old_rows['bin/native-boot'].items() if k not in {'sha256','size'}}:
        raise ValueError('all inherited boot metadata retained')
    output=out/'lifecycle.cpio.gz';write(output,ov._gzip(raw))
    if gzip.decompress(output.read_bytes())!=raw:raise ValueError('full archive reread')
    om.update(final_map=final,output_identity=ov._identity(output.stat()),output_sha256=sha(output.read_bytes()),
              overlay_sha256=sha(mid[len(base_raw):]+extra),size=output.stat().st_size)
    js(out/'overlay-manifest.json',om)
    m=copy.deepcopy(old)
    m['case_id']='practical.rust.two-cpu-pair.repaired-affinity-205'
    m['artifacts']['payload']=inputs['app0'];m['artifacts']['native_boot']=inputs['native_boot'];m['artifacts']['mckernel_image']=inputs['repaired_image']
    for k in ('initramfs','root_base'):m['artifacts'][k]=base
    m['staging'].update(base_initramfs=base,collector=inputs['collector'],derived_initramfs=ref(output),overlay_manifest=ref(out/'overlay-manifest.json'),overlay_source=ref(Path(__file__)))
    m['payload']={'cwd':'/case/work','argv':['/bin/mcexec','-t','1','0','/apps/app'],
        'env':{'PATH':'/usr/bin:/bin','COKERNEL_PATH':'/apps'},
        'oracle':{'stdout_hex':Path(inputs['expected0']['path']).read_bytes().hex(),'stderr_hex':'','exit_code':0},'stdout_limit_bytes':1024,'stderr_limit_bytes':1024}
    apps=[]
    for i in range(2):
        apps.append({'id':i,'cpu':i,'argv':nd.pair_argv(i),'cwd':'/case/two-app/work'+str(i),'env':nd.pair_env(i),
            'payload':inputs['app'+str(i)],'oracle':{'stdout_hex':Path(inputs['expected'+str(i)]['path']).read_bytes().hex(),'stderr_hex':'','exit_code':0},
            'stdout_limit_bytes':1024,'stderr_limit_bytes':1024,'timeout_ms':10000})
    m['pair']={'version':1,'os':0,'generation':1,'host_cpus':[1,2],'cpus':[0,1],'default_ikc_linux':0,'apps':apps,
        'source_authority':inputs['authority'],'inherited_overlay_manifest':old['staging']['overlay_manifest']}
    nd._validate_manifest(m)
    for r in inputs.values():exact(r)
    for r in old['artifacts'].values():exact(r)
    for r in old['modules']:exact(r)
    js(out/'manifest.json',m)
    used=sum(p.stat().st_size for p in out.iterdir() if p.is_file())
    if used>64*1024**2:raise ValueError('stage output budget')
    result={'status':'PASS_TWO_CPU_OFFLINE_STAGE_PENDING_NATIVE_RELEASE','manifest':ref(out/'manifest.json'),'overlay':ref(output),
            'image_sha256':inputs['repaired_image']['sha256'],'base_derivation_only_image_and_boot_payload':True,'all_original_records_order_metadata_preserved':True,
            'raw_header_proof':header_proof,'original_base':original_base,'derived_base':base,
            'derived_base_prefix_preserved_by_overlay':True,'members':len(final),'stage_bytes':used,'guest_runs':0,'acceptance':False}
    js(out/'stage-result.json',result)
    return result
if __name__=='__main__':
    ap=argparse.ArgumentParser(allow_abbrev=False);ap.add_argument('--inputs',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    result=stage(json.loads(Path(a.inputs).read_text()),a.out)
    print(json.dumps({k:result[k] for k in ('status','members','stage_bytes','guest_runs','acceptance')}))
