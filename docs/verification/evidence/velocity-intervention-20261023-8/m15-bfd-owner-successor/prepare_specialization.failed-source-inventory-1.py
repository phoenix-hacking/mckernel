#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One source-only specialization generator. No imports of owners, tests or subprocesses.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import stat
import uuid

HERE = Path(__file__).resolve().parent
OLD = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-4/dual-container/reuse/compile-only-candidate')
BFD = HERE.parent / 'm15-bfd'
REPO = Path('/home/holden/mckernel')
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write_json(path, doc):
    path.write_text(json.dumps(doc, indent=2, sort_keys=True)+'\n')

def identity(path):
    st = path.lstat()
    return dict(path=str(path.resolve()), dev=st.st_dev, inode=st.st_ino, uid=st.st_uid,
                gid=st.st_gid, mode=stat.S_IMODE(st.st_mode), file_type=stat.S_IFMT(st.st_mode))

def inventory(root, selected=None):
    rows = {}
    def walk(path):
        relative = path.relative_to(root).as_posix()
        st = path.lstat()
        row = {'mode':stat.S_IMODE(st.st_mode)}
        if path.is_symlink():
            target = path.resolve(strict=True)
            assert root in target.parents and target.is_file(), str(path)
            row.update(type='symlink', target=os.readlink(path), resolved=target.relative_to(root).as_posix(), sha256=sha(target))
        elif path.is_dir():
            row['type']='directory'
            for child in sorted(path.iterdir()):
                if child.name not in ('.git','__pycache__'):
                    walk(child)
        else:
            assert stat.S_ISREG(st.st_mode), str(path)
            row.update(type='file',size=st.st_size,sha256=sha(path))
        if relative!='.': rows[relative]=row
    if selected is None: walk(root)
    else:
        for relative in selected: walk(root/relative)
    return rows

assert not (HERE/'compile_image_owner.py').exists(), 'Preserve each generated candidate; do not overwrite/replay'
old_owner=(OLD/'compile_image_owner.py').read_text()
assert sha(OLD/'compile_image_owner.py')=='8cd5a1948fc973461e15c17cdea604932b723f839f00646ec7df35c31647d555'
helper=(OLD/'compile_host_helper.py').read_text().replace("'Memory': 4 * 2**30, 'MemorySwap': 4 * 2**30", "'Memory': 2 * 2**30, 'MemorySwap': 2 * 2**30").replace('--memory=4g','--memory=2g').replace('--memory-swap=4g','--memory-swap=2g')
# Deliberately change only the resource reservation; retain transport/measurement implementation.
(HERE/'compile_host_helper.py').write_text(helper)
helper_sha=sha(HERE/'compile_host_helper.py')
retained=json.loads((OLD/'compile-request.PREPARED.json').read_text())
ready=json.loads((BFD/'READY-FOR-ROOT.json').read_text())
selected=['executer/user','cmake/modules','ihk/linux/include']
inputs={'scope':SCOPE,'schema':'mckernel.m15-bfd-fixed-inputs.v1','source_roots':selected,
        'candidate':inventory(BFD),'source':inventory(REPO, selected)}
write_json(HERE/'BFD-INPUTS.json',inputs)
namespace=HERE/'operation-1'
namespace.mkdir(mode=0o700)
for child in ('owner-work','owner-evidence'): (namespace/child).mkdir(mode=0o700)
nonce=uuid.uuid4().hex
old_profile=json.loads((OLD/'COMPILE-PROFILE.json').read_text())
profile={k:old_profile[k] for k in ('activation','admission_max_age_ns','image_id','jobs','minimum_MemAvailable','reserved_native_profile','sole_rw_mount_target','toolchain_manifest_sha256')}
profile.update(schema='mckernel.m15-bfd-compile-link-profile.v1', scope=SCOPE,
    operation='M15_BFD_PINNED_SELECTED_USER_TOOLS_COMPILE_ONLY_V1', namespace=str(namespace),
    lease_path=str(namespace/'compile-lease.json'), owner_nonce=nonce,
    container_name='mckernel-m15-bfd-compile-'+nonce, host_helper_sha256=helper_sha,
    limits=dict(old_profile['limits'], Memory=2*2**30, MemorySwap=2*2**30),
    candidate_root=str(BFD), source_root=str(REPO), source_identity=identity(REPO), candidate_identity=identity(BFD),
    input_manifest=str(HERE/'BFD-INPUTS.json'), input_manifest_sha256=sha(HERE/'BFD-INPUTS.json'),
    retained_request=str(OLD/'compile-request.PREPARED.json'), retained_request_sha256=sha(OLD/'compile-request.PREPARED.json'),
    command=ready['exact_next_command'])
write_json(HERE/'COMPILE-PROFILE.json',profile)
profile_sha=sha(HERE/'COMPILE-PROFILE.json')
text=old_owner.replace('1CPU/4GiB','1CPU/2GiB').replace('"Memory": 4 * 2**30, "MemorySwap": 4 * 2**30','"Memory": 2 * 2**30, "MemorySwap": 2 * 2**30').replace('--memory=4g','--memory=2g').replace('--memory-swap=4g','--memory-swap=2g')
text=text.replace("EXPECTED_HOST_OWNER_SHA256 = '8ffc9a09e2f2e9e9c9cc09af559d707bf6c4b989fc4f9d3ad51fe88a8e5b6083'",'EXPECTED_HOST_OWNER_SHA256 = '+repr(helper_sha))
text=text.replace(str(OLD/'compile_host_helper.py'),str(HERE/'compile_host_helper.py'))
text=text.replace('REQUEST_SCHEMA = "mckernel.native-exact-mckernel-image-container-request.v1"','REQUEST_SCHEMA = "mckernel.m15-bfd-compile-request.v1"\nSCOPE = '+repr(SCOPE))
text=re.sub(r'^COMMON_EXCLUSION = .+$','COMMON_EXCLUSION = '+repr(profile['lease_path']),text,flags=re.M)
text=re.sub(r'^COMPILE_PROFILE = .+$','COMPILE_PROFILE = '+repr(profile),text,flags=re.M)
text=re.sub(r'^COMPILE_PROFILE_PATH = .+$','COMPILE_PROFILE_PATH = Path('+repr(str(HERE/'COMPILE-PROFILE.json'))+')',text,flags=re.M)
text=re.sub(r'^COMPILE_PROFILE_SHA256 = .+$','COMPILE_PROFILE_SHA256 = '+repr(profile_sha),text,flags=re.M)
text=re.sub(r'^PRIVATE_ROOT = .+$','PRIVATE_ROOT = Path('+repr(str(HERE))+')',text,flags=re.M)
# Replace the fixed workload functions, preserving other reusable validation helpers.
fragment=(HERE/'bfd_workload.py.fragment').read_text()
def functions(source):
    starts=list(re.finditer(r'^def (\w+)\(',source,re.M))
    return {match.group(1):source[match.start():starts[i+1].start() if i+1<len(starts) else len(source)] for i,match in enumerate(starts)}
fragments=functions(fragment)
for name in ('_validate_request','_revalidate_inputs','_validate_driver_result','_compile_mounts','_compile_command'):
    # End at next top-level declaration, to preserve class/constant blocks too.
    match=re.search(r'^def '+name+r'\(',text,re.M)
    end=re.search(r'^(?:def |class |[A-Z_]+ = )',text[match.end():],re.M)
    finish=match.end()+end.start() if end else len(text)
    text=text[:match.start()]+fragments[name].rstrip()+'\n\n\n'+text[finish:]
insert=fragments['_bfd_inventory']+fragments['_retained_toolchain_request']
text=text.replace('def _validate_request(request):',insert+'def _validate_request(request):',1)
start=text.index('    _fail(request.get("native_fork_owned_transaction") is True,',text.index('def _validate_compile_domain'))
end=text.index('    root = Path(COMPILE_PROFILE["namespace"])',start)
text=text[:start]+'''    for key in ("source_root", "candidate_root", "input_manifest_sha256", "toolchain_manifest_sha256", "image_id"):
        _fail(request.get(key) == COMPILE_PROFILE[key], "fixed BFD input differs: " + key)
    _fail(request.get("exact_command") == COMPILE_PROFILE["command"], "fixed BFD command differs")
'''+text[end:]
text=text.replace('"owner-work/output"','"owner-work/qualification-1"').replace('"owner-work/evidence"','"owner-work/qualification-1"')
text=text.replace('"RELEASED_FOR_ONE_COMPILE_ONLY_CANDIDATE14"','"RELEASED_FOR_ONE_COMPILE_ONLY_M15_BFD"')
text=text.replace('mckernel.m14-candidate14-dual-container-admission.v1','mckernel.m15-bfd-dual-container-admission.v1')
text=text.replace('PASS_DUAL_CONTAINER_COMPILE_CPU6_4G','PASS_DUAL_CONTAINER_COMPILE_CPU6_2G')
text=text.replace('mckernel.m14-candidate14-compile-lease.v1','mckernel.m15-bfd-compile-lease.v1')
text=text.replace('mckernel.m14-candidate14-compile-owner-receipt.v1','mckernel.m15-bfd-compile-owner-receipt.v1')
text=text.replace('config.get("Entrypoint") == ["/usr/bin/python3"]','config.get("Entrypoint") == ["/usr/bin/env"]')
text=text.replace('["--entrypoint", "/usr/bin/python3", request["image_id"], *command]','["--entrypoint", "/usr/bin/env", request["image_id"], *command]')
text=text.replace('"candidate_sha": r["candidate_sha"], "ihk_sha": r["ihk_sha"],','"input_manifest_sha256": r["input_manifest_sha256"],')
text=text.replace('"source_derivative_sha256": r["source_derivative_sha256"], "materialization_sha256": r["materialization_sha256"],','"candidate_root": r["candidate_root"], "source_root": r["source_root"],')
text=text.replace('"offline candidate14 image driver failed"','"BFD qualifier failed; failure evidence retained"')
text=text.replace('bound["evidence"] / "receipt.json", "driver receipt"','bound["evidence"] / "RESULT.json", "BFD qualifier result"')
text=text.replace('            receipt["status"] = "PASS"','''            receipt["qualification_result_sha256"] = _sha256(bound["output"] / "RESULT.json")
            receipt["qualification_inventory"] = _closure_inventory(bound["output"], bound["output"], Path("/work/qualification-1"))
            receipt["status"] = "PASS"''')
text=text.replace('Fixed candidate14 compile owner.','Fixed M15 BFD compile-only owner.')
(HERE/'compile_image_owner.py').write_text(text)
request={key:profile[key] for key in ('source_root','candidate_root','input_manifest_sha256','toolchain_manifest_sha256','image_id')}
request.update(schema='mckernel.m15-bfd-compile-request.v1', scope=SCOPE,
    compile_operation=profile['operation'], compile_profile_sha256=profile_sha, compile_only_release=None,
    exact_command=profile['command'], jobs=1, timeout=retained['timeout'],
    aggregate_memory_required=2*2**30, memory_backed_bytes=0,
    memory_allocation_roots=[str(REPO),str(BFD)]+[row['host_path'] for row in retained['toolchain_roots']],
    host_owner_path=str(HERE/'compile_host_helper.py'), host_owner_sha256=helper_sha,
    work_root=str(namespace/'owner-work'), output_root=str(namespace/'owner-work/qualification-1'),
    evidence_root=str(namespace/'owner-work/qualification-1'), owner_evidence_root=str(namespace/'owner-evidence'),
    attempt_root=str(namespace/'owner-evidence/attempt'), lease_path=profile['lease_path'], common_exclusion_path=profile['lease_path'],
    disk_admission=retained['disk_admission'])
write_json(HERE/'compile-request.PREPARED.json',request)
write_json(HERE/'SOURCE-DELTA.json',{'scope':SCOPE,'status':'SOURCE_PREPARED_NOT_EXECUTED',
    'base_owner_sha256':sha(OLD/'compile_image_owner.py'),'base_helper_sha256':sha(OLD/'compile_host_helper.py'),
    'base_owner':str(OLD/'compile_image_owner.py'),'base_review':str(OLD.parents[1]/'compile-only-review/INDEPENDENT-REVIEW.md'),
    'owner_sha256':sha(HERE/'compile_image_owner.py'),'helper_sha256':helper_sha,'profile_sha256':profile_sha,
    'request_sha256':sha(HERE/'compile-request.PREPARED.json'),'input_manifest_sha256':sha(HERE/'BFD-INPUTS.json'),
    'source_members':len(inputs['source']),'candidate_members':len(inputs['candidate']),
    'actual_admission':None,'actual_release':None,'actual_output_hashes':None,
    'actual_tests':None,'native_acceptance':False,
    'failure_history':['Inherited original missing-entrypoint defect corrected and 19 tests PASS in original owner.',
                       'Inherited pre-create/CIDless lease retained; finite accepted-CID release cannot reconcile it.',
                       'This BFD specialization has no executed candidate yet; one unexpected candidate plus one bounded correction then expert.']})
