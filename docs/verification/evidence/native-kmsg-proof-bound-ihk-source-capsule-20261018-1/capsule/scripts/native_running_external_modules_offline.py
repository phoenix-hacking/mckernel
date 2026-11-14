#!/usr/bin/env python3
"""Focused native IHK target; container/lease/retirement belongs to reviewed owner."""
import argparse, hashlib, importlib.util, json, os, re, shlex, stat, struct, subprocess
from pathlib import Path
BASE_DRIVER_SHA = '2622f418c3748dfacaecfe368762ecb2f0a205939c23c121f37629745e6498c5'
SOURCE_BASE = 'd99edf2f58ee44b1a7e9aa726cbb49eee7850248'
PATCH_SHA = 'e419bfbc42c670ea6c10b63f2c757ee6cb20ef3b8181cc9d44c1ee2e248a71ee'
SOURCE_ID = SOURCE_BASE + '+private-kmsg:' + PATCH_SHA
PREPARATION_SHA256 = '1a0fbe157ce6a15de78a38b145efdd6bc3b7b7772f2c05fb4dc4a79e3f93a05f'
IMAGE = 'sha256:0f8ad280e47d76b23554de4aec411752e1f779f9b2fc7fece6b0b3375dc9775d'

def need(ok, message):
    if not ok: raise ValueError(message)

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def plain(path):
    s=path.lstat();need(stat.S_ISREG(s.st_mode) and s.st_nlink==1,'nonregular/hardlinked input: '+str(path));return path

def save(path, value):
    with path.open('x') as f: json.dump(value,f,indent=2);f.write('\n')

def files(root):
    out={}
    for p in sorted(root.rglob('*')):
        s=p.lstat();need(not stat.S_ISLNK(s.st_mode),'symlink refused')
        if stat.S_ISDIR(s.st_mode):continue
        plain(p);out[str(p.relative_to(root))]=p
    return out

def inherited(inputs):
    p=plain(inputs/'accepted-driver.py');need(digest(p)==BASE_DRIVER_SHA,'accepted ELF/helper driver changed')
    spec=importlib.util.spec_from_file_location('accepted_kmsg_build_base',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def load_preparation(p):
    need(digest(plain(p))==PREPARATION_SHA256,'preparation digest mismatch');m=json.loads(p.read_text())
    need(m['schema']=='mckernel.native-kmsg-focused-preparation.v1' and m['source_base_sha']==SOURCE_BASE and m['patch_sha256']==PATCH_SHA,'preparation scope')
    need(len(m['closure'])==14 and sum(x['bytes'] for x in m['closure'])==313606,'closure profile')
    need({x['path'] for x in m['closure'] if x['changed']}=={'os_runtime.rs'},'only one source replacement');return m

def closure(m,candidate,*,generated=False):
    d=candidate/'modules';need(d.is_dir() and d.resolve()==d,'module root canonical')
    actual=files(d);expected={x['path']:x for x in m['closure']};need(len(expected)==14,'duplicate sources')
    for n,r in expected.items():
        need(not Path(n).is_absolute() and '..' not in Path(n).parts,'unsafe source name');p=plain(d/n)
        need(p.stat().st_size==r['bytes'] and digest(p)==r['sha256'],'source changed: '+n)
    if not generated:need(set(actual)==set(expected),'extra source/generated input')
    return {n:r['sha256'] for n,r in expected.items()}

def plan(m):
    a=m['proposed_external_command'];expected=list(m['accepted_external_command']);need(expected[-1]=='modules','accepted target')
    expected[-1]='ihk.ko';expected.insert(expected.index('-j2'),'--jobserver-style=pipe')
    need(a==expected and a.count('M=/candidate/modules')==1 and a.count('O=/out/build')==1,'exact focused make/pipe argv')
    need(m['tool_image']==IMAGE,'tool image');return dict(argv=a,cwd='/out/build',environment=m['environment'],timeout_seconds=1800,execution_release=False)

def validate(m,baseline,candidate,inputs):
    for r in (baseline,candidate,inputs):need(r.is_dir() and r.resolve()==r,'noncanonical root')
    need(baseline!=candidate and baseline not in candidate.parents and candidate not in baseline.parents,'basis overlap')
    sources=closure(m,candidate)
    for r in m['references'].values():
        p=plain(inputs/Path(r['retained_copy']).name);need(p.stat().st_size==r['bytes'] and digest(p)==r['sha256'],'reference drift')
        if r['path'].startswith(m['accepted_basis']+'/'):
            q=plain(baseline/r['path'][len(m['accepted_basis'])+1:]);need(digest(q)==r['sha256'],'basis reference drift')
    for r in m['rust_support_exact_cmd_deps']:
        need(r['path'].startswith(m['accepted_basis']+'/build/rust/'),'support path')
        need(digest(plain(baseline/r['path'][len(m['accepted_basis'])+1:]))==r['sha256'],'Rust support drift')
    b=inherited(inputs)
    for n,h in b.BASIS_DIGESTS.items():need(digest(plain(baseline/'build'/n))==h,'basis tool/header drift')
    for n in ('home','tmp'):need((candidate/n).is_dir() and not any((candidate/n).iterdir()),'fresh home/tmp')
    return sources

def pipe_probe(m,inputs):
    r=m.get('make_pipe_probe');need(isinstance(r,dict),'pinned make pipe recipe observation pending; never retry FIFO')
    p=plain(inputs/r['input_name']);need(digest(p)==r['sha256'],'pipe probe drift');v=json.loads(p.read_text())
    need(v['status']=='PASS_PINNED_MAKE_PIPE_RECIPE' and v['image_id']==IMAGE and v['make_path']=='/usr/bin/make','pinned make probe identity')
    need(v['returncode']==0 and v['direct_child_joined'] is True and v['pipe_jobserver_observed'] is True and v['fifo_count']==0,'pipe recipe proof')
    need(v['argv']==['/usr/bin/make','--jobserver-style=pipe','-j2','-f','/probe/Makefile','all'],'exact bounded recipe probe')

def source_bindings(candidate,inputs,m):
    p=plain(candidate/'modules/.ihk.o.cmd');text=p.read_text();old=(inputs/'accepted-ihk.o.cmd').read_text()
    def cmd(t):
        rows=re.findall(r'^savedcmd_/candidate/modules/ihk\.o := (.+)$',t,re.M);need(len(rows)==1,'saved command');return rows[0]
    actual=cmd(text);need(shlex.split(actual)==shlex.split(cmd(old)),'compiler/strict objtool CLI or flags changed')
    need(re.findall(r'^source_[^\n]+ := ([^\n]+)$',text,re.M)==['/candidate/modules/ihk.rs'],'source assignment')
    need(re.search(r'^deps_/candidate/modules/ihk\.o :=',text,re.M) is not None,'dependency header')
    deps=set(re.findall(r'^  /candidate/modules/([^ \n]+) ',text,re.M));deps.add('ihk.rs')
    need(deps=={x['path'] for x in m['closure']}-{'Kbuild'},'13 actual compiler dependencies')
    need(not re.search(r'^  /out/.*drivers/misc/mckernel/',text,re.M),'foreign production source')
    return dict(command_sha256=digest(p),saved_command=actual,sources=sorted(deps))

def elf_imports(path):
    data=plain(path).read_bytes();need(data[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<HH',data,16)==(1,62),'ELF target')
    off=struct.unpack_from('<Q',data,40)[0];sz,count,names=struct.unpack_from('<HHH',data,58);need(sz==64 and 0<names<count and off+count*sz<=len(data),'ELF sections')
    sec=[struct.unpack_from('<IIQQQQIIQQ',data,off+i*sz) for i in range(count)]
    def content(s):
        a,n=s[4:6];need(a+n<=len(data),'ELF section bounds');return data[a:a+n]
    sections=content(sec[names]);imports=[];namespaces=[]
    for s in sec:
        need(s[0]<len(sections),'section name');name=sections[s[0]:].split(b'\0',1)[0]
        if name==b'.modinfo':
            namespaces.extend(e.split(b'=',1)[1].decode('ascii') for e in content(s).split(b'\0') if e.startswith(b'import_ns='))
        if s[1]!=2:continue
        need(s[9]==24 and s[5]%24==0 and s[6]<len(sec),'symbol geometry');strings=content(sec[s[6]])
        for i in range(0,s[5],24):
            n,info,other,index,value,length=struct.unpack_from('<IBBHQQ',content(s),i)
            if index==0 and n and info>>4 in (1,2):
                need(n<len(strings) and b'\0' in strings[n:],'symbol name');imports.append(strings[n:].split(b'\0',1)[0].decode('ascii'))
    need(len(imports)==len(set(imports)),'duplicate undefined imports');return sorted(imports),set(namespaces)

def export_rows(s):
    result=[]
    for line in s.splitlines():
        v=line.split();need(len(v)==5 and v[2]=='/candidate/modules/ihk','export shape');result.append((v[0],v[1],v[3],v[4]))
    need(len(result)==len(set(result))==21,'exact21 exports');return sorted(result)

def check_imports(imports,namespaces,kernel):
    for n in imports:
        need(n in kernel and kernel[n][2]=="vmlinux","unresolved/nonkernel import: "+n)
        need(len(kernel[n])==4 or kernel[n][4] in namespaces,"unimported kernel namespace: "+n)

def outputs(candidate,inputs,m,baseline):
    d=candidate/'modules';actual=files(d);need({n for n in actual if n.endswith('.ko')}=={'ihk.ko'},'single IHK artifact')
    need(not (d/'modules.order').exists(),'single-target temporary modules.order must be removed')
    need(not any(re.search(r'(?:smp|mcctrl|mckernel\.img)',n) for n in actual),'foreign target output')
    for name in ('ihk.ko.cmd','ihk.mod.cmd','ihk.mod.o.cmd'):
        old=(inputs/('accepted-'+name)).read_text();new=plain(d/('.'+name)).read_text()
        def saved(t):return [x.split(':=',1)[1].strip() for x in t.splitlines() if x.startswith('savedcmd_')]
        need(len(saved(old))==1 and saved(new)==saved(old),'link/mod compiler command changed: '+name)
    expected={x['path'] for x in m['closure']};generated={'ihk.o','.ihk.o.cmd','ihk.mod','.ihk.mod.cmd','ihk.mod.c','ihk.mod.o','.ihk.mod.o.cmd','.module-common.o','..module-common.o.cmd','Module.symvers','.Module.symvers.cmd','ihk.ko','.ihk.ko.cmd','.ihk.o.d'}
    need(set(actual)<=expected|generated,'unexpected generated file')
    for n in ('ihk.o','ihk.mod.c','ihk.mod.o','ihk.ko','.ihk.ko.cmd','Module.symvers'):need(plain(d/n).stat().st_size>0,'missing link input')
    need(export_rows((d/'Module.symvers').read_text())==export_rows((inputs/'accepted-exports.symvers').read_text()),'IHK exports/kinds/namespace/CRC changed')
    b=inherited(inputs);info=b.modinfo(d/'ihk.ko')
    for k,v in m['expected_modinfo'].items():
        if k!='srcversion':need(info.get(k)==v,'module metadata changed: '+k)
    imports,namespaces=elf_imports(d/'ihk.ko');kernel={}
    for line in (baseline/'build/Module.symvers').read_text().splitlines():
        v=line.split();need(len(v) in (4,5),'kernel symbol row');kernel[v[1]]=v
    check_imports(imports,namespaces,kernel)
    return {'ihk':dict(sha256=digest(d/'ihk.ko'),bytes=(d/'ihk.ko').stat().st_size,modinfo=info,compiler_binding=source_bindings(candidate,inputs,m),undefined_imports=imports,import_namespaces=sorted(namespaces),export_count=21)}

def execute(preparation,baseline,candidate,inputs,*,run=False):
    evidence=candidate/'evidence';evidence.mkdir();receipt=dict(status='FAIL',application_acceptance=False,production_acceptance=False,make_returncode=None,preparation_sha256=PREPARATION_SHA256,baseline_source_sha=SOURCE_BASE,source_candidate_sha=SOURCE_ID,source_base_sha=SOURCE_BASE,patch_sha256=PATCH_SHA)
    try:
        need({p.name for p in candidate.iterdir()}=={'modules','home','tmp','evidence'},'fresh candidate layout')
        m=load_preparation(preparation);receipt['source_sha256']=validate(m,baseline,candidate,inputs);request=plan(m)
        receipt['source_provenance']=dict(baseline_source_sha=SOURCE_BASE,source_candidate_sha=SOURCE_ID,source_base_sha=SOURCE_BASE,patch_sha256=PATCH_SHA,closure_sha256=hashlib.sha256(json.dumps(receipt['source_sha256'],sort_keys=True,separators=(',',':')).encode()).hexdigest())
        save(evidence/'request.json',request)
        if not run:receipt['status']='PLAN_VALIDATED_NO_BUILD'
        else:
            pipe_probe(m,inputs)
            with (evidence/'make.stdout').open('xb') as out,(evidence/'make.stderr').open('xb') as err:
                r=subprocess.run(request['argv'],cwd=baseline/'build',env=request['environment'],stdout=out,stderr=err,timeout=1800,check=False)
            receipt['make_returncode']=r.returncode;receipt['make_direct_child_joined']=True;need(r.returncode==0,'IHK make failed')
            closure(m,candidate,generated=True);receipt['artifacts']=outputs(candidate,inputs,m,baseline);receipt['status']='BUILD_ARTIFACT_CHECKS_PASS'
    except Exception as e:receipt['error']=type(e).__name__+': '+str(e)
    finally:
        receipt['retained_files']={}
        for p in sorted((candidate/'modules').rglob('*')):
            s=p.lstat();n=str(p.relative_to(candidate/'modules'))
            if stat.S_ISREG(s.st_mode):receipt['retained_files'][n]=dict(bytes=s.st_size,sha256=digest(p))
            elif not stat.S_ISDIR(s.st_mode):receipt['retained_files'][n]=dict(nonregular=True)
        save(evidence/'receipt.json',receipt)
    return receipt

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true');a=p.parse_args()
    r=execute(Path('/inputs/preparation.json'),Path('/out'),Path('/candidate'),Path('/inputs'),run=a.execute);print(json.dumps(r,indent=2));return int(r['status']=='FAIL')
if __name__=='__main__':raise SystemExit(main())
