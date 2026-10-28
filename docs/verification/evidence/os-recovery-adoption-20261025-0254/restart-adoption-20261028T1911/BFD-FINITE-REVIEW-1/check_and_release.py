"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Authenticate published BFD closure and fresh read-only initial admission; no capture.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import stat
import subprocess
import sys

ROOT = Path('/home/holden/mckernel')
E = ROOT/'docs/verification/evidence/os-recovery-adoption-20261025-0254'
OWN = E/'restart-adoption-20261028T1911/BFD-FINITE-REVIEW-1'
I = OWN.parent/'BFD-FINAL-INTEGRATION-1'
D = E/'bfd-default-control-routing-restart-20261028-1/entry'
sys.path.insert(0, str(OWN))
from check_static import ref, checked, load, authenticated

def main():
    assert os.getuid() == os.geteuid() == 1000
    publication_path = I/'SOURCE-PUBLICATION.FETCHED.json'
    seal_path = D/'SEALED-ENTRY-BINDINGS.json'
    auth_path = I/'ROOT-INDEPENDENT-FINITE-REVIEW-AUTHORIZATION.json'
    assert ref(publication_path)['sha256'] == '46447096a37bc57b853716fd5bc5fe73738392474db7905f8956e74a0e015468'
    assert ref(seal_path) == dict(path=str(seal_path),bytes=15440,sha256='509adcba115395eb53c6696112b1f38375bd877b6a4e964d9f48888376b44c40')
    assert ref(auth_path)['sha256'] == '3341fde8236c53bd11954a01b2395617386b8884a923bd3f27ab3c83b434a3bf'
    auth = load(auth_path); b = load(seal_path); pub = load(publication_path)
    assert auth['author'] == '/root' and auth['reviewer'] == '/root/observerreview'
    assert auth['decision'] == 'ROOT_AUTHORIZES_ONE_INDEPENDENT_BFD_FINITE_REVIEW_AFTER_EXACT_EXECUTION_RELEASE'
    assert auth['nonce'] == b['nonce'] == 'faac1b4804174de5800c58d61ba98004'
    assert auth['bindings'] == ref(seal_path) and auth['publication'] == ref(publication_path)
    H = Path(auth['handoff']); assert H == I/'HANDOFF-1' and H.is_dir() and not H.is_symlink()
    assert list(H.iterdir()) == [], 'actual handoff must be fresh and empty'
    original = load(D/'ENTRY-BINDINGS.json'); original['source_publication'] = ref(publication_path)
    assert b == original
    assert pub['status'] == 'PASS_FETCHED_EXACT_BFD_SOURCE_CONFIG_CLOSURE' and pub['runtime_authority'] is None
    assert pub['commit'] == '0d4c1d986b23199f9532fcddb5602286651e4b59' and len(pub['rows']) == 40
    fetched_tip = subprocess.run(['git','rev-parse',pub['remote']],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    assert fetched_tip == pub['commit']
    published = {}
    for row in pub['rows']:
        actual = row['actual']; authenticated(actual)
        assert Path(actual['path']).relative_to(ROOT).as_posix() == row['git_path']
        assert row['fetched_commit'] == pub['commit'] and row['git_blob_sha256'] == actual['sha256']
        blob = subprocess.run(['git','cat-file','blob',pub['commit']+':'+row['git_path']],cwd=ROOT,capture_output=True,check=True).stdout
        assert len(blob) == actual['bytes'] and hashlib.sha256(blob).hexdigest() == actual['sha256']
        assert actual['path'] not in published
        published[actual['path']] = actual
    for r in list(b['static_refs'].values())+[b['contract'],b['observer_source'],b['guard_facade'],b['guard_configuration'],b['finite_verifier'],b['capture_source'],b['publisher_source']]:
        assert published[r['path']] == r
    prior = load(OWN/'STATIC-CHECK.json')
    assert prior['decision'] == 'PASS_STATIC_EXECUTION_DESIGN_ONLY' and prior['static_refs'] == b['static_refs']
    for path in prior['runtime_namespaces_absent']:
        assert not os.path.lexists(path)
    profile = checked(b['static_refs']['profile'])
    assert not os.path.lexists(profile['actual_output_root'])
    assert b['nonce'] not in checked(checked(b['contract'])['Root61_observer_fragment']['current_ledger'])['consumed_nonces']
    spec = importlib.util.spec_from_file_location('reviewer_exact_bfd_guard',authenticated(b['guard_facade']))
    guard = importlib.util.module_from_spec(spec); spec.loader.exec_module(guard)
    guard.configure(b['guard_configuration'])
    first = guard.guard()
    limits = guard.current_cutoffs()
    assert limits == b['authorized_cutoffs']
    memory = int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
    capacity = {k:os.statvfs(p).f_bavail*os.statvfs(p).f_frsize for k,p in [('host',ROOT),('scratch','/home/holden/mckernel-work/scratch')]}
    assert memory >= 22<<30 and capacity['host'] >= 16<<30 and capacity['scratch'] >= 14091616256
    mutex = Path('/run/lock/mckernel-development.lock'); st = mutex.lstat()
    assert stat.S_ISREG(st.st_mode) and (st.st_dev,st.st_ino) == (27,4)
    locks = [r for r in Path('/proc/locks').read_text().splitlines() if '00:1b:4' in r]
    assert locks == []
    expected_cgroups = {'/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_period_us':'100000','/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_quota_us':'400000','/sys/fs/cgroup/memory/mckernel-dev/memory.limit_in_bytes':'12884901888','/sys/fs/cgroup/pids/mckernel-dev/pids.max':'512','/sys/fs/cgroup/pids/mckernel-dev/pids.current':'0'}
    actual_cgroups = {p:Path(p).read_text().strip() for p in expected_cgroups}
    assert actual_cgroups == expected_cgroups
    final = guard.guard()
    assert all(a <= z < c for a,z,c in zip(first,final,limits))
    exact = load(E/'bfd-default-control-routing-restart-20261028-1/ROOT-EXACT-COMMANDS.NOT-AUTHORITY.json')
    # Root chooses the fresh handoff argument; all actual program bodies are unchanged.
    commands = exact['commands'][2:]
    for command in commands:
        command['argv'] = [str(H) if value.endswith('/entry/HANDOFF-1') else value for value in command['argv']]
    result = dict(scope=__doc__.splitlines()[0],decision='PASS_EXACT_BFD_FINITE_CAPTURE_HOLDER_AND_CONDITIONAL_BUILD_RELEASE',
        reviewer='/root/observerreview',independent=True,implementation_ownership=False,
        nonce=b['nonce'],maximum_invocations=1,root_authorization=ref(auth_path),
        source_publication=ref(publication_path),published_commit=pub['commit'],independently_verified_blob_rows=40,
        sealed_bindings=ref(seal_path),static_review=ref(OWN/'STATIC-CHECK.json'),execution_design=ref(OWN/'REVIEW.md'),
        handoff=str(H),commands=commands,clamps=limits,first_guard_clocks=first,final_guard_clocks=final,
        fresh_initial_observations=dict(MemAvailable=memory,capacity=capacity,cgroups=actual_cgroups,permanent_mutex=dict(device=27,inode=4,regular=True,no_kernel_lock_row=True)),
        fresh_physical_clearance=False,guard_calls=2,physical_captures=0,holders=0,producers=0,native_cases=0,
        verifier_profile=dict(uid=1000,affinity=[0],AS_bytes=2<<30,finite_wait_seconds=600,custom_timeout=False,automatic_kill=False),
        capture_profile=dict(uid=1000,affinity=[0],AS_bytes=2<<30,CPU_seconds=60,owner_wait_seconds=90,positive_join_required=True),
        holder_only_precondition='Root physical capture zero/positive join and fresh sole-heavy admission; exact permanent27:4 bootstrap only',
        producer_preconditions=['Both original Root captures positively joined','Same original live holder PID/birth/FD3/27:4','Actual independent Hot PASS for exact pending SHA','Original120s freshness after fsync at PASS and READY','Root once publisher and original holder consume READY','All runtime operation/account/guardian/resource guards pass'],
        producer_profile=dict(CPU='2-5',memory_bytes=12<<30,memory_swap_bytes=12<<30,pids=512,network='none',jobs=1,maximum_wall_seconds=19800),
        no_native_payload_guest_authority=True,no_cleanup_authority=True,no_retry_authority=True,
        runtime_authority='INITIAL_FINITE_READONLY_AND_ROOT_CAPTURE_RELEASE_CONDITIONAL_ONE_BUILD_ONLY',
        original_window_and_credit_unchanged=True)
    with (OWN/'EXECUTION-RELEASE.json').open('x') as stream:
        json.dump(result,stream,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
    print(json.dumps(dict(decision=result['decision'],release=ref(OWN/'EXECUTION-RELEASE.json'),guards=2,blobs=40)))

if __name__ == '__main__':
    main()
