"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure source composition; --write writes only inside this private packet.
No compiler, fixture, origin producer, guard, process or runtime entry is called.
"""
from pathlib import Path
import argparse
import ast
import copy
import difflib
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
PINS = json.loads((HERE / 'INPUTS.json').read_bytes())
SCOPE = __doc__.splitlines()[0]
RUST = 'kernel/rust/syscall_policy.rs'
CMAKE = 'kernel/CMakeLists.txt'
ARCH = 'arch/x86_64/kernel/syscall.c'
PROFILE = 'scripts/f06_origin_command_profile.json'
PRODUCER = 'scripts/derive_f06_origin.py'
LEAF = 'kernel/rust/f06_native_signal_restore_fp.rs'


def require(ok, why):
    if not ok:
        raise ValueError(why)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def ref(path):
    path = Path(path)
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=sha(raw))


def read(row):
    require(ref(row['path']) == row, 'exact BYTE input: ' + row['path'])
    return Path(row['path']).read_bytes()


def checked(row):
    return json.loads(read(row))


def hunks(patch):
    blocks = re.split(r'^@@[^\n]*\n', patch, flags=re.M)[1:]
    require(bool(blocks), 'unified patch requires context hunks')
    result = []
    for block in blocks:
        lines = block.splitlines(True)
        require(all(line[:1] in (' ', '+', '-') for line in lines), 'unsupported patch line')
        old = ''.join(line[1:] for line in lines if line[:1] in (' ', '-'))
        new = ''.join(line[1:] for line in lines if line[:1] in (' ', '+'))
        require(old and old != new, 'nonempty changed patch hunk')
        result.append((old, new))
    return result


def apply(source, patch):
    for old, new in hunks(patch):
        require(new not in source, 'patch already applied')
        require(source.count(old) == 1, 'exact unique patch preimage')
        source = source.replace(old, new, 1)
    return source


def patch_for(before, after, path):
    return ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                       fromfile='a/' + path, tofile='b/' + path))


def additions(patch):
    blocks = hunks(patch)
    require(len(blocks) == 1, 'one additive CMake hunk')
    lines = patch.splitlines(True)
    require(not any(x.startswith('-') and not x.startswith('---') for x in lines),
            'CMake reconciliation is insertion only')
    added = ''.join(x[1:] for x in lines if x.startswith('+') and not x.startswith('+++'))
    old, new = blocks[0]
    require(new.count(added) == 1 and new.replace(added, '', 1) == old,
            'one exact contiguous CMake addition')
    return old, new, added


def merge_cmake(base116, source117, patch117, patch118):
    old117, new117, added117 = additions(patch117)
    old118, new118, added118 = additions(patch118)
    require(old117 == old118, 'reviewed CMake additions share the same exact116 boundary')
    require(apply(base116, patch117) == source117, 'banked117 CMake derives exactly from116')
    # Both owners appended after the same shmget selection. Preserve each exact
    # addition, using reviewed118-before117 declaration order at that boundary.
    require(source117.count(new117) == 1, 'unique banked117 CMake hunk')
    joined = new117.replace(added117, added118 + added117, 1)
    result = source117.replace(new117, joined, 1)
    require(result.replace(added118, '', 1) == source117, 'CMake inverse retains exact117')
    require(result.replace(added117, '', 1) == apply(base116, patch118),
            'CMake inverse retains exact reviewed118 insertion')
    return result


def encoder():
    # Extract the existing pure function only, without importing its effectful
    # module. Four accepted command records independently bind its serialization.
    tree = ast.parse(read(PINS['command_encoder']))
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'canonical_bytes']
    require(len(nodes) == 1, 'one actual canonical_bytes encoder')
    namespace = {'json': json}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), PINS['command_encoder']['path'], 'exec'), namespace)
    encode = namespace['canonical_bytes']
    vectors = checked(PINS['encoding_vectors'])['exact_commands']
    require(len(vectors) == 4, 'four accepted command encoding vectors')
    require(all(sha(encode(row['argv'])) == row['argv_sha256'] for row in vectors),
            'actual accepted command encoding vectors')
    return encode


def reviewed(pin):
    review = checked(pin)
    require(review['independent'] is True and review['implementation_ownership'] is False
            and review['runtime_authority'] is None and review['decision'].startswith('PASS_'),
            'independent source/HOST review only')
    checked(review['source_ready'])
    for row in review['integration_patches']:
        read(row)
    return review


def validate_sources(base116, source117, result, review03, review06):
    require(read(review03['entry']).decode() in result[RUST], 'exact reviewed clear_host_pte entry')
    require(read(PINS['clear_body']).decode() in result[RUST], 'existing complete clear_host_pte body reused')
    require(read(review03['data_binding']).decode() in result['kernel/syscall.c'],
            'exact immutable24B header-produced binding')
    require(result[LEAF] == read(review06['source']).decode(), 'exact reviewed signal-FP leaf')
    require(result[RUST].count('pub unsafe extern "C" fn clear_host_pte(') == 1,
            'one Rust public clear_host_pte source provider')
    require(result[LEAF].count('pub unsafe extern "C" fn arch_native_signal_restore_fp_bridge(') == 1,
            'one Rust public signal-FP source provider')
    require(result['kernel/rust/lib.rs'].count('mod f06_native_signal_restore_fp;') == 1,
            'one signal-FP root module')
    require(result[RUST].count('mod f03_perf_mmap_entry_v1 {') == 1
            and result[RUST].count('mod f06_vdso_info;') == 1,
            'exact banked117 module providers retained')
    require(result['kernel/rust/f06_vdso_info.rs'] == source117['kernel/rust/f06_vdso_info.rs'],
            'banked117 VDSO leaf retained exact')
    for token in ['f06_vdso_info_candidate', 'f06_native_signal_restore_fp_candidate']:
        require(result[CMAKE].count('"' + token + '"') == 1, 'one paired supported CMake cfg: ' + token)
    for token in ['MCKERNEL_RUST_F06_VDSO_INFO', 'MCKERNEL_RUST_F06_NATIVE_SIGNAL_RESTORE_FP']:
        require(result[CMAKE].count('"' + token + '"') == 1, 'one paired supported CMake define: ' + token)
    require('#ifndef MCKERNEL_RUST_F06_NATIVE_SIGNAL_RESTORE_FP\nlong arch_native_signal_restore_fp_bridge(' in result[ARCH],
            'paired signal-FP C fallback remains exact')
    require(result['kernel/syscall.c'].count('extern long clear_host_pte(uintptr_t, size_t, int);') == 1,
            'one real C caller declaration')
    native_pattern = r'#\[cfg\(native_linux_irq_work_v6_12\)\]\nunsafe extern "C" fn vdso_get_vdso_info\(\) -> CInt \{.*?\n\}\n'
    native = re.findall(native_pattern, source117[RUST], re.S)
    require(len(native) == 1 and native[0] in result[RUST], 'native private VDSO initializer retained exact')
    require('setresuid-entry' not in result[RUST] and 'f03_setresuid_entry' not in result[RUST],
            'held credential drafts excluded')
    profile = json.loads(result[PROFILE])
    require(profile['composed_arch_source_sha256'] == sha(result[ARCH].encode()), 'fresh exact arch source/profile join')
    profile_sha = sha(result[PROFILE].encode())
    old_sha = sha(source117[PROFILE].encode())
    require(result[PRODUCER].replace(profile_sha, old_sha, 1) == source117[PRODUCER],
            'origin producer changes only pinned profile hash')
    for path in result:
        if path not in (PROFILE, PRODUCER, LEAF) and result[path] != source117.get(path):
            require(apply(result[path], patch_for(result[path], source117[path], path)) == source117[path],
                    'exact inverse to banked117: ' + path)


def validate_recipe(recipe, source, retained):
    commands = recipe['ordered_commands']
    require(len(commands) == 4, 'exact four current-candidate commands')
    encode = encoder()
    for row in commands:
        require(type(row['argv']) is list and all(type(arg) is str and arg for arg in row['argv']), 'literal argv only')
        require(sha(encode(row['argv'])) == row['argv_sha256'], 'fresh actual command argv/hash')
        require(row['purpose'].startswith(SCOPE), 'explicit functional scope for every command')
    require(recipe['retained_inputs'] == retained and len(retained) == 8, 'eight exact retained inputs, no prefix replay')
    require(commands[0]['argv'].count('f06_native_signal_restore_fp_candidate') == 1, 'one new Rust cfg')
    require(commands[2]['argv'].count('-DMCKERNEL_RUST_F06_NATIVE_SIGNAL_RESTORE_FP') == 1, 'one new arch define')
    profile_commands = json.loads(source[PROFILE])['exact_commands']
    require(len(profile_commands) == 1 and commands[2]['argv'] == profile_commands[0]['argv'],
            'exact arch command matches fresh origin profile')
    origin = '/work/output/build/kernel/rust/f06-origin'
    require(recipe['prerequisite_origin']['output'] == origin
            and 'MCKERNEL_F06_CLONE_CPUID_METADATA_RS=' + origin + '/f06_clone_cpuid_metadata.rs' in commands[0]['argv']
            and '-I' + origin in commands[2]['argv'], 'coherent actual origin consumer paths')
    require(recipe['expected_closed_source_files'] == 123 and recipe['expected_rs_files'] == 112,
            'exact123/112 Rust source closure')


def compose():
    adoption = checked(PINS['adopted116'])
    checked(PINS['accepted116'])
    require(adoption['status'].startswith('ROOT_ADOPTED_QUALIFIED_NEXT116'), 'actual116 source adoption')
    base116 = {}
    for row in adoption['source_changes']:
        read(row['retained_candidate'])
        base116[row['relative']] = read(row['after']).decode()
    source_map = checked(PINS['source117'])
    review117 = checked(PINS['review117'])
    require(review117['independent'] is True and review117['runtime_authority'] is None
            and review117['decision'] == 'PASS_EXACT_NEXT117_SOURCE_AND_CORRECTED_RECIPE_CHECKS_ONLY',
            'reviewed exact banked117 source and corrected recipe')
    require(review117['source_map'] == PINS['source117'] and review117['corrected_recipe'] == PINS['recipe117'],
            'banked117 independent review BYTE joins')
    source117 = dict(base116)
    map117 = {row['relative']: row for row in source_map['writes']}
    require(len(map117) == 7, 'exact banked117 seven-path increment')
    for path, row in map117.items():
        post = read(row['postimage']).decode()
        if row['preimage'] is not None:
            require(read(row['preimage']).decode() == base116[path], 'banked117 canonical116 preimage')
            require(apply(base116[path], read(row['patch']).decode()) == post, 'banked117 patch/postimage binding')
        else:
            require(path not in base116 and row['patch'] is None, 'banked117 new leaf path')
        source117[path] = post
    review03 = reviewed(PINS['reviewF03'])
    review06 = reviewed(PINS['reviewF06'])
    actual03 = checked(review03['actual_HOST_result'])
    actual06 = checked(review06['actual_HOST_summary'])
    supplement = checked(PINS['host_retirement'])
    require(len(supplement['actors']) == 7 and all(
        row['returncode'] == 0 and row['positive_join'] and row['group_absent'] and row['streams_closed']
        for row in supplement['actors']), 'actual seven HOST child retirements')
    require({row['evidence']['sha256'] for row in supplement['actors']} ==
            {review03['actual_HOST_result']['sha256'], review06['actual_HOST_summary']['sha256']},
            'actual HOST supplement binds the two exact reviewed results')
    require(review03['checks']['C_Rust_pairs'] == 2304 and review06['checks']['C_Rust_pairs'] == 576,
            'reuse actual2304+576 HOST pairs without fixture replay')
    require(actual03 and actual06, 'actual HOST records exist')
    result = dict(source117)
    patch03 = [read(row).decode() for row in review03['integration_patches']]
    patch06 = [read(row).decode() for row in review06['integration_patches']]
    result['kernel/syscall.c'] = apply(source117['kernel/syscall.c'], patch03[0])
    result[RUST] = apply(source117[RUST], patch03[1])
    result[ARCH] = apply(source117[ARCH], patch06[0])
    result['kernel/rust/lib.rs'] = apply(source117['kernel/rust/lib.rs'], patch06[1])
    result[CMAKE] = merge_cmake(base116[CMAKE], source117[CMAKE], read(map117[CMAKE]['patch']).decode(), patch06[2])
    result[LEAF] = read(review06['source']).decode()
    profile = json.loads(source117[PROFILE])
    profile['composed_arch_source_sha256'] = sha(result[ARCH].encode())
    commands = profile['exact_commands']
    require(len(commands) == 1 and commands[0]['stage'] == 'selected x86 syscall object', 'one real arch origin command')
    commands[0]['argv'].insert(1, '-DMCKERNEL_RUST_F06_NATIVE_SIGNAL_RESTORE_FP')
    result[PROFILE] = json.dumps(profile, indent=2, sort_keys=True) + '\n'
    old_profile_sha = sha(source117[PROFILE].encode())
    require(source117[PRODUCER].count('PROFILE_SHA256 = "' + old_profile_sha + '"') == 1, 'banked117 producer/profile join')
    result[PRODUCER] = source117[PRODUCER].replace(old_profile_sha, sha(result[PROFILE].encode()), 1)
    validate_sources(base116, source117, result, review03, review06)
    old_recipe = checked(PINS['recipe117'])
    ordered = copy.deepcopy(old_recipe['ordered_commands'])
    ordered[0]['argv'][-1:-1] = ['--cfg', 'f06_native_signal_restore_fp_candidate']
    ordered[2]['argv'].insert(1, '-DMCKERNEL_RUST_F06_NATIVE_SIGNAL_RESTORE_FP')
    encode = encoder()
    history = []
    for index, row in enumerate(ordered):
        row['purpose'] = SCOPE + ' ' + row['stage']
        row['argv_sha256'] = sha(encode(row['argv']))
        history.append(dict(index=index, predecessor117_argv_sha256=old_recipe['ordered_commands'][index]['argv_sha256'],
                            current118_argv_sha256=row['argv_sha256'],
                            argv_changed=row['argv'] != old_recipe['ordered_commands'][index]['argv']))
    require([row['index'] for row in history if row['argv_changed']] == [0, 2], 'only Rust/arch command argv changed')
    origin = copy.deepcopy(old_recipe['prerequisite_origin'])
    origin['action'] = 'After genuine exact118 source adoption/review: generate fresh118 origin for this exact source/profile; no115/116/117 receipt reuse'
    recipe = dict(scope=SCOPE, status='PRIVATE_NEXT118_FOUR_COMMAND_RECIPE_NOT_GRANTED', runtime_authority=None,
                  predecessor117_recipe=PINS['recipe117'], predecessor117_review=PINS['review117'],
                  source_review_authorities=[PINS['reviewF03'], PINS['reviewF06']],
                  actual_accepted116=PINS['accepted116'], ordered_commands=ordered,
                  command_hash_history=history, encoding_source=PINS['command_encoder'],
                  accepted_encoding_vectors=PINS['encoding_vectors'], retained_inputs=copy.deepcopy(old_recipe['retained_inputs']),
                  prerequisite_origin=origin, expected_closed_source_files=123, expected_rs_files=112,
                  expected_new_production_objects=3, expected_raw_link_inputs=11,
                  desired_C_function_delta_relative117=2, desired_C_function_delta_relative116=4,
                  desired_C_symbols_relative117=['clear_host_pte', 'arch_native_signal_restore_fp_bridge'],
                  inherited117_desired_C_symbols=['perf_mmap', 'vdso_get_vdso_info'],
                  source_adoption=None, actual_origin=None, actual_export=None, actual_operation=None,
                  actual_admission=None, future_production_objects=None, future_image=None,
                  future_currentconsumer_proof=None, native_release=None,
                  cohort117_cannot_be_executed_unchanged='Its producer/materializer pins seven adoption paths and122/111 closure. A separately reviewed118 successor must bind nine paths and123/112, exact118 profile/recipe, and fresh actual controls/current native boundary.')
    validate_recipe(recipe, result, old_recipe['retained_inputs'])
    changed116 = {path: raw for path, raw in result.items() if raw != base116.get(path)}
    changed117 = {path: raw for path, raw in result.items() if raw != source117.get(path)}
    require(len(changed116) == 9 and len(changed117) == 8, 'exact nine cumulative/eight incremental changed paths')
    checks = dict(source_only=True, actual_builds=0, actual_fixture_replays=0, actual_native=0,
                  canonical_writes=0, file_closures=0, changed_paths_relative116=9, changed_paths_relative117=8,
                  existing_complete_Rust_body_reused=True, F06_reviewed_leaf_byte_exact=True,
                  CMake_two_additions_exactly_reconciled=True, native_VDSO_initializer_byte_exact=True,
                  actual_HOST_pairs_reused=2880, HOST_children_positively_retired=7,
                  origin_producer_algorithm_unchanged=True, fresh_command_digests=True,
                  arch_command_matches_origin_profile=True, retained_objects=8,
                  future_closed_files=123, future_rs_files=112,
                  desired_C_function_delta_relative117_pending_proof=2,
                  desired_C_function_delta_relative116_pending_proof=4)
    return base116, source117, result, recipe, checks


def write_outputs(base116, source117, result, recipe, checks):
    maps = {116: [], 117: []}
    # The cumulative set is sufficient for Root to adopt directly from canonical116;
    # the incremental set also supports a genuine later117 source adoption.
    for path, raw in result.items():
        if raw == base116.get(path):
            continue
        target = HERE / 'candidate' / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(raw)
        for number, baseline in [(116, base116), (117, source117)]:
            if raw == baseline.get(path):
                continue
            patch = None
            preimage = None
            if path in baseline:
                target_patch = HERE / ('patches-from' + str(number)) / (path.replace('/', '__') + '.patch')
                target_patch.parent.mkdir(parents=True, exist_ok=True)
                target_patch.write_text(patch_for(baseline[path], raw, path))
                patch = ref(target_patch)
                if number == 116:
                    preimage = ref(Path(PINS['checkout']) / path)
                else:
                    source_map = checked(PINS['source117'])
                    matches = [row['postimage'] for row in source_map['writes'] if row['relative'] == path]
                    preimage = matches[0] if matches else ref(Path(PINS['checkout']) / path)
            maps[number].append(dict(relative=path, preimage=preimage, postimage=ref(target), patch=patch))
    for number, rows in maps.items():
        output = dict(scope=SCOPE, status='PRIVATE_NEXT118_SOURCE_COMPOSITION_ONLY', runtime_authority=None,
                      baseline=number, writes=rows, inputs=PINS, checks=checks)
        (HERE / ('SOURCE-MAP-FROM' + str(number) + '.json')).write_text(json.dumps(output, indent=2) + '\n')
    (HERE / 'MINIMAL-FOUR-COMMAND-CONTINUATION.NOT-GRANTED.json').write_text(json.dumps(recipe, indent=2) + '\n')
    overlay = checked(PINS['overlay117'])
    require(len(overlay['files']) == 122 and overlay['expected_rs_count'] == 111, 'exact reviewed117 reference closure')
    files = []
    for row in overlay['files']:
        read(row['source'])
        item = copy.deepcopy(row)
        if row['relative'] in ('lib.rs', 'syscall_policy.rs'):
            item['source'] = ref(HERE / 'candidate/kernel/rust' / row['relative'])
            item['action'] = 'exact_reviewed118_composed_source_reference'
        files.append(item)
    files.append(dict(relative='f06_native_signal_restore_fp.rs', source=ref(HERE / 'candidate' / LEAF),
                      action='exact_reviewed_body2_leaf'))
    require(len(files) == 123 and len({row['relative'] for row in files}) == 123
            and sum(row['relative'].endswith('.rs') for row in files) == 112, 'actual123/112 reference closure')
    overlay118 = dict(scope=SCOPE, status='REFERENCE_OVERLAY_ONLY_NOT_EXPORTED', runtime_authority=None,
                      predecessor=PINS['overlay117'], files=files, expected_count=123, expected_rs_count=112,
                      container_destination='/src/kernel/rust', physical_directory_exports_created=0,
                      external_relative_modules='Reuse the exact three accepted116/117 external relative module sources; Root must include and authenticate them in the genuine118 export/consumer closure.')
    (HERE / 'RUST-CLOSED-SOURCE-OVERLAY.NOT-MATERIALIZED.json').write_text(json.dumps(overlay118, indent=2) + '\n')
    proposal = checked(PINS['origin_proposal117'])
    proposal['after'] = 'Root genuine ninepath cumulative118 adoption plus independent source/recipe review; fresh118 source origin only'
    proposal['argv'][-1] = str(HERE / 'ROOT-ACTUAL-ORIGIN-PRODUCER-OUTPUT-1')
    proposal['recipe_prerequisite_output_spelling_note'] = 'Fresh outputs must be staged at literal /work/output/build/kernel/rust/f06-origin paths consumed by all four exact commands.'
    proposal['purpose'] = SCOPE + ' Generate genuine exact-source118 origin metadata after Root admission; no producer executed here.'
    (HERE / 'ROOT-ORIGIN-PRODUCER-PROPOSAL.NOT-GRANTED.json').write_text(json.dumps(proposal, indent=2) + '\n')
    (HERE / 'SOURCE-COMPOSITION-CHECKS.json').write_text(json.dumps(checks, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=SCOPE)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    values = compose()
    if args.write:
        write_outputs(*values)
    print(json.dumps(values[-1], indent=2))
