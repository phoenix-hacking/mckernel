"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One exact 110->142GiB physical prerequisite; pure metadata, no operation authority.
"""
import hashlib
import json
from pathlib import Path

NATIVE2_SHA = 'f18a78021d4f801d54c556a60d8ae751c31c3681c4dafceb00e813efdebeb268'
OWNER_KEY = 'scripts/native_running_external_modules_owner.py'
D = Path(__file__).resolve().parent

def need(ok, message):
    if not ok:
        raise ValueError(message)

def identity(size):
    return dict(path='/home/holden/mckernel-work/scratch.ext4', device=66306,
                inode=47468427, uid=0, gid=0, mode=0o600, nlink=1, size=size,
                uuid='2a5768c8-718d-4914-bdc0-6b32c5a92a52')

BEFORE = identity(110 * 2**30)
AFTER = identity(142 * 2**30)

def current_sources(bundle, origin, historical_map, load, adapter_ref):
    """A current owner needs its own map, publication and independent source review."""
    mapping = load(bundle['current_source_map'])
    expected = dict(historical_map['source_sha256'])
    owner_path = D / 'daemon_sdk_owner.142G-SOURCE-ONLY.py'
    owner_raw = owner_path.read_bytes()
    owner_ref = dict(path=str(owner_path), bytes=len(owner_raw),
                     sha256=hashlib.sha256(owner_raw).hexdigest())
    expected[OWNER_KEY] = owner_ref['sha256']
    paths = dict(historical_map['effective_runtime_paths'])
    paths[OWNER_KEY] = owner_ref['path']
    need(mapping['source_sha256'] == expected
         and mapping['effective_runtime_paths'] == paths
         and mapping['historical_full11_map'] == origin['full11_map']
         and mapping['historical_source_approval'] == origin['source_approval']
         and mapping['historical_owner'] == origin['owner'], 'current owner/map provenance differs')
    for name, digest in expected.items():
        need(hashlib.sha256(Path(paths[name]).read_bytes()).hexdigest() == digest,
             'current runtime source drift: ' + name)
    publication = load(bundle['current_source_publication'])
    review = load(bundle['current_source_review'])
    validator_raw = Path(__file__).read_bytes()
    validator_ref = dict(path=str(Path(__file__).resolve()), bytes=len(validator_raw),
                         sha256=hashlib.sha256(validator_raw).hexdigest())
    bindings = dict(current_growth_validator=validator_ref, current_owner=owner_ref, current_source_map=bundle['current_source_map'],
                    current_adapter=adapter_ref, historical_owner=origin['owner'],
                    historical_source_approval=origin['source_approval'])
    need(publication['status'] == 'PASS_ACTUAL_FETCHED_CURRENT_CONSUMER_SOURCE'
         and publication['bindings'] == bindings
         and publication['execution_authority'] is False, 'current source publication required')
    need(review['decision'] == 'PASS_SOURCE' and review['implementation_ownership'] is False
         and review['reviewer'] and review['execution_authority'] is False
         and review['SDK_execution_released'] is False
         and review['source_sha256'] == expected and review['bindings'] == bindings
         and review['current_source_publication'] == bundle['current_source_publication'],
         'independent current consumer source review required')
    return mapping, review, owner_ref

def growth_chain(bundle, head, latest, request, live, window, load):
    """Latest container remains native2; exactly one accepted growth follows it."""
    need(head['schema'] == 'mckernel.serial-operation-head.v2'
         and head['latest_container_operation'] == bundle['latest_operation']
         and bundle['latest_operation']['sha256'] == NATIVE2_SHA
         and head['latest_serial_operation'] == bundle['growth_closure']
         and head['physical_prerequisites'] == [bundle['growth_closure']]
         and head['no_unlisted_intervening_operation'] is True
         and 'no_intervening_operation' not in head,
         'exact native2/growth serial head required')
    consumed = head['consumed_nonces']
    need(isinstance(consumed, list) and len(consumed) == len(set(consumed))
         and request['nonce'] not in consumed and latest['nonce'] in consumed,
         'complete consumed nonce head required')
    growth = load(bundle['growth_closure'])
    need(growth['schema'] == 'mckernel.scratch-growth-closure.v1'
         and growth['kind'] == 'scratch_ext4_110_to_142g'
         and growth['status'] == 'PASS_SCRATCH_GROWTH_CLOSED'
         and growth['previous_serial_operation'] == bundle['latest_operation']
         and growth['boot_id'] == window['boot_id']
         and growth['nonce'] in consumed and growth['nonce'] not in (latest['nonce'], request['nonce'])
         and growth['before'] == BEFORE and growth['after'] == AFTER
         and growth['closed_wall'] >= latest['closed_wall']
         and not any(k in growth for k in ('container', 'terminal', 'container_dispositions')),
         'one exact same-inode scratch growth required')
    source = load(growth['source'], False)
    grant, review, commands, release, physical = [load(growth[k]) for k in
        ('grant', 'execution_review', 'actual_commands', 'normal_fd_release', 'fresh_physical_acceptance')]
    binding = dict(source=growth['source'], previous_serial_operation=bundle['latest_operation'],
                   nonce=growth['nonce'], before=BEFORE, after=AFTER)
    need(bool(source) and grant['status'] == 'GRANTED_SCRATCH_GROWTH_110_TO_142G'
         and grant['bindings'] == binding and grant['lower_reserves'] is False,
         'exact finite growth source/grant required')
    need(review['decision'] == 'PASS_SCRATCH_GROWTH_EXECUTION'
         and review['implementation_ownership'] is False and review['reviewer']
         and review['grant'] == growth['grant'] and review['bindings'] == binding,
         'independent exact growth execution review required')
    need(commands['status'] == 'PASS_ACTUAL_SCRATCH_GROWTH_COMMANDS'
         and commands['grant'] == growth['grant']
         and commands['argv'] == grant['commands'] and len(commands['argv']) > 0
         and commands['returncodes'] == [0] * len(commands['argv']),
         'actual exact growth command results required')
    need(release['status'] == 'PASS_NORMAL_FD_RELEASE'
         and release['grant'] == growth['grant']
         and all(release[k] is True for k in ('fd_closed', 'holder_retired', 'group_absent', 'closed_streams'))
         and release['closed_wall'] <= growth['closed_wall'], 'growth normal FD release required')
    physical_bindings = dict(binding, grant=growth['grant'], execution_review=growth['execution_review'],
                             actual_commands=growth['actual_commands'], normal_fd_release=growth['normal_fd_release'])
    need(physical['decision'] == 'PASS_SCRATCH_GROWTH_CURRENT_PHYSICAL'
         and physical['implementation_ownership'] is False and physical['reviewer']
         and physical['bindings'] == physical_bindings
         and physical['actual_backing_identity'] == AFTER
         and physical['observed_wall'] >= growth['closed_wall'], 'fresh accepted growth physical proof required')
    # The ordinary owner receives its existing backing-identity shape (UUID is a mount check).
    need(request['backing_identity'] == {k:v for k,v in AFTER.items() if k != 'uuid'}
         and live['actual_backing_identity'] == AFTER
         and live['growth_closure'] == bundle['growth_closure']
         and live['latest_serial_operation'] == bundle['growth_closure']
         and live['clock']['wall'] >= physical['observed_wall'], 'post-growth actual identity/clock required')
    return growth
