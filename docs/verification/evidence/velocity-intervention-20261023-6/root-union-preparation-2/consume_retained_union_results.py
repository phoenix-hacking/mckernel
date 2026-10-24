"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure fixed retained-result consumer: no commands, signals or object hashes.
Root supplies successful00..06 plus corrected07..14 and actual object receipts.
"""
from pathlib import Path
from collections import Counter
import hashlib, json, os, re, stat

D = Path(__file__).resolve().parent
S = D / 'abi-include-path-correction-1'
H = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-syscall/production-consumer-preparation-1/accepted_ELF64_symtab_RELA.ACTUAL-FUNCTION.py')
H_SHA = '874bd6814dc73b51d7a81676657b05b0dcb9f976c183267fd19063ab583c8126'

def need(value, message):
    if not value:
        raise ValueError(message)

def small_json(path):
    raw = Path(path).read_bytes()
    need(len(raw) <= 1 << 20, 'bounded fixed metadata')
    return json.loads(raw)

def file_stat(path):
    path = Path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        a, named, b = os.fstat(fd), path.lstat(), os.fstat(fd)
        fields = ('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns','st_uid','st_gid','st_mode','st_nlink')
        need(stat.S_ISREG(a.st_mode) and all(getattr(a,k) == getattr(named,k) == getattr(b,k) for k in fields), 'stable regular FD/named identity')
        return dict(path=str(path),device=a.st_dev,inode=a.st_ino,size=a.st_size,mtime_ns=a.st_mtime_ns,ctime_ns=a.st_ctime_ns,uid=a.st_uid,gid=a.st_gid,mode=oct(stat.S_IMODE(a.st_mode)),nlink=a.st_nlink)
    finally:
        os.close(fd)

def expected_reused():
    five = small_json(D / 'FIVE-ACCEPTED-C-OBJECTS.REUSE.json')
    new = small_json(D / 'root-actual-combined-production-1/DURABLE-SUCCESSFUL-RUST-AND-F06-C.json')
    return [row['accepted_object'] for row in five['objects']] + new['objects']

def reused_snapshot():
    """Call before suffix consumption and after the final join; hashes are retained references only."""
    result = []
    for expected in expected_reused():
        observed = file_stat(expected['path'])
        need(all(observed[k] == expected[k] for k in observed), 'reused object identity drift')
        result.append(observed)
    return result

def raw_text(row):
    raw = Path(row['path']).read_bytes()
    need(len(raw) == row.get('size', row.get('bytes')) and len(raw) <= 32 << 20 and hashlib.sha256(raw).hexdigest() == row['sha256'], 'retained text capture binding')
    return raw.decode()

def nm(text):
    rows = [line.split() for line in text.splitlines() if line.split()]
    rows = [r for r in rows if len(r) >= 2 and len(r[-2]) == 1 and r[-2].isalpha()]
    return rows, Counter(r[-1] for r in rows if r[-2] == 'T'), {r[-1] for r in rows if r[-2] == 'U'}, {r[-1] for r in rows if r[-2].isupper() and r[-2] not in ('U','N')}

def unique(rows, name, kind):
    found = [r for r in rows if r[-1] == name]
    need(len(found) == 1 and found[0][-2] == kind, 'exact unique symbol ' + name)

def consume(prefix_records, suffix_records, reused_before, reused_after, produced_objects):
    need(len(prefix_records) == 7 and len(suffix_records) == 8, 'successful00..06 and corrected07..14 only; exclude failed07')
    original = small_json(D / 'IMMUTABLE-ROOT-JOBLIST.NOT-EXECUTED.json')
    suffix = small_json(S / 'ROOT-SUFFIX-07-14.NOT-EXECUTED.json')
    commands = original['commands'][:7] + suffix['commands']
    texts = []
    for row, command in zip(prefix_records + suffix_records, commands):
        actual, result = row['command'], row['result']
        need(actual['argv'] == command['argv'] and actual['label'] == command['label'] and actual['cwd'] == command['cwd'], 'exact producer command')
        need(result['returncode'] == 0 and result['direct_child_joined'] is True and result['group_absent'] is True and result['closed_streams'] is True and result['error'] is None and result['retirement_error'] is None and result['timed_out'] is False, 'actual positive whole join')
        texts.append(raw_text(result['captures']['stdout']))
    expected = [{k:r[k] for k in file_stat(r['path'])} for r in expected_reused()]
    need(reused_before == reused_after == expected == reused_snapshot(), 'all seven reused objects stable before/after, no object rehash')
    paths = {'Rust':D/'mckernel_rust.union.o','F06_C':D/'F06-arch-syscall.o','ABI':S/'F06-real-ABI-and-callers.o','partial':S/'six-C-Rust.union.o'}
    need(set(produced_objects) == set(paths), 'root-sealed actual new object receipts required')
    for key,path in paths.items():
        receipt = produced_objects[key]
        need(receipt['path'] == str(path) and re.fullmatch('[0-9a-f]{64}', receipt['sha256']) and all(receipt[k] == v for k,v in file_stat(path).items()), 'actual durable object identity ' + key)
    need(hashlib.sha256((D/'source/F06-real-header-ABI-and-callers.path-correction1.c').read_bytes()).hexdigest() == 'be298ece3033952f6a2298211cac4d4a472afae19498afefac6930ff85fe54e2', 'only corrected witness bytes')
    need(hashlib.sha256((D/'source/arch/x86_64/kernel/syscall.c').read_bytes()).hexdigest() == 'd876e0b24f789372e6747fee7c554a53a3deaa9cee7034d7096374c2dff34ad6', 'exact staged F06 whole C source')
    expected_sets = small_json(D/'EXPECTED-GLOBAL-SYMBOL-SETS.json')
    rust = nm(texts[1]); arch = nm(texts[5]); abi = nm(texts[8]); partial = nm(texts[12])
    need(set(rust[1]) == set(expected_sets['expected_Rust_T']) and all(v == 1 for v in rust[1].values()) and rust[2] == set(expected_sets['expected_Rust_U']), 'exact combined Rust T/U SETs')
    removed = ('vdso_map_global_pages','ptrace_report_signal','arch_ptrace_signal_lock_bridge','arch_ptrace_signal_unlock_bridge','arch_ptrace_save_debugreg_bridge','arch_ptrace_waitq_wake_bridge','arch_ptrace_do_kill_bridge','arch_ptrace_schedule_bridge','arch_ptrace_signal_log_bridge')
    need(not [r for r in arch[0] if r[-1] in removed and r[-2] in ('T','t')], 'selected C entries/adapters absent')
    for name in removed:
        need(re.search(r'\b'+name+r'\s*\([^;{}]*\)\s*\{', texts[10], re.S) is None, 'selected preprocessed C body absent ' + name)
    for name in ('vdso_map_global_pages','vdso_map_global_pages_body_result','ptrace_report_signal','ptrace_report_signal_body_result','arch_ptrace_syscall_event'):
        unique(rust[0], name, 'T')
    for name in ('vdso_map_global_pages','ptrace_report_signal'):
        need(name not in rust[2] and name not in partial[2], 'retired imports absent')
        unique(abi[0], name, 'U'); unique(partial[0], name, 'T')
    unique(arch[0], 'ptrace_report_signal', 'U')
    five = small_json(D/'FIVE-ACCEPTED-C-OBJECTS.REUSE.json')
    inputs = [('Rust', rust), ('F06_C', arch)] + [(row['lane'], nm(raw_text(row['actual_NM']))) for row in five['objects']]
    all_T, all_U, all_defined = Counter(), set(), set()
    for _,table in inputs:
        all_T.update(table[1]); all_U.update(table[2]); all_defined.update(table[3])
    need(all(v == 1 for v in all_T.values()), 'no multiple strong T definitions among actual inputs')
    need(set(partial[1]) == set(all_T) and all(v == 1 for v in partial[1].values()) and partial[2] == all_U-all_defined, 'exact six-C/Rust partial T/U SET resolution')
    helper_raw = H.read_bytes(); need(hashlib.sha256(helper_raw).hexdigest() == H_SHA, 'unmodified accepted ELF64 helper')
    namespace = {'Path':Path, '_fail':need}
    exec(compile(helper_raw, str(H), 'exec'), namespace)
    check = namespace['_m14_Rust_callback_relocations']
    counts = {'root_union_Rust':check(paths['Rust'],('vdso_map_global_pages','do_kill')), 'plain_arch':check(paths['F06_C'],('ptrace_report_signal',)), 'real_header_C_callers':check(paths['ABI'],('vdso_map_global_pages','ptrace_report_signal')), 'partial':check(paths['partial'],('vdso_map_global_pages','ptrace_report_signal'))}
    need(reused_snapshot() == reused_after, 'reused objects remain identical after ELF reads')
    return dict(scope=__doc__,status='PASS_ACTUAL_FULL78_F06_WHOLE_TU_REAL_ABI_ALLOCATED_RELA_AND_SIX_C_PARTIAL_ONLY',successful_commands=15,preserved_original_failed07=True,Rust_T=len(rust[1]),Rust_U=len(rust[2]),partial_T=len(partial[1]),partial_U=len(partial[2]),allocated_RELA=counts,SHF_ALLOC_sh_info_filter=True,exact_target_names=True,substring_matching=False,cross_resolutions={label:sorted(table[2] & all_defined) for label,table in inputs},actual_objects=produced_objects,reused_stat_records=reused_after,object_rehashes=0,commands_launched=0,canonical_changes=0,native_acceptance=False,default_GCC14_final_image=False)
