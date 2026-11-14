"""Single reviewed exit7 init-only offline proposal; no execution grant here.
Functional OS/apps plus compute-C to Rust/reviewed assembly. Existing archive,
app, image/modules and old collector remain retained. No subprocess or guest.
"""
from pathlib import Path
import ast, copy, hashlib, importlib.util, json, os, stat
D = Path(__file__).resolve().parent

def exact(row):
    p = Path(row['path']); a = p.lstat()
    assert stat.S_ISREG(a.st_mode) and a.st_mode == row['mode']
    raw = p.read_bytes(); b = p.lstat()
    assert (a.st_dev,a.st_ino,a.st_mode,a.st_size,a.st_mtime_ns,a.st_ctime_ns) == (b.st_dev,b.st_ino,b.st_mode,b.st_size,b.st_mtime_ns,b.st_ctime_ns)
    assert len(raw) == row['size'] and hashlib.sha256(raw).hexdigest() == row['sha256']
    return raw

def load(name, row):
    exact(row)
    spec = importlib.util.spec_from_file_location(name, row['path'])
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

def main():
    cfg = json.loads((D/'STAGE-INPUTS.json').read_bytes())
    for key in ('parent','parent_overlay','base','lineage_base','old_collector',
                'new_collector','new_collector_source','actual_checks','actual_check_review',
                'stage_engine','overlay_engine','evaluator','original_evaluator','evaluator_source_freeze'):
        exact(cfg[key])
    parent = json.loads(exact(cfg['parent']))
    tree = ast.parse(exact(cfg['evaluator']))
    nodes = [n for n in tree.body if isinstance(n, ast.Assign) and any(
        isinstance(t, ast.Name) and t.id == 'M03_CASE_BINDING' for t in n.targets)]
    assert len(nodes) == 1 and ast.literal_eval(nodes[0].value) == cfg['required_future_runtime_binding']
    original_tree = ast.parse(exact(cfg['original_evaluator']))
    original_nodes = [n for n in original_tree.body if isinstance(n, ast.Assign) and any(
        isinstance(t, ast.Name) and t.id == 'M03_CASE_BINDING' for t in n.targets)]
    assert len(original_nodes) == 1 and ast.literal_eval(original_nodes[0].value) == cfg['current_runtime_binding']
    binding = cfg['current_runtime_binding']
    assert binding['case_id'] == parent['case_id'] == cfg['case_id'] == 'startup.nonzero-dualstream.rust.exit7'
    assert binding['payload'] == parent['payload']
    assert binding['payload_artifact'] == parent['artifacts']['payload']
    assert binding['matched_modules'] == parent['modules'] and binding['matched_profile'] == parent['profile']
    for key, row in binding['matched_artifacts'].items(): assert parent['artifacts'][key] == row
    assert binding['accepted_stage_base'] == cfg['lineage_base']
    assert parent['staging']['derived_initramfs'] == cfg['base']
    assert parent['staging']['collector'] == cfg['old_collector']
    future = copy.deepcopy(binding); future['accepted_stage_base'] = cfg['base']
    assert future == cfg['required_future_runtime_binding']
    assert cfg['permitted_final_changes'] == ['init']
    engine = load('accepted_init_only_derive', cfg['stage_engine'])
    assert engine.CHANGED == frozenset(('init',))
    overlay_engine = load('accepted_archive_overlay', cfg['overlay_engine'])
    nd = load('unchanged_exit7_structural_validator', cfg['evaluator'])
    assert nd.M03_CASE_BINDING == cfg['required_future_runtime_binding']
    old_map = json.loads(exact(cfg['parent_overlay']))['final_map']
    output = Path(cfg['output']); assert output.parent == D and not os.path.lexists(output)
    output.mkdir(mode=0o700)
    archive = output/'exit7.cpio.gz'
    overlay = engine.derive(overlay_engine, cfg['base'], binding['payload_artifact'],
        cfg['new_collector'], binding['matched_artifacts']['mcexec'], archive, old_map)
    engine.retained_map(old_map, overlay['final_map'])
    assert overlay['final_map']['init']['sha256'] == cfg['new_collector']['sha256']
    engine.js(output/'overlay-manifest.json', overlay)
    manifest = copy.deepcopy(parent)
    manifest['artifacts']['initramfs'] = manifest['artifacts']['root_base'] = cfg['base']
    manifest['staging'] = dict(base_initramfs=cfg['base'],collector=cfg['new_collector'],
        derived_initramfs=engine.ref(archive),overlay_manifest=engine.ref(output/'overlay-manifest.json'),
        overlay_source=cfg['overlay_engine'])
    assert manifest['payload'] == binding['payload'] and manifest['modules'] == parent['modules']
    nd._validate_manifest(manifest)
    engine.js(output/'manifest.json', manifest)
    assert nd.load_manifest(str(output/'manifest.json')) == manifest
    used = sum(p.stat().st_size for p in output.iterdir())
    assert used <= 64 << 20
    engine.js(output/'stage-result.json', dict(status='EXIT7_INIT_ONLY_OFFLINE_STAGE',
        manifest=engine.ref(output/'manifest.json'),bytes=used,permitted_final_changes=['init'],
        accepted_original_archive_prefix_unchanged=True,app_unchanged=True,
        required_future_runtime_binding=cfg['required_future_runtime_binding'],
        runtime_blocker='Shared frozen c8fb evaluator bound; separate reviewed runtime owner and execution release still required',
        guest_runs=0,native_acceptance=False))
    print(json.dumps(dict(status='EXIT7_INIT_ONLY_OFFLINE_STAGE',files=4,guest_runs=0)))

if __name__ == '__main__': main()
