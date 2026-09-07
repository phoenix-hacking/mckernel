"""Update the source review queue, preserving IDs and all pending review gates."""
import collections
import copy
import json
from pathlib import Path
import sys

sys.path.insert(0, '/workspace/scripts')
import native_rust_unsafe_ffi_ledger as checker

repo = '/workspace'
ledger = json.loads(Path(repo, checker.LEDGER_PATH).read_text())
discovery = checker.discover(repo)
old = collections.defaultdict(list)

def key(site):
    return (site['path'], site['kind'], site['expression_sha256'],
            json.dumps(site['macro_context'], sort_keys=True))

for site in ledger['sites']:
    old[key(site)].append(site)
next_id = max(int(site['id'].split('-')[-1]) for site in ledger['sites']
              if site['id'].startswith('RS011-SMP-')) + 1
records = []
for found in discovery['sites']:
    prior = old[key(found)]
    if prior:
        record = copy.deepcopy(prior.pop(0))
        record.update(checker.mechanical_site(found))
        if record['id'] in ('RS011-SMP-0026', 'RS011-SMP-0027'):
            record['caller_obligations'] = [found['safety_comment']['text']]
            record['context_constraints'] = [
                'The resident SMP module descriptor is shared by both CPU and memory reservation adapters.',
                'A control-file module owner protects acquisition and final release; a non-Copy reservation pin remains in the owning mutex context while resources or uncertain state remain.',
                'Each successful try_module_get has exactly one module_put; neither CPU nor memory teardown may bypass its outstanding pin.',
            ]
            record['owner']['component'] = 'native Rust SMP shared CPU/memory reservation module pin'
    else:
        if found['path'] != 'host-kernel/native-rust/smp_memory.rs':
            raise SystemExit('Unexpected changed boundary: ' + found['path'])
        record = checker.mechanical_site(found)
        comment = found.get('safety_comment')
        if not comment or not comment.get('text'):
            raise SystemExit('Memory boundary lacks an adjacent safety argument')
        record.update(
            id='RS011-SMP-%04d' % next_id,
            caller_obligations=[comment['text']],
            context_constraints=[
                'Pinned Linux 6.12 x86_64 NUMA/SPARSEMEM_VMEMMAP layout; compile-time page size, node mask/width, section width and allocator order assertions must hold.',
                'Module initialization lends static memory state exactly once to its pinned mutex; a live miscdevice file pins every ioctl and published mutex access.',
                'The memory mutex precedes sleepable memory-hotplug read exclusion; the non-Send guard ends on its acquiring task and no callback reacquires this mutex.',
                'Each non-movable compound allocation retains its original head page and order until exactly one free; ownership transfers exclusively, never through shared mutable aliases.',
                'Batch preflight precedes publication or return; outstanding or poisoned memory retains the shared reservation module pin. OS assignment and guest access are not implemented by this adapter.',
            ],
            owner=dict(component='native Rust SMP Linux memory reservation adapter',
                       accountable_role='host-module maintainer'),
            compiler_capture=dict(required=True, status='not_captured', evidence_sha256=None),
            independent_review=dict(required=True, status='pending', reviewer=None, evidence_sha256=None))
        next_id += 1
    records.append(record)
if any(old.values()):
    raise SystemExit('An existing unsafe boundary was removed or changed without review')
ledger['sites'] = records
ledger['repository_locks'], ledger['target'] = checker.expected_locks(repo)
ledger['crate_roots'] = discovery['roots']
ledger['source_inputs'] = discovery['inputs']
ledger['source_closure_sha256'] = discovery['source_closure_sha256']
by_kind = collections.Counter(site['kind'] for site in records)
by_crate = {crate: sum(crate in site['crate_roots'] for site in records)
            for crate in checker.EXPECTED_CRATES}
ledger['coverage'] = dict(
    source_input_count=len(discovery['inputs']), site_count=len(records),
    site_ids_sha256=checker.sha256_bytes(checker.canonical_bytes([site['id'] for site in records])),
    by_kind=dict(sorted(by_kind.items())), by_crate=by_crate,
    source_inventory_status='complete_for_locked_source_bytes')
ledger['ledger_sha256'] = checker.ledger_digest(ledger)
checker.validate_ledger(ledger, repo)
Path('/work/native-memory-updated-ffi-ledger.json').write_text(checker.pretty(ledger))
print(json.dumps(ledger['coverage'], sort_keys=True))
