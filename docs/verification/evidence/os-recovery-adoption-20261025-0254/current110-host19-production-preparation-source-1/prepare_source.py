"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Prepare one disjoint CURRENT110 source/command proposal. No execution authority.
Only ordinary source copies, pinned helper adaptations and JSON are written here.
"""
from pathlib import Path
import ast
import copy
import difflib
import hashlib
import json

D = Path(__file__).resolve().parent
E = D.parent
ROOT = E.parents[3]
A = E / 'ROOT-CURRENT109-NEXT-DEFAULT-BUILD-ADMISSION-1'
ADOPTION = E / 'ROOT-HOST19-SELECTIVE-INTEGRATION-NEW12H-1/ROOT-CANONICAL-SOURCE-ADOPTION.json'
GUARD = E / 'operation-account-window-new12h-source-1/actual_account_window.py'
GUARDIAN = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/restart-20261027-1717/ACTUAL-GUARDIAN-VERIFIED.json')
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
CUTOFFS = [1793165769.0, 947874.5689514667, 963213.6960030915]
BUDGET = 23259332608

def read(p): return json.loads(p.read_text())
def ref(p):
    raw = p.read_bytes()
    return dict(path=str(p), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
def save(name, value):
    raw = json.dumps(value, indent=2)+'\n'
    if (D/name).exists():
        assert (D/name).read_text() == raw, 'own existing output must be byte-identical'
        return
    with (D/name).open('x') as stream:
        stream.write(raw)
def write_source(relative, raw):
    path = D/relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert path.read_bytes() == raw and not path.is_symlink(), 'own frozen snapshot must be byte-identical'
        return path
    with path.open('xb') as stream: stream.write(raw)
    path.chmod(0o400)
    return path
def replace_once(text, old, new):
    assert text.count(old) == 1, old[:120]
    return text.replace(old, new, 1)

assert not (D/'PROFILE.SOURCE-ONLY.json').exists(), 'fresh source packet only'
old = read(A/'PROFILE.SOURCE-ONLY.json')
old_map_path = Path(old['inputs']['source_directory_exports'][0]['manifest']['path'])
old_map = read(old_map_path)
adoption = read(ADOPTION)
assert adoption['status'] == 'PASS_ROOT_EXACT_NINE_SOURCE_ADOPTION_ONLY'
for row in adoption['files']:
    assert ref(Path(row['destination']))['sha256'] == row['candidate']['sha256']
guardian = read(GUARDIAN)
assert guardian['journal_state']['finite_watcher_monotonic_deadline'] == CUTOFFS[1]
assert guardian['journal_state']['boot_deadline'] == CUTOFFS[2]

# Preserve the exact accepted source closure; only the three new modules join it.
prior = {row['relative']: row for row in old_map['files']}
added = ['arch_rt_sigreturn_syscall_bridge.rs', 'arch_rt_sigreturn_set_signal_bridge.rs',
         'arch_rt_sigreturn_check_signal_bridge.rs']
expected = set(prior) | set(added)
actual = {str(p.relative_to(ROOT/'kernel/rust')) for p in (ROOT/'kernel/rust').rglob('*') if p.is_file()}
excluded = actual-expected
assert all('/__pycache__/' in p and p.endswith('.pyc') for p in excluded), excluded
assert len(expected) == 112 and expected <= actual
rows = []
for relative in sorted(expected):
    canonical = ROOT/'kernel/rust'/relative
    assert not canonical.is_symlink()
    path = write_source('rust-subtree/'+relative, canonical.read_bytes())
    previous = prior.get(relative, {}).get('snapshot')
    rows.append(dict(relative=relative, original=ref(canonical), snapshot=ref(path),
                     predecessor_snapshot=previous,
                     kind='new HOST19 module' if previous is None else
                     ('unchanged CURRENT109' if previous['sha256'] == ref(path)['sha256'] else 'adopted HOST19 successor')))
assert {r['relative'] for r in rows if r['kind'] == 'adopted HOST19 successor'} == {'process_helpers.rs', 'syscall_policy.rs'}
source_map = dict(scope=SCOPE, runtime_authority=None,
    schema='mckernel.exact-kernel-rust-subtree-readonly.v1',
    base_source_root=old['inputs']['source6153']+'/kernel/rust',
    export_root=str(D/'rust-subtree'), container_destination='/src/kernel/rust',
    files=rows, total_bytes=sum(r['snapshot']['bytes'] for r in rows),
    new_leaf_files=added, no_symlinks=True, no_hardlinks=True,
    original_source_mutations=0, predecessor_manifest=ref(old_map_path),
    excluded_generated_cache_preserved=[ref(ROOT/'kernel/rust'/p) for p in sorted(excluded)])
save('RUST-SUBTREE-CLOSED-SOURCE-MAP.json', source_map)

profile = copy.deepcopy(old)
profile.update(status='CURRENT110_HOST19_SOURCE_PREPARATION_NOT_RELEASED', runtime_authority=None,
    request_sha256=None, deadline_epoch=CUTOFFS[0], native_custody_clearance=None,
    actual_nonce=None, actual_root_adoption=None, actual_execution_review=None,
    actual_resource_authority=None, actual_output_root=None, actual_holder=None,
    fixed_three_clock_cutoffs=CUTOFFS, aggregate_memory_budget_bytes=BUDGET)
for key in list(profile):
    if key.startswith('baseline_') or key == 'unchanged_completed_process_prefix': del profile[key]
postimages = []
for item in old['inputs']['postimages']:
    row = copy.deepcopy(item)
    path = write_source('candidate/'+row['relative'], (ROOT/row['relative']).read_bytes())
    row['postimage'] = ref(path)
    postimages.append(row)
profile['inputs']['postimages'] = postimages
profile['inputs']['source_directory_exports'] = [dict(host_path=str(D/'rust-subtree'),
    container_destination='/src/kernel/rust', readonly=True,
    manifest=ref(D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json'))]
profile['cohort_source_bindings'] = [dict(relative=x['relative'], postimage=x['postimage']) for x in postimages]
profile['cohort_source_bindings'] += [dict(relative='kernel/rust/'+x['relative'], postimage=x['snapshot']) for x in rows]

# Four fresh changed objects; seven exact unchanged inputs, never SDK recompiles.
producer = read(A/'OUTPUT/work/evidence/producer-contract.json')
outputs = {}
for row in producer['commands']:
    container_output = row['output']
    relative = Path(container_output['path']).relative_to('/work/output/build')
    host_output = ref(A/'OUTPUT/work/output/build'/relative)
    assert host_output['bytes'] == container_output['bytes'] and host_output['sha256'] == container_output['sha256']
    outputs[relative.as_posix()] = host_output
for row in profile['inputs']['objects']:
    if row['replace']:
        row['source'] = outputs[row['build_relative']]
        row['retained_archive_member'] = row['source']['path']
        row['action'] = 'CURRENT109 predecessor provenance only; must genuinely rebuild changed CURRENT110 object'
    assert ref(Path(row['source']['path'])) == row['source']
for row in profile['inputs']['configuration']:
    assert ref(Path(row['source']['path'])) == row['source']

commands = copy.deepcopy(old['exact_commands'])
rust_cfg = ['f03_perf_alloc_bridges_selected_candidate', 'f06_rt_sigreturn_syscall_candidate',
            'f06_rt_sigreturn_set_signal_candidate', 'f06_rt_sigreturn_check_signal_candidate']
argv = commands[0]['argv']; insertion = next(i for i, v in enumerate(argv) if v.startswith('--emit=obj='))
argv[insertion:insertion] = [v for cfg in rust_cfg for v in ['--cfg', cfg]]
for index, flags in [(2, ['MCKERNEL_RUST_F03_PERF_ALLOC_BRIDGES']),
                     (3, ['MCKERNEL_RUST_F06_RT_SIGRETURN_SYSCALL', 'MCKERNEL_RUST_F06_RT_SIGRETURN_SET_SIGNAL', 'MCKERNEL_RUST_F06_RT_SIGRETURN_CHECK_SIGNAL'])]:
    argv = commands[index]['argv']; insertion = next(i for i, v in enumerate(argv) if v.startswith('-I'))
    argv[insertion:insertion] = ['-D'+flag for flag in flags]
assert commands[1] == old['exact_commands'][1] and commands[4] == old['exact_commands'][4]
profile['exact_commands'] = commands
profile['producer_contract'].update(source='Accepted CURRENT109 plus exact adopted HOST19 six callbacks/two idle tables; five commands/four fresh objects/seven retained inputs',
    process_delta='process70->68 OBJECT records expected; move immutable idle offsets80B and values36B into genuine Rust; timer120B and13 tracked-line owners preserved',
    expected_F03_C_functions=69, expected_F06_C_functions=25, expected_total_selected_C_functions=94,
    expected_current_cohort_Rust_function_exports=45, expected_process_OBJECT_records=68,
    expected_new_C_function_removals=['perf_event_alloc_kmalloc_bridge', 'perf_event_alloc_free_bridge', 'perf_event_alloc_hw_init_bridge',
        'arch_rt_sigreturn_syscall_bridge', 'arch_rt_sigreturn_set_signal_bridge', 'arch_rt_sigreturn_check_signal_bridge'],
    expected_new_Rust_data=['process_idle_offsets', 'process_idle_values'],
    counts_are_unaccepted_expectations=True)
profile['reuse_descriptor'] = str(D/'FROZEN-FIVE-COMMAND-SEVEN-INPUT-REUSE.json')
save('FROZEN-FIVE-COMMAND-SEVEN-INPUT-REUSE.json', dict(scope=SCOPE, runtime_authority=None,
    predecessor=ref(Path(old['reuse_descriptor'])), accepted_CURRENT109=ref(E/'CURRENT109-INDEPENDENT-DEFAULT-ARTIFACT-ACCEPTANCE.json'),
    configuration=profile['inputs']['configuration'], objects=profile['inputs']['objects'],
    new_objects=[x['build_relative'] for x in profile['inputs']['objects'] if x['replace']],
    actual_commands=commands, source_view=ref(D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json'),
    configuration_reuse_not_fresh_configure=True, previous_commands_replayed=False))
save('PROFILE.SOURCE-ONLY.json', profile)
save('EXACT-FIVE-COMMAND-PROPOSAL.NOT-GRANTED.json', dict(scope=SCOPE, runtime_authority=None,
    deadline_epoch=CUTOFFS[0], fixed_three_clock_cutoffs=CUTOFFS, commands=commands,
    source_profile=ref(D/'PROFILE.SOURCE-ONLY.json'), tool_files=read(A/'OUTPUT/plan.json')['tool_files'],
    producer_contract=profile['producer_contract']))

# Finite adaptations of the existing worker/runner/holder; no new launcher.
tools = []
runner = (A/'run_build_only.py').read_text()
runner = replace_once(runner, 'DEADLINE=1793100290', 'DEADLINE=1793165769')
runner = replace_once(runner, 'BUDGET=23357213271  # current aggregate 21.7531 GiB planning ceiling',
    'BUDGET=23259332608  # current aggregate21.661941528320312GiB ceiling')
guard_ref = ref(GUARD); guardian_ref = ref(GUARDIAN)
guard_code = '''
def current_operation_guard():
    # Read-only fixed-window/account successor; no release or outer control.
    import importlib.util
    policy = Path(%r)
    require(reference(policy)==%r, 'pinned NEW12h account/window guard')
    spec=importlib.util.spec_from_file_location('current110_actual_account_window',policy)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    clocks=module.guard()
    require(reference(Path(%r))==%r, 'fixed actual guardian receipt')
    require(all(now<cutoff for now,cutoff in zip(clocks,%r)), 'stricter actual parent fixed cutoffs')
    return clocks

''' % (str(GUARD), guard_ref, str(GUARDIAN), guardian_ref, CUTOFFS)
runner = replace_once(runner, 'def execute(grant_path):\n', guard_code+'def execute(grant_path):\n    current_operation_guard()\n')
runner = replace_once(runner, "    name='current290-build-only-'+grant['nonce']", "    name='current110-build-only-'+grant['nonce']")
runner = replace_once(runner, "    argv=docker_argv(profile,name,rows,output)", "    current_operation_guard()\n    argv=docker_argv(profile,name,rows,output)")
# Keep positive container terminal evidence before checking an account hold at return.
runner = replace_once(runner, "    require(result.returncode==terminal['ExitCode']==0", "    current_operation_guard()\n    require(result.returncode==terminal['ExitCode']==0")
worker = (A/'build_only_worker.py').read_text()
worker = replace_once(worker, "def alarm_handler(signum,frame):", "CUTOFFS="+repr(CUTOFFS)+"\nBOOT='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'\ndef window_remaining():\n    clocks=[time.time(),time.monotonic(),time.clock_gettime(time.CLOCK_BOOTTIME)]\n    require(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT,'same boot')\n    remaining=min(cutoff-now for now,cutoff in zip(clocks,CUTOFFS))\n    require(remaining>0,'fixed actual three-clock cutoff')\n    return remaining\ndef alarm_handler(signum,frame):")
worker = replace_once(worker, "require(plan['deadline_epoch']==1793100290,'fixed campaign deadline')", "require(plan['deadline_epoch']==1793165769,'fixed actual campaign deadline')")
worker = replace_once(worker, "seconds=min(19800,int(plan['deadline_epoch']-time.time()))", "seconds=min(19800,int(window_remaining()))")
worker = replace_once(worker, "require(time.time()<plan['deadline_epoch'],'before fixed deadline')", "window_remaining()")
holder = (A/'hold_and_run_build_only.py').read_text()
holder = replace_once(holder, "r.require(time.time()<r.DEADLINE,'fixed campaign deadline')", "r.current_operation_guard()")
holder = replace_once(holder, "        while not go.exists():\n", "        while not go.exists():\n            r.current_operation_guard()\n")
for name, text in [('run_build_only.py',runner), ('build_only_worker.py',worker), ('hold_and_run_build_only.py',holder),
                   ('publish_approved_ready.py',(A/'publish_approved_ready.py').read_text())]:
    ast.parse(text, filename=name)
    path = write_source(name, text.encode())
    old_text = (A/name).read_text()
    diff = ''.join(difflib.unified_diff(old_text.splitlines(keepends=True),text.splitlines(keepends=True),fromfile='CURRENT109/'+name,tofile='CURRENT110/'+name))
    target = write_source('tool-diffs/'+name+'.diff',diff.encode())
    tools.append(dict(name=name, predecessor=ref(A/name), successor=ref(path), diff=ref(target)))

export = copy.deepcopy(read(A/'ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json'))
export.update(status='CURRENT110_EXPORT_TEMPLATE_NOT_ACTUAL_AUTHORITY',author=None,decision=None,request_sha256=None)
export['qualified_readonly_files'] = [r['source'] for r in profile['inputs']['configuration']]+[r['source'] for r in profile['inputs']['objects'] if not r['replace']]+[r['postimage'] for r in postimages]+[r['snapshot'] for r in rows]
save('INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json',export)
save('ROOT-NEXT-STEPS.NOT-AUTHORITY.json', dict(scope=SCOPE, runtime_authority=None,
    source_adoption=ref(ADOPTION), accepted_CURRENT109=ref(E/'CURRENT109-INDEPENDENT-DEFAULT-ARTIFACT-ACCEPTANCE.json'),
    source_profile=ref(D/'PROFILE.SOURCE-ONLY.json'), exact_commands=ref(D/'EXACT-FIVE-COMMAND-PROPOSAL.NOT-GRANTED.json'),
    guard=guard_ref, stricter_guardian_receipt=guardian_ref, adapted_tools=tools,
    actual_nonce=None, actual_physical_clearance=None, actual_request=None, actual_export_authority=None,
    actual_holder_bootstrap=None, actual_resource_authority=None, actual_independent_execution_review=None,
    actual_root_grant=None, actual_output_root=None,
    required_next=['Independent review of exact sources/profile/tool diffs and new guard; preserve existing tool decisions and custody protocol.',
      'Root binds fresh current physical clearance/account/source/ownership, new nonce/current ledger; ea92 consumed and all old grants remain invalid.',
      'Root finalizes request/profile/export/publication and source fetch verification using this packet, not CURRENT109 finalizer replay.',
      'Use adapted holder bootstrap only after actual holder-only grant; bind fresh resource data with CPU2-5/12GiB/512tasks, one heavy, aggregate7jobs/23259332608B, HOST16GiB/scratch12GiB floors and actual larger packet floor.',
      'Fresh independent exact execution review and Root grant precede publish_approved_ready; runner executes exactly5commands once.',
      'Capture first failure/passed prefix, actual commands/PIDs/joins/streams/CPU/RSS/container terminal; no automatic rerun.',
      'New source-bound actual object/ELF/default qualifier required: CURRENT109 qualifier inputs remain immutable and are not acceptance for CURRENT110.',
      'Recheck native ownership after positive holder/container joins and integrate only actual accepted artifact predicates.'],
    resource_capture_helper_reuse='Do not call CURRENT109 capture_and_bind_resource.py unchanged: old account guard/deadlines, old admission path and budget fields must be rebound from actual new records; no generic replacement helper is generated here.',
    limits=['No compiler/configure/Docker/guest/root/native/cleanup command executed in this preparation.',
      'Helper AST parsing is syntax-only; independent execution review/local functional regression of changed admission guards remains required.',
      'Actual default/native/full-file claims remain OPEN; planned94 C functions/68process objects/45cohort Rust exports are expectations only.',
      'Current scripted folded-argument/timer OPEN supplemented acceptance remains distinct and must be reread for new actual image.',
      'No outer guardian launch/signal/control or account/budget mutation.']))
save('SOURCE-READY.json',dict(scope=SCOPE,status='SOURCE_READY_MINIMAL_CURRENT110_FIVE_COMMAND_PROPOSAL_NOT_RELEASED',
    runtime_authority=None,profile=ref(D/'PROFILE.SOURCE-ONLY.json'),closed_Rust_source_map=ref(D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json'),
    next_steps=ref(D/'ROOT-NEXT-STEPS.NOT-AUTHORITY.json'),tools=tools,commands=5,new_objects=4,retained_objects=7,
    closed_Rust_sources=112,adopted_files_checked=9,source_only=True,actual_compilers=0,actual_native_apps=0))
print(json.dumps(dict(status='SOURCE_READY_NOT_RELEASED',Rust_files=112,commands=5,new_objects=4,retained_objects=7,canonical_mutations=0)))
