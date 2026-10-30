"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
UNRUN exact successor oracle. Reads bounded private data only; writes nothing.
"""
from pathlib import Path
import hashlib,json
from exact_projection import require,parse_patch,construct,validate_outputs
D=Path(__file__).resolve().parent
OLD=D.parent
ROOT=Path('/home/holden/mckernel')
E=ROOT/'docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234'
MODULE=b'\n#[cfg(all(f03_request_constructors_candidate, target_arch = "x86_64"))]\n#[path = "f03_request_constructors.rs"]\nmod f03_request_constructors;\n'

def verify_inputs():
    rows=json.loads((D/'INPUTS.json').read_bytes())['inputs']
    require(0<len(rows)<=32,'input row bound')
    paths=[row['path'] for row in rows]
    require(len(set(paths))==len(paths),'duplicate input path')
    required={str(ROOT/'kernel/syscall.c'),str(ROOT/'kernel/rust/syscall_policy.rs'),str(ROOT/'executer/user/rust/mcexec_helpers.rs'),str(OLD/'INPUTS.json'),str(OLD/'UTI-PREACTIVATION-PUBLICATION.PRIVATE-NOT-APPLIED.patch')}
    for name in ['DO-SYSCALL','UTIL-THREAD']:
        packet=E/f'M14-LARGE-{name}-REUSE-1'
        required.update(str(packet/file) for file in ['CURRENT119-PRIVATE-REBASE.patch','RUST-BODY.REUSED.rs.inc','syscall.PRIVATE.c'])
    cp=E/'M14-UPGRADED-F03-REQUEST-CONSTRUCTORS-1'
    required.update([str(cp/'REQUEST-CONSTRUCTORS.ON-TEN.PRIVATE-NOT-APPLIED.patch'),str(cp/'natural-alignment-correction-1/postimage/kernel/rust/f03_request_constructors.rs')])
    contract=E/'M14-F03-REQUEST-CONSTRUCTOR-CONTRACT-1'
    required.update(str(contract/file) for file in ['ROOT-CONTRACT.REFINED-APPROVED.json','ROOT-ALIGNMENT-CORRECTION.APPROVED.json'])
    require(set(paths)==required,'input paths do not exactly bind all real dependencies')
    total=0
    for row in rows:
        path=Path(row['path'])
        require(path.is_absolute() and path.is_file(),'input is not a real absolute file')
        size=path.stat().st_size;total+=size
        require(size<=8*1024*1024 and total<=32*1024*1024,'source input byte bound')
        data=path.read_bytes()
        require(len(data)==size,'input changed during read')
        require(hashlib.sha256(data).hexdigest()==row['sha256'],'input SHA256 mismatch: '+str(path))

def run():
    verify_inputs()
    base_c=(ROOT/'kernel/syscall.c').read_bytes()
    base_rust=(ROOT/'kernel/rust/syscall_policy.rs').read_bytes()
    host=(ROOT/'executer/user/rust/mcexec_helpers.rs').read_bytes()
    c_hunks=[];bodies=[]
    for name in ['DO-SYSCALL','UTIL-THREAD']:
        packet=E/f'M14-LARGE-{name}-REUSE-1'
        sections=parse_patch((packet/'CURRENT119-PRIVATE-REBASE.patch').read_bytes())
        require(set(sections)=={'kernel/syscall.c','kernel/rust/syscall_policy.rs'},'unexpected large-body patch path')
        require(len(sections['kernel/syscall.c'])==2,'unexpected large-body C hunks')
        # This also proves the input candidate itself contains the real deletions.
        require(construct(base_c,sections['kernel/syscall.c'])==(packet/'syscall.PRIVATE.c').read_bytes(),'packet C candidate mismatch')
        c_hunks.extend(sections['kernel/syscall.c'])
        bodies.append((packet/'RUST-BODY.REUSED.rs.inc').read_bytes())
    cp=E/'M14-UPGRADED-F03-REQUEST-CONSTRUCTORS-1'
    sections=parse_patch((cp/'REQUEST-CONSTRUCTORS.ON-TEN.PRIVATE-NOT-APPLIED.patch').read_bytes())
    require('kernel/syscall.c' in sections and len(sections['kernel/syscall.c'])==3,'unexpected constructor C hunks')
    # Only these three existing C hunks participate. No older profile, CMake,
    # held caller, or unrelated patch section is admitted to the staged result.
    c_hunks.extend(sections['kernel/syscall.c'])
    expected_combined=bodies[0]+b'\n'+bodies[1]+MODULE
    combined=(OLD/'COMBINED-RUST-BODIES.rs.inc').read_bytes()
    constructor=(cp/'natural-alignment-correction-1/postimage/kernel/rust/f03_request_constructors.rs').read_bytes()
    hp=parse_patch((OLD/'UTI-PREACTIVATION-PUBLICATION.PRIVATE-NOT-APPLIED.patch').read_bytes())
    host_path='executer/user/rust/mcexec_helpers.rs'
    require(set(hp)=={host_path},'unexpected host patch path')
    host_hunks=hp[host_path]
    require(len(host_hunks)==2,'unexpected host hunk count')
    source_paths={'kernel/syscall.c','kernel/rust/syscall_policy.rs','kernel/rust/f03_request_constructors.rs'}
    actual_paths=[]
    for p in (OLD/'postimage').rglob('*'):
        if p.is_file():
            actual_paths.append(str(p.relative_to(OLD/'postimage')))
            require(len(actual_paths)<=3,'unexpected extra staged source file')
    require(set(actual_paths)==source_paths,'unexpected or missing staged source file')
    staged={name:(OLD/'postimage'/name).read_bytes() for name in source_paths}
    staged['host_function']=(OLD/'mcexec_util_thread_body.PRIVATE.rs.inc').read_bytes()
    staged['host_postimage']=construct(host,host_hunks)
    validate_outputs(base_c,c_hunks,base_rust,combined,expected_combined,constructor,staged,host,host_hunks)
    return {'C_hunks':len(c_hunks),'host_hunks':len(host_hunks),'status':'PASS_EXACT_SOURCE_BYTES_ONLY','tests_or_runtime_acceptance':False}

if __name__=='__main__':
    print(json.dumps(run(),sort_keys=True))
