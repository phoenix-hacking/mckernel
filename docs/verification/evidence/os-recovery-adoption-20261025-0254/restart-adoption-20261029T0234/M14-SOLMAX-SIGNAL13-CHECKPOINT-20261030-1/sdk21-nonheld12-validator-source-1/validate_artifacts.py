#!/usr/bin/env python3
"""Read-only, non-authoritative SDK21 twelve-provider artifact observations.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
No subprocesses. A separate reviewed producer, dependency and origin binding is mandatory.
"""
import ast, collections, hashlib, json, struct, shlex
from pathlib import Path

BASE = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1')
PROFILE = BASE / 'sdk21-nonheld12-compile-preparation-1/SDK21-COMPILE.SOURCE-ONLY.json'
PROFILE_SHA = 'c88825ef2e2cfbf28e8e244c2010748c493bdb0924fc333a69b79eb80d627d69'
RUST = 'rust/mckernel_rust.o'
GENERIC = 'CMakeFiles/mckernel.img.dir/syscall.c.o'
ARCH = 'CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o'


def digest(p):
    b = Path(p).read_bytes()
    return {'path': str(p), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}


def authenticate(ref):
    actual = digest(ref['path'])
    assert actual['sha256'] == ref['sha256'], ref['path']
    if 'bytes' in ref:
        assert actual['bytes'] == ref['bytes'], ref['path']
    return Path(ref['path'])


def load_nodes(profile):
    template = profile['original_oracle_and_validation']['validator_template']
    authenticate(template)
    document = json.loads(Path(template['path']).read_bytes())
    rows = profile['original_oracle_and_validation']['frozen_nodes']
    assert rows == document['validator_nodes']
    space = dict(Path=Path, ast=ast, collections=collections, hashlib=hashlib, json=json, struct=struct)
    for row in rows:
        path = authenticate(row['source'])
        raw = path.read_text()
        matches = [n for n in ast.parse(raw).body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == row['name']]
        assert len(matches) == 1
        node = matches[0]
        assert (node.lineno, node.end_lineno) == (row['first_line'], row['last_line'])
        assert hashlib.sha256(ast.get_source_segment(raw, node).encode()).hexdigest() == row['source_segment_sha256']
        assert hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest() == row['AST_sha256']
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(path) + ':authenticated-node', 'exec'), space)
    space.update(rels=space['_reuse_elf_owning_relocations'], data=space['_reuse_elf_object_bytes'],
                 host=None, HOST_FILE=b'', PROD_FILE=b'', HOST_X86_FILE=b'', PROD_X86_FILE=b'',
                 finite_sections={'.lrodata.' + n for n in ('process_add_range_log_bridge','process_init_stack_log_bridge','process_range_public_log_bridge','process_remove_range_log_bridge','process_sched_runq_log_bridge')})
    return space


def expected_records(rows):
    assert len(rows) == 389 and all(r['padding'] == 0 for r in rows)
    return [(r['file'].encode().hex()+'00', r['function'].encode().hex()+'00',
             None if r['fmt'] is None else r['fmt'].encode().hex()+'00',
             r['line'] | (r['flags'] << 24)) for r in rows]


def make_first_rule(path):
    # Read only the first make rule. Fail closed on unsupported or malformed syntax.
    text = Path(path).read_text().replace('\\\n', ' ')
    line = text.splitlines()[0]
    left, right = line.split(':', 1)
    lexer = shlex.shlex(right, posix=True); lexer.whitespace_split = True; lexer.commenters = ''
    deps = list(lexer)
    assert left.strip() and deps
    return left.strip(), deps


def inspect(work, worker_path, binding_path):
    # No result constitutes a producer receipt, authorization or acceptance.
    assert digest(PROFILE)['sha256'] == PROFILE_SHA
    profile = json.loads(PROFILE.read_bytes())
    binding = json.loads(Path(binding_path).read_bytes())
    assert binding['profile_sha256'] == PROFILE_SHA
    assert profile['actual_artifacts'] is None and profile['authority'] is None
    orders = profile['link']['order']; rebuilt = profile['link']['rebuild']
    assert len(orders) == len(set(orders)) == 11 and set(rebuilt) == {RUST, GENERIC, ARCH}
    retained = profile['link']['retained_8']
    assert len(retained) == 8 and {r['token'] for r in retained} == set(orders)-set(rebuilt)
    worker = json.loads(Path(worker_path).read_bytes())
    assert len(worker['commands']) == len(profile['commands']) == 4
    root = Path(work).resolve(); build = root / 'output/build/kernel'
    for actual, planned in zip(worker['commands'], profile['commands']):
        assert actual['argv'] == planned['argv'] and actual['cwd'] == planned['cwd'] and actual['returncode'] == 0
        token = Path(planned['output']).relative_to('/work')
        observed = digest(root / token)
        assert (actual['output']['sha256'],actual['output']['bytes']) == (observed['sha256'],observed['bytes'])
        assert actual['output']['path'] == planned['output']
    assert [x for x in worker['commands'][-1]['argv'] if x.endswith('.o')] == orders
    for row in retained:
        authenticate(row)
        a = digest(build / row['token'])
        assert (a['sha256'],a['bytes']) == (row['sha256'],row['bytes'])
    # These identities and the dependency resolution must be supplied from actual
    # independently reviewed producer evidence, never synthesized by this adapter.
    excluded = binding['old_objects']
    assert set(excluded) == {'generic', 'arch'}
    for kind, token in [('generic',GENERIC),('arch',ARCH)]:
        assert excluded[kind] and all(authenticate(ref) for ref in excluded[kind])
        assert digest(build/token)['sha256'] not in {r['sha256'] for r in excluded[kind]}
    linkmap = build/'mckernel.img.map'; linkdep = build/'CMakeFiles/mckernel.img.dir/link.d'
    maptext=linkmap.read_text(); _, linktokens=make_first_rule(linkdep)
    maploads=[line[5:].strip() for line in maptext.splitlines() if line.startswith('LOAD ') and line[5:].strip().endswith('.o')]
    assert maploads == orders
    for token in orders:
        assert token in linktokens, token
    assert {x for x in linktokens if x.endswith('.o')} == set(orders)
    assert not any('witness' in x.lower() for x in linktokens)
    depfiles = {'rust':build/'rust/mckernel_rust.d', 'generic':build/(GENERIC+'.d'), 'arch':build/(ARCH+'.d')}
    depfacts = {}
    assert set(binding['dependencies']) == set(depfiles)
    for kind,path in depfiles.items():
        target,tokens=make_first_rule(path)
        rows=binding['dependencies'][kind]
        assert rows and len(rows)==len(tokens) and [r['token'] for r in rows]==tokens
        for row in rows: authenticate(row['actual_file'])
        depfacts[kind]={'depfile':digest(path),'target':target,'dependencies':rows}
    origin=binding['arch_full_source_origin']; assert origin is not None
    authenticate(origin['receipt']); authenticate(origin['independent_review'])
    assert origin['source_sha256'] == profile['source_bindings']['overlay_hashes']['arch/x86_64/kernel/syscall.c']['sha256']
    assert origin['source_logical_path'] == '/src/arch/x86_64/kernel/syscall.c'
    authenticate(origin['staged_source']); assert origin['staged_source']['sha256']==origin['source_sha256']
    receipt=json.loads(Path(origin['receipt']['path']).read_bytes())
    assert receipt['profile_sha256']==PROFILE_SHA and receipt['staged_source']==origin['staged_source']
    assert receipt['logical_path']==origin['source_logical_path']
    assert any(row['actual_file']['sha256']==origin['source_sha256'] and row['token']==origin['source_logical_path'] for row in binding['dependencies']['arch'])
    space = load_nodes(profile)
    objects = {n: space['_ReuseElf'](build/n) for n in orders}
    image = space['Final'](build/'mckernel.img')
    for e in [*objects.values(),image]:
        assert not any('witness' in s['name'].lower() for s in e.sections)
        assert not any('witness' in s['name'].lower() for s in e.symbols)
    providers = profile['selectors']['generic_functions'] + profile['selectors']['arch_functions']
    assert len(providers) == len(set(providers)) == 12
    proofs = []
    for name in providers:
        owners = [(token,s) for token,e in objects.items() for s in e.symbols if s['name']==name and s['shndx']]
        assert len(owners)==1 and owners[0][0]==RUST, (name,owners)
        symbol = owners[0][1]; final = image.sym(name)
        assert (symbol['bind'],symbol['type'],symbol['size']) == (final['bind'],final['type'],final['size']) and symbol['bind']==1 and symbol['type']==2 and symbol['size']>0
        _,_,_,relocations = space['relocated_function'](objects[RUST],name,image)
        proofs.append({'name':name, 'provider':RUST, 'final':final, 'relocations':relocations})
    assert not [s for s in image.symbols if s['shndx']==0 and s['bind']==1 and s['name']]
    cfuncs = {name: sorted(space['allocated'](objects[token],2)) for name,token in [('generic',GENERIC),('arch',ARCH)]}
    assert not (set(providers) & (set(cfuncs['generic']) | set(cfuncs['arch'])))
    assert 'do_signal' in cfuncs['arch']
    oracle_ref=profile['original_oracle_and_validation']['original389']; authenticate(oracle_ref)
    oracle=json.loads(Path(oracle_ref['path']).read_bytes()); assert oracle['count']==389
    observed=space['registry'](image); space['compare'](expected_records(oracle['records']), observed)
    return {'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing',
            'status':'BOUNDED_ARTIFACT_OBSERVATIONS_ONLY_NOT_ACCEPTANCE', 'profile':digest(PROFILE),
            'worker':digest(worker_path), 'objects':{n:digest(build/n) for n in orders},
            'image':digest(build/'mckernel.img'), 'providers':proofs, 'C_allocated_function_names':cfuncs,
            'link_map':digest(linkmap), 'link_depfile':digest(linkdep), 'dependencies':depfacts,
            'origin_input':origin, 'old_object_inputs':excluded, 'binding_input':digest(binding_path),
            'original389':{'oracle':oracle_ref,'count':len(observed),'full_tuple_multiset_equal':True},
            'required_separate_review':['actual producer, link map and link depfile, exact old generic/arch exclusions and witness absence',
             'all three actual depfiles and resolved source/header/tool origin closure',
             'fresh independently reviewed full-source origin receipt for arch source 78546125873dbf1f3619c2ce678bf9a07cc306b72db73f4597cc3d85ac4146de',
             'all other retained original artifact/consumer/ABI and native acceptance requirements'],
            'sdk21_qualification':False,'default_acceptance':False,'native_acceptance':False,'C_retirement':False,'runtime_authority':None}


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', required=True); parser.add_argument('--worker', required=True)
    parser.add_argument('--binding', required=True); parser.add_argument('--output', required=True)
    args=parser.parse_args()
    result=inspect(args.work,args.worker,args.binding)
    with Path(args.output).open('x') as f:
        json.dump(result,f,indent=2); f.write('\n')
