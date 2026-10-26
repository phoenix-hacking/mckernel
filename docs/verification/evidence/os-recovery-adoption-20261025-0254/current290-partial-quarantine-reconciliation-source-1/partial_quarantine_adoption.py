"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Bounded SOURCE stage. Authenticate the retained partial transaction and check
same-description custody. No root transport, retirement, cleanup, quarantine
removal, configure bypass, or runtime execution entrypoint is provided.
"""
import ast
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import types

SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
E = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254')
SNAPSHOT = E / 'current290-post-recovery-retirement-review-1/quarantine-readonly-snapshot-1'
PREPARATION = E / 'current290-dead-caller-normal-cleanup-source-1/ROOT-NORMAL-RETIREMENT-PREPARATION-1'
SOURCE = E / 'current290-dead-caller-normal-cleanup-source-1/bounded-observer-correction-source-1/native_rust_cutover_image_terminal_cleanup.CURRENT290.EXACT-DEAD-CALLER.py'
SOURCE_SHA = 'e49eaf2a7bacc6a64523f9f6c91516b9a3abefc875cdc1d8941c4e6b55473de3'
GRANT_SHA = 'a9f54316ae1c5be8338531a692d7fad76f52402dd61727b46fc70f2ea55cf1c2'
RELEASE_SHA = '9c7589afa411c1b40fe02777facf69007b885d228632b12c3f34e5a091b517e9'
RELEASE_CANONICAL_SHA = '57c62c0c739438ca4a68c2ec167dc953f7274b4968e7c4e6dba74272acc32f70'
PLAN_SHA = 'b5df1a15e071ce09cc4ba44d316baee32b9217917f307dde388efb69196ca88c'
PLAN_CANONICAL_SHA = '279b40f40ae69255914c064e92486fdfbb65ad798077206dc9c598d185e277f8'
JOURNAL_SHA = 'f51d694648934ea837a035daf8adcf99da36d4e47a24cfe1ae397b20861a7577'
QUARANTINE_SHA = '1df4c03a3bc191e82b1b6dd4afb816311e827be25d401bfa3261b284535b1dbc'
COMMON_SHA = '70d279e0a98ef975c49f3bcde549867c8b2df215f800f39c7e41dcccc57edf5d'
SHARED_SHA = 'f65b41d9c9834a1f2b3d1dc9ed1e14307fe6189dd9c3521c8119fdb24847c0d8'
SNAPSHOT_SHA = '1ce1956d78c4b67325430dada8052cc957c8978a6cd28826107dbf88dfd3185c'
BOOT = '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
ROOT_ACTOR = {'pid': 1060806, 'starttime': '80309560', 'fd': 3,
              'parent': 1060803, 'pgid': 1060803, 'boot_id': BOOT}
ROOT_MUTEX = Path('/run/lock/mckernel-development.lock')
REQUIRED_NEXT = (
    'independent high source and exact execution release',
    'fresh authenticated current root actor, old release, plan, journal, archive, namespace and protected-data observations',
    'reviewed real pidfd_getfd transport of root PID1060806/start80309560 FD3',
    'genuine same-OFD custody verified and retained before any old-actor retirement',
    'bounded retirement release, positive pidfd exit and original outer caller/tool65524 joins',
    'phase-aware old-release configure retaining every original predicate at its actual phase',
    'reviewed shared-only continuation using original append/exchange/release predicates',
    'preserve quarantine as original evidence and bind an additive reconciliation record',
)


class Refusal(ValueError):
    pass


def need(condition, reason):
    if not condition:
        raise Refusal(reason)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def strict(raw):
    def pairs(items):
        answer = {}
        for key, value in items:
            need(key not in answer, 'duplicate-json-key')
            answer[key] = value
        return answer
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(Refusal('nonfinite-json')))


def pinned_bytes(path, expected, size=None):
    # Only the retained unprivileged source/evidence inputs are read here.
    raw = path.read_bytes()
    need(digest(raw) == expected and (size is None or len(raw) == size), 'input-pin:' + path.name)
    return raw


def authenticate_retained_snapshot():
    """Exact evidence authentication; explicitly supplies no fresh/live authority."""
    raw_source = pinned_bytes(SOURCE, SOURCE_SHA, 128910)
    raw_release = pinned_bytes(PREPARATION / 'RELEASE.PASS_EXECUTION_RELEASE.json', RELEASE_SHA, 241402)
    release = strict(raw_release)
    need(release['status'] == 'PASS_EXECUTION_RELEASE' and release['script_sha256'] == digest(raw_source)
         and digest(canonical(release)) == RELEASE_CANONICAL_SHA, 'old-release-binding')
    plan_raw = pinned_bytes(SNAPSHOT / 'PLAN.json', PLAN_SHA, 15316)
    plan = strict(plan_raw)
    need(plan_raw == canonical(plan) + b'\n' and digest(canonical(plan)) == PLAN_CANONICAL_SHA
         and plan['release_sha256'] == RELEASE_CANONICAL_SHA, 'old-plan-canonical-binding')
    journal_raw = pinned_bytes(SNAPSHOT / 'JOURNAL.jsonl', JOURNAL_SHA, 1245)
    need(journal_raw.endswith(b'\n'), 'torn-journal')
    rows = [strict(line) for line in journal_raw.splitlines()]
    need(len(rows) == 4, 'exact-four-event-prefix')
    previous = PLAN_CANONICAL_SHA
    for sequence, (event, row) in enumerate(zip(('before_exchange', 'after_exchange', 'release', 'after_release'), rows)):
        body = dict(event=event, index=0, sequence=sequence,
                    plan_identity=[1828, 116868], plan_sha256=PLAN_CANONICAL_SHA, previous=previous)
        wanted = dict(body, hash=digest(canonical(body)))
        need(row == wanted and journal_raw.splitlines()[sequence] == canonical(wanted), 'journal-prefix-binding')
        previous = wanted['hash']
    quarantine = strict(pinned_bytes(SNAPSHOT / 'QUARANTINE.json', QUARANTINE_SHA, 208))
    need(quarantine == dict(error_type='Refusal', release_sha256=RELEASE_CANONICAL_SHA,
                           requires='independent-exact-state-reconciliation',
                           schema='fp-save-image.cleanup-quarantine.v1'), 'original-quarantine-binding')
    common = pinned_bytes(SNAPSHOT / 'COMMON-ARCHIVE.json', COMMON_SHA, 272)
    shared = pinned_bytes(SNAPSHOT / 'SHARED-ACTIVE.json', SHARED_SHA, 269)
    snapshot = strict(pinned_bytes(SNAPSHOT / 'SNAPSHOT.json', SNAPSHOT_SHA))
    need(snapshot['source']['sha256'] == SOURCE_SHA and snapshot['release']['sha256'] == RELEASE_SHA,
         'snapshot-source-release-binding')
    original_records = release['observation']['retained_exclusions']
    need([[r['path'], str(Path(r['path']).parent), p[2], r['sha256'], r['inode'], r['size']]
          for r, p in zip(original_records, plan['records'])] == plan['records']
         and len(original_records) == len(plan['records']) == 2, 'original-record-plan-binding')
    need([digest(common), digest(shared)] == [r['sha256'] for r in original_records], 'archive-original-bytes')
    metadata = {row['path']: row for row in snapshot['metadata']}
    common_active, shared_active = [row[0] for row in plan['records']]
    common_archive = str(Path(plan['records'][0][1]) / plan['records'][0][2])
    shared_archive = str(Path(plan['records'][1][1]) / plan['records'][1][2])
    need(metadata[common_active] == dict(path=common_active, exists=False), 'common-active-must-remain-absent')
    for path, device, inode, length, mode in (
            (common_archive, 66306, 59657390, 272, '0o100600'),
            (shared_active, 1828, 116861, 269, '0o100600'),
            (shared_archive, 1828, 116866, 4096, '0o40700')):
        row = metadata[path]
        need(row['exists'] is True and (row['device'], row['inode'], row['size'], row['mode'], row['uid'], row['gid'])
             == (device, inode, length, mode, 1000, 1000), 'partial-node-binding')
    need(metadata[shared_archive]['children'] == [] and metadata[shared_archive]['nlink'] == 2,
         'remaining-shared-sentinel-binding')
    grant = strict(pinned_bytes(PREPARATION / 'ROOT-ACTUAL-NORMAL-RETIREMENT-GRANT.json', GRANT_SHA))
    need(grant['decision'] == 'GRANT_EXACT_DEAD_CALLER_NORMAL_RETIREMENT_ONCE'
         and '--release-sha256' in grant['argv']
         and grant['argv'][grant['argv'].index('--release-sha256') + 1] == RELEASE_SHA
         and str(SOURCE) in grant['argv'], 'old-actual-grant-binding')
    return dict(scope=SCOPE, status='AUTHENTICATED_RETAINED_PARTIAL_SNAPSHOT_SOURCE_ONLY',
                old_release_sha256=RELEASE_SHA, old_release_canonical_sha256=RELEASE_CANONICAL_SHA,
                plan_sha256=PLAN_SHA, plan_canonical_sha256=PLAN_CANONICAL_SHA,
                journal_sha256=JOURNAL_SHA, journal_events=4, completed_record_indices=[0],
                remaining_record_indices=[1], states=['after_release', 'before_exchange'],
                original_quarantine_sha256=QUARANTINE_SHA, original_root_actor=ROOT_ACTOR,
                runtime_authority=False, fresh_live_state=False, old_actor_retired=False,
                no_replay_of_completed_common=True, missing_prerequisites=list(REQUIRED_NEXT))


def reviewed_phase_algorithms():
    """Extract unchanged e49 predicates, never its main/configure/run entrypoints.

    Callers must supply their complete configured namespace. The fixture supplies
    local temporary paths; production configuration is intentionally unavailable.
    """
    raw = pinned_bytes(SOURCE, SOURCE_SHA, 128910)
    functions = {'digest', 'canonical', 'parse', 'identity', 'exists', 'read_at', 'write_all', 'rename_exchange'}
    methods = {'state', 'append', 'sentinel', 'preserved', 'parent_fd'}
    tree = ast.parse(raw)
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in functions]
    need({node.name for node in nodes} == functions, 'original-functions-missing')
    transaction = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Transaction')
    selected = [node for node in transaction.body if isinstance(node, ast.FunctionDef) and node.name in methods]
    need({node.name for node in selected} == methods, 'original-methods-missing')
    cls = ast.ClassDef(name='Transaction', bases=[], keywords=[], body=selected, decorator_list=[])
    module = types.ModuleType('_reviewed_e49_partial_state')
    module.__dict__.update(os=os, Path=Path, stat=stat, hashlib=hashlib, json=json, Refusal=Refusal)
    import ctypes
    module.ctypes = ctypes
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes + [cls], type_ignores=[])), str(SOURCE), 'exec'), module.__dict__)
    return module


def require_partial_phase(tx, plan, expected_plan_raw, expected_journal_raw):
    """Gate for an already configured, genuinely held transaction; no mutations.

    This does not construct/configure a production transaction or retire actors.
    Original state/preserved/pinned predicates must run unchanged on each call.
    """
    need(expected_plan_raw == canonical(plan) + b'\n', 'adoption-plan-raw-binding')
    rows, actual = tx.state(plan)
    need(b''.join(canonical(row) + b'\n' for row in rows) == expected_journal_raw,
         'adoption-journal-raw-binding')
    need(len(rows) == 4 and actual == ['after_release', 'before_exchange'], 'adoption-exact-phase')
    # A later successor must use this index alone, and bind every operation to
    # the original old-release plan; it must never prepare() or rerun index0.
    return (1,)


def description_lock_rows(pid, fd):
    raw = Path('/proc/{}/fdinfo/{}'.format(pid, fd)).read_text()
    return [line.split()[2:] for line in raw.splitlines() if line.startswith('lock:')]


def verify_description_custody(fd, holder_pid, holder_fd, path, expected_metadata):
    """Read-only same-OFD evidence, retaining the returned FD in the caller.

    FD acquisition MUST be reviewed pidfd_getfd or existing genuine transport.
    This predicate does not acquire/close/release an FD or signal a process.
    Exact target birth/source/boot/pidfd binding is a separate required layer.
    """
    before = os.fstat(fd)
    named = os.stat(path, follow_symlinks=False)
    fields = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    observed = {key: getattr(before, key) for key in fields}
    need(observed == expected_metadata and all(getattr(named, key) == observed[key] for key in fields)
         and stat.S_ISREG(before.st_mode) and before.st_size == 0 and before.st_nlink == 1,
         'custody-fd-and-name-binding')
    need(fcntl.fcntl(fd, fcntl.F_GETFL) & os.O_ACCMODE == os.O_RDONLY and not os.get_inheritable(fd),
         'custody-private-readonly-fd')
    key = '{:02x}:{:02x}:{}'.format(os.major(before.st_dev), os.minor(before.st_dev), before.st_ino)
    wanted = ['FLOCK', 'ADVISORY', 'WRITE', str(holder_pid), key, '0', 'EOF']
    need(description_lock_rows(os.getpid(), fd) == [wanted]
         and description_lock_rows(holder_pid, holder_fd) == [wanted], 'custody-same-description-lock')
    global_rows = [line.split()[1:] for line in Path('/proc/locks').read_text().splitlines() if key in line.split()]
    need(global_rows == [wanted], 'custody-global-exclusive-holder')
    after, named_after = os.fstat(fd), os.stat(path, follow_symlinks=False)
    need(all(getattr(after, name) == observed[name] == getattr(named_after, name) for name in fields),
         'custody-descriptor-or-name-raced')
    return dict(same_description_observed=True, holder_pid=holder_pid, holder_fd=holder_fd,
                retained_fd=fd, lock=wanted, inode=before.st_ino, device=before.st_dev,
                retirement_authority=False, fresh_root_actor_binding=False)


if __name__ == '__main__':
    # Source/evidence authentication only. No runtime options exist.
    print(json.dumps(authenticate_retained_snapshot(), sort_keys=True, indent=2))
