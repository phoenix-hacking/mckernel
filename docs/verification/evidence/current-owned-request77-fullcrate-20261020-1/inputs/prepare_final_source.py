#!/usr/bin/env python3
"""Materialize one exact committed current crate batch; never execute compiler/container."""
import argparse, hashlib, json, os, re, subprocess, uuid
from pathlib import Path
W=Path(__file__).resolve().parent
BASE=W.parent/'current-fullcrate-owner-1'
REPO=Path('/home/holden/mckernel')
def sha(raw): return hashlib.sha256(raw).hexdigest()
def write(path,raw):
    with path.open('xb') as f: f.write(raw)
def save(path,value): write(path,(json.dumps(value,sort_keys=True,indent=2)+'\n').encode())
def ref(path):
    raw=path.read_bytes();return {'path':str(path),'bytes':len(raw),'sha256':sha(raw)}
def replace(value,old,new):
    if isinstance(value,str): return value.replace(old,new)
    if isinstance(value,list): return [replace(v,old,new) for v in value]
    if isinstance(value,dict): return {k:replace(v,old,new) for k,v in value.items()}
    return value

def main():
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',required=True);a=p.parse_args()
    assert re.fullmatch('[0-9a-f]{40}',a.checkpoint),'full root checkpoint required'
    head=subprocess.check_output(['git','rev-parse',a.checkpoint+'^{commit}'],cwd=REPO,text=True).strip()
    assert head==a.checkpoint,'exact existing root checkpoint commit required'
    old=json.loads((BASE/'source-manifest.json').read_bytes())
    cmake=(REPO/'kernel/CMakeLists.txt').read_text()
    block=cmake.split('set(RUST_KERNEL_SRCS',1)[1].split('\n\t)',1)[0]
    paths={r['relative'] for r in old['rows']}
    for suffix in re.findall(r'"\$\{CMAKE_CURRENT_SOURCE_DIR\}/([^"\n]+)"',block):
        paths.add(str((REPO/'kernel'/suffix).resolve().relative_to(REPO)))
    # All old closure inputs and actual current CMake dependency additions must be
    # committed bytes. A root-supplied checkpoint cannot cover uncommitted changes.
    rows=[];blobs=[]
    for relative in sorted(paths):
        path=REPO/relative;assert path.is_file() and not path.is_symlink()
        raw=path.read_bytes()
        committed=subprocess.check_output(['git','show',head+':'+relative],cwd=REPO)
        assert raw==committed,'uncommitted current source: '+relative
        rows.append({'relative':relative,'origin':str(path),'bytes':len(raw),'sha256':sha(raw)})
        blobs.append((relative,raw))
    assert 'kernel/rust/fork_child_credits.rs' in paths
    assert 'fork_child_credits.rs' in dict(blobs)['kernel/rust/fork_control_guest.rs'].decode()
    source=W/'source';assert not source.exists()
    source.mkdir(mode=0o700)
    for relative,raw in blobs:
        out=source/relative;out.parent.mkdir(parents=True,exist_ok=True);write(out,raw)
    identity=sha(json.dumps(rows,sort_keys=True,separators=(',',':')).encode())
    manifest={'schema':old['schema'],'status':'MATERIALIZED_SOURCE_ONLY','source_identity':identity,
              'checkpoint':head,'rows':rows,'count':len(rows),'bytes':sum(r['bytes'] for r in rows),
              'closure_basis':'previous complete closure union actual current RUST_KERNEL_SRCS; current committed bytes only'}
    save(W/'source-manifest.json',manifest)
    commands=json.loads((BASE/'compiler-commands.json').read_bytes())
    for row in commands:
        row['argv']=[('MCKERNEL_RUST_BUILDID=current-guest-source-'+head[:12]) if s.startswith('MCKERNEL_RUST_BUILDID=') else s for s in row['argv']]
    save(W/'compiler-commands.json',commands)
    owner=(BASE/'current_fullcrate_owner_selfretire_ready.py').read_text()
    assert owner.count("usage['usedPercent'] < 97")==1
    owner=owner.replace("usage['usedPercent'] < 97", "usage['usedPercent'] < 100")
    write(W/'current_fullcrate_owner.py',owner.encode())
    # Exact unchanged accepted driver, provider, capture and retirement imports
    # remain shared readonly inputs. This fresh owner differs only in manual
    # invocation's explicit included-plan admission threshold.
    request=json.loads((BASE/'request-selfretire-ready.json').read_bytes())
    nonce=uuid.uuid4().hex
    for key in ('source','commands','owner'):
        request[key]=ref(W/{'source':'source-manifest.json','commands':'compiler-commands.json','owner':'current_fullcrate_owner.py'}[key])
    request['nonce']=nonce;request['container_name']='mckernel-owned-request-fullcrate-'+nonce[:12]
    request['lease_path']='/home/holden/mckernel-work/scratch/'+request['container_name']+'.lease.json'
    request['work_root']=str(W/'work');request['owner_evidence_root']=str(W/'owner-evidence')
    request['mounts']=[dict(row) for row in request['mounts']]
    for row in request['mounts']:
        if row['target']=='/src':row['source']=str(source)
        elif row['target']=='/inputs.json':row['source']=str(W/'source-manifest.json')
        elif row['target']=='/commands.json':row['source']=str(W/'compiler-commands.json')
        elif row['target']=='/work':row['source']=str(W/'work')
    argv=list(request['create_argv']);argv[argv.index('--name')+1]=request['container_name']
    argv[argv.index('--label')+1]='mckernel.owner='+nonce
    for i,item in enumerate(argv):
        if item.startswith('type=bind,src='):
            target=item.split(',dst=',1)[1].split(',',1)[0]
            row=next(r for r in request['mounts'] if r['target']==target)
            argv[i]='type=bind,src='+row['source']+',dst='+target+(',readonly' if row['readonly'] else '')
    request['create_argv']=argv
    for rel in ('output','home','tmp'):(W/'work'/rel).mkdir(mode=0o700,parents=True)
    save(W/'request.json',request)
    profile=json.loads((BASE/'EXECUTABLE-OWNER-PROFILE-SELFRETIRE-READY.json').read_bytes())
    for key in ('owner','source','request'):profile[key]=ref(W/{'owner':'current_fullcrate_owner.py','source':'source-manifest.json','request':'request.json'}[key])
    argv=profile['argv'];argv[argv.index(str(BASE/'current_fullcrate_owner_selfretire_ready.py'))]=str(W/'current_fullcrate_owner.py')
    argv[argv.index('--request')+1]=str(W/'request.json');argv[argv.index('--request-sha256')+1]=profile['request']['sha256']
    argv[argv.index('--release')+1]=str(W/'execution-release.json')
    profile['status']='PREPARED_NOT_RELEASED_NOT_EXECUTED';save(W/'profile.json',profile)
    changed=[r['relative'] for r in rows if next((x['sha256'] for x in old['rows'] if x['relative']==r['relative']),None)!=r['sha256']]
    save(W/'materialization-result.json',{'status':'SOURCE_ONLY_NOT_RELEASED_NOT_EXECUTED','checkpoint':head,'count':len(rows),'source_identity':identity,'changed_source_paths':changed,'review_delta':['exact final current source/commands/request/profile identities','owner admission 97 -> 100 per current manual invocation','fresh owner nonce/name/lease/output roots; all late physical evidence still root-owned'],'acceptance_limits':['direct rustc objects do not execute CMake dependency scheduling','five existing defined global/weak FUNC ELF64 x86-64 ET_REL oracles retained in both selections','object bytes/hash and bound source are compilation proof only; no linked image/default/native caller/ACK acceptance']})
    print(json.dumps({'count':len(rows),'source_identity':identity,'changed_paths':changed[:5],'request_sha256':profile['request']['sha256'],'compiler_started':False}))
if __name__=='__main__': main()
