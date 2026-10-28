"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure exact source composition. Only --write creates files inside this private root.
"""
from pathlib import Path
import argparse
import copy
import difflib
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
INPUTS = json.loads((HERE/'INPUTS.json').read_bytes())


def require(ok, why):
    if not ok:
        raise ValueError(why)


def ref(path):
    path = Path(path); raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def read(row):
    require(ref(row['path']) == row, 'input BYTE binding: '+row['path'])
    return Path(row['path']).read_bytes()


def checked(row):
    return json.loads(read(row))


def apply(source, patch):
    """Match every complete context hunk once; reject missing/ambiguous preimages."""
    hunks = re.split(r'^@@[^\n]*\n', patch, flags=re.M)[1:]
    require(bool(hunks), 'unified patch hunks required')
    for hunk in hunks:
        lines = hunk.splitlines(True)
        require(all(line[:1] in (' ', '+', '-') for line in lines), 'unsupported patch line')
        old = ''.join(line[1:] for line in lines if line[:1] in (' ', '-'))
        new = ''.join(line[1:] for line in lines if line[:1] in (' ', '+'))
        require(source.count(old) == 1, 'exact unique patch preimage')
        source = source.replace(old, new, 1)
    return source


def compose():
    adoption = checked(INPUTS['adopted116'])
    require(adoption['status'].startswith('ROOT_ADOPTED_QUALIFIED_NEXT116'), 'actual116 source adoption')
    for row in adoption['source_changes']:
        read(row['retained_candidate'])
        require(ref(row['after']['path']) == row['after'], 'canonical adopted116 preimage changed')
    reviews = [checked(INPUTS['reviewF03']), checked(INPUTS['reviewF06'])]
    for review in reviews:
        require(review['independent'] is True and review['implementation_ownership'] is False and
                review['runtime_authority'] is None and review['decision'].startswith('PASS_'), 'independent source-only review')
        checked(review['source_ready'])
        for row in review['integration_patches']: read(row)
    base = {row['relative']:read(row['after']).decode() for row in adoption['source_changes']}
    f03 = [read(row).decode() for row in reviews[0]['integration_patches']]
    f06 = [read(row).decode() for row in reviews[1]['integration_patches']]
    source = dict(base)
    rust = 'kernel/rust/syscall_policy.rs'
    forward = apply(apply(base[rust],f03[1]),f06[1])
    reverse = apply(apply(base[rust],f06[1]),f03[1])
    require(forward == reverse, 'shared Rust hunks must commute exactly')
    source[rust] = forward
    source['kernel/syscall.c'] = apply(base['kernel/syscall.c'],f03[0])
    source['arch/x86_64/kernel/syscall.c'] = apply(base['arch/x86_64/kernel/syscall.c'],f06[0])
    source['kernel/CMakeLists.txt'] = apply(base['kernel/CMakeLists.txt'],f06[2])
    source['kernel/rust/f06_vdso_info.rs'] = read(reviews[1]['source']).decode()
    profile = json.loads(base['scripts/f06_origin_command_profile.json'])
    profile['composed_arch_source_sha256'] = hashlib.sha256(source['arch/x86_64/kernel/syscall.c'].encode()).hexdigest()
    archs = [row for row in profile['exact_commands'] if row['stage']=='selected x86 syscall object']
    require(len(archs)==1, 'one exact arch origin command')
    argv = archs[0]['argv']; require('-DMCKERNEL_RUST_F06_VDSO_INFO' not in argv, 'selector new exactly once')
    argv.insert(1,'-DMCKERNEL_RUST_F06_VDSO_INFO')
    source['scripts/f06_origin_command_profile.json'] = json.dumps(profile,indent=2,sort_keys=True)+'\n'
    profile_sha = hashlib.sha256(source['scripts/f06_origin_command_profile.json'].encode()).hexdigest()
    producer = base['scripts/derive_f06_origin.py']
    old_sha = hashlib.sha256(base['scripts/f06_origin_command_profile.json'].encode()).hexdigest()
    require(producer.count('PROFILE_SHA256 = "'+old_sha+'"')==1, 'original producer/profile join')
    source['scripts/derive_f06_origin.py'] = producer.replace(old_sha,profile_sha,1)
    require(source['scripts/derive_f06_origin.py'].replace(profile_sha,old_sha,1)==producer,
            'origin producer algorithm unchanged')
    # Existing native initializer and inherited Rust mapping body are exact bytes.
    native_pattern = r'#\[cfg\(native_linux_irq_work_v6_12\)\]\nunsafe extern "C" fn vdso_get_vdso_info\(\) -> CInt \{.*?\n\}\n'
    native = re.findall(native_pattern,base[rust],re.S)
    require(len(native)==1 and native[0] in source[rust], 'native private initializer retained exact')
    binding = read(reviews[0]['C_header_data_binding']).decode()
    require(binding in source['kernel/syscall.c'], 'header-produced C data binding exact')
    require(source[rust].count('mod f03_perf_mmap_entry_v1 {')==1 and source[rust].count('mod f06_vdso_info;')==1,
            'exactly one added Rust callback and child module')
    require(base[rust] in apply(source[rust], ''.join(difflib.unified_diff(source[rust].splitlines(True),base[rust].splitlines(True)))),
            'Rust union inverse restores baseline')
    require(source['kernel/syscall.c'].count('#define perf_mmap f03_perf_mmap_v1')==1,
            'single production descriptor token replacement')
    require('MCKERNEL_RUST_F06_VDSO_INFO' in source['kernel/CMakeLists.txt'] and
            'f06_vdso_info_candidate' in source['kernel/CMakeLists.txt'], 'paired supported C/Rust selectors')
    recipe = checked(INPUTS['recipe116'])
    recipe = copy.deepcopy(recipe)
    commands = recipe['ordered_commands']; require(len(commands)==4, 'original four-command continuation')
    commands[0]['argv'][-1:-1] = ['--cfg','f06_vdso_info_candidate']
    commands[2]['argv'].insert(1,'-DMCKERNEL_RUST_F06_VDSO_INFO')
    require(commands[2]['argv']==archs[0]['argv'], 'arch compiler command exactly matches origin profile')
    require(len(recipe['retained_inputs'])==8, 'eight retained objects, no prefix rebuild')
    recipe.update(runtime_authority=None, status='PRIVATE_NEXT117_COMMAND_RECIPE_NOT_GRANTED',
                  predecessor_recipe=INPUTS['recipe116'], source_review_authorities=[INPUTS['reviewF03'],INPUTS['reviewF06']],
                  source_adoption=None, future_production_objects=None, future_image=None, future_currentconsumer_proof=None,
                  native_release=None, desired_C_function_delta_relative116=2,
                  desired_C_symbols=['perf_mmap','vdso_get_vdso_info'], expected_closed_source_files=122, expected_rs_files=111)
    recipe['Root_command_sequence'] = [
        'Root rechecks adopted116 preimages and independent next117 composition review; copies only seven changed postimages',
        'Bind coherent closed122 Rust export and fresh origin producer/profile metadata to actual proposed source',
        'Retain same eight exact object inputs; execute only four exact current-candidate commands under fresh reviewed admission',
        'Verify new public providers, paired C exclusions, header C data owner, do_mmap debt, two Ddebug descriptors, full ABI/metadata and final consumers']
    changed = {path:text for path,text in source.items() if path not in base or text!=base[path]}
    require(len(changed)==7, 'exactly seven private postimages')
    checks = dict(shared_Rust_hunks_commute=True,native_private_initializer_exact=True,source116_preimages_exact=8,
                  new_Rust_child_module_exact=True,C_header_binding_exact=True,paired_supported_selectors=True,
                  producer_algorithm_unchanged=True,arch_origin_compiler_command_exact=True,retained_objects=8,
                  changed_paths=len(changed),source_only=True,desired_C_function_delta_relative116_pending_proof=2)
    return base, changed, recipe, checks


def main():
    parser=argparse.ArgumentParser(description=__doc__.splitlines()[0]);parser.add_argument('--write',action='store_true');args=parser.parse_args()
    base,changed,recipe,checks=compose()
    if args.write:
        rows=[]
        for path,text in changed.items():
            p=HERE/'candidate'/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
            patch=None
            if path in base:
                q=HERE/'patches'/(path.replace('/','__')+'.patch');q.parent.mkdir(parents=True,exist_ok=True)
                q.write_text(''.join(difflib.unified_diff(base[path].splitlines(True),text.splitlines(True),fromfile='a/'+path,tofile='b/'+path)));patch=ref(q)
            rows.append(dict(relative=path,preimage=ref(Path(INPUTS['checkout'])/path) if path in base else None,postimage=ref(p),patch=patch))
        (HERE/'SELECTIVE-SEVEN-SOURCE-MAP.json').write_text(json.dumps(dict(scope=__doc__.splitlines()[0],status='PRIVATE_SOURCE_ONLY',writes=rows,inputs=INPUTS,checks=checks,runtime_authority=None),indent=2)+'\n')
        (HERE/'MINIMAL-FOUR-COMMAND-CONTINUATION.NOT-GRANTED.json').write_text(json.dumps(recipe,indent=2)+'\n')
        (HERE/'SOURCE-COMPOSITION-CHECKS.json').write_text(json.dumps(checks,indent=2)+'\n')
    print(json.dumps(checks,indent=2))


if __name__=='__main__':main()
