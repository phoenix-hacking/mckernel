"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Private current68 successor. Reuses the real M05 62-member stage and unchanged
overlay implementation. Only init collector changes against actual SDK5 base; M05 app,
two boot helpers, public probes and other61 members stay exact.
"""
from pathlib import Path
from contextlib import ExitStack
import argparse, copy, gc, hashlib, importlib.util, json, os, resource, shutil

HERE = Path(__file__).resolve().parent
BINDING_SHA256 = 'a0c17f4c93e388b354e31ff7c27f2771068b1f3e3950d075425530135970a2e3'
MEMBERS = {'init'}


def need(ok, why):
    if not ok:
        raise ValueError(why)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def load_binding():
    raw = (HERE / 'BINDING.json').read_bytes()
    need(digest(raw) == BINDING_SHA256, 'frozen binding hash')
    return json.loads(raw)


def authenticated(ov, row, stack):
    source = ov._Source(row['path'], stack)
    need(source.sha256 == row['sha256'] and len(source.data) == row['size']
         and source.identity['st_mode'] == row['mode'], 'authenticated input ' + row['path'])
    return source


def authorities(binding):
    """Authenticate small real authority records; no large artifact reread."""
    source = binding['overlay_source']
    need(digest(Path(source['path']).read_bytes()) == source['sha256'], 'overlay source pin')
    ov = module('m05_unchanged_overlay', source['path'])
    with ExitStack() as stack:
        docs = {name: json.loads(authenticated(ov, row, stack).data)
                for name, row in binding['authority'].items()}
        old = docs['baseline_overlay_manifest']['final_map']
        need(len(old) == 62 and docs['baseline_stage_result']['final_map'] == old,
             'actual 62-member predecessor map')
        sdk_artifact_authority(docs, binding)
        return old


def sdk_artifact_authority(docs, binding):
    """Select one exact reviewed SDK authority; never infer a profile."""
    sdk = docs['current_SDK_acceptance']
    profile = binding.get('authority_profile', 'current68-retained')
    if profile == 'current68-retained':
        need(sdk['status'] == 'PASS' and sdk['implementation_ownership'] is False
             and sdk['decision'] == 'ACCEPT_CURRENT68_RETAINED_LINKED_ARTIFACTS_AND_SOURCE_BINDINGS_ONLY',
             'independent current68 artifact authority')
    elif profile == 'current68-v3-build-link-physical':
        need(binding['authority']['current_SDK_acceptance']['path'] == '/home/holden/mckernel-work/host-preparation/current68-native235-production-binding-20261022-1/INDEPENDENT-ACTUAL-SDK68-V3-ARTIFACT-AND-PHYSICAL-ACCEPTANCE-1.json'
             and binding['authority']['current_SDK_acceptance']['sha256'] == '6a6a47b9899e8de45ab650023419b5a1af0596fb34865241cae263e0b19cac2f'
             and sdk['status'] == 'PASS' and sdk['implementation_ownership'] is False
             and sdk['decision'] == 'ACCEPT_ACTUAL_SDK68_V3_BUILD_LINK_ARTIFACTS_AND_HOST_PHYSICAL_RETIREMENT'
             and sdk['physical_acceptance'] is True and sdk['QEMU_or_guest_execution'] is False
             and sdk['native_or_P06_acceptance'] is False, 'exact independent V3 artifact authority')
        receipt = docs['v3_snapshot_receipt']
        need(binding['authority']['v3_snapshot_receipt']['path'] == '/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/fork-v3-matched-process-successor-1/module-runtime-snapshots-1/ACTUAL-THREE-MODULE-SNAPSHOT-RECEIPT.json'
             and binding['authority']['v3_snapshot_receipt']['sha256'] == '7eaaffb59663f27943c2f766ff4d737d790ade99349574349ba9453afa5cd33d'
             and receipt['status'] == 'PASS_THREE_ACTUAL_EXCLUSIVE_MODULE_RUNTIME_SNAPSHOTS'
             and receipt['independent_acceptance']['sha256'] == binding['authority']['current_SDK_acceptance']['sha256'],
             'exact V3 snapshot authority')
        need([row['name'] for row in receipt['modules']] == ['ihk.ko','ihk-smp-x86_64.ko','mcctrl.ko'], 'exact snapshot module names')
        for row in receipt['modules']:
            need(row['copied'] == binding['replacements']['modules/' + row['name']], 'exact actual V3 snapshot descriptor')
    elif profile == 'current68-sdk5-build-link-physical':
        need(binding['authority']['current_SDK_acceptance']['sha256'] == '8614e3e2bbf9e07c01f396079fc83fedbbb4119a3c37b5e311bdcc6cb6099623'
             and sdk['status'] == 'PASS' and sdk['implementation_ownership'] is False
             and sdk['decision'] == 'PASS_ACTUAL_SDK5_ARTIFACT_AND_PHYSICAL_ACCEPTANCE'
             and sdk['physical_acceptance'] is True and sdk['native_acceptance'] is False,
             'exact independent SDK5 artifact authority')
        matched = docs['sdk5_matched_manifest']
        need(binding['authority']['sdk5_matched_manifest']['sha256'] == 'fa8f54d7eb07906b167863314702ed948ed0d120214a8f40570d916baf2bcfae'
             and matched['modules'] == [binding['replacements'][name] for name in
                 ('modules/ihk.ko', 'modules/ihk-smp-x86_64.ko', 'modules/mcctrl.ko')]
             and matched['artifacts']['mckernel_image'] == binding['replacements']['images/mckernel.img']
             and matched['artifacts']['mcexec'] == binding['replacements']['bin/mcexec'],
             'exact SDK5 matched module/image/launcher descriptors')
    else:
        need(False, 'unknown SDK authority profile')
    for member, row in binding['replacements'].items():
        if member.startswith('modules/'):
            artifact = sdk['artifacts'][member.split('/')[-1]]
            wanted = {'bytes': row['size'], 'sha256': row['sha256']}
            need(({key: artifact[key] for key in wanted} if profile == 'current68-sdk5-build-link-physical'
                  else artifact) == wanted, 'SDK module descriptor join')


def validate_selection(selection, old, binding):
    need(set(selection) == MEMBERS and selection == {'init': binding['collector']},
         'exact one init collector change')
    need(len(old) == binding['expected_member_count'] == 62, 'exact predecessor membership')
    for name, row in binding['replacements'].items():
        need(old[name]['sha256'] == row['sha256'] and old[name]['size'] == row['size']
             and old[name]['mode'] == row['mode'] and old[name]['nlink'] == 1,
             'actual SDK5 predecessor member ' + name)
    for name, key in [('init', 'predecessor_collector'), ('apps/app', 'payload'),
                      ('bin/native-boot', 'first_boot'), ('bin/native-boot-second', 'second_boot')]:
        row, wanted = old[name], binding[key]
        need(row['sha256'] == wanted['sha256'] and row['size'] == wanted['size']
             and row['mode'] == 0o100755, 'unchanged real M05 member ' + name)
    need(binding['payload_contract']['oracle'] == {
        'exit_code': 0, 'stderr_hex': '',
        'stdout_hex': '68616e646c65643d31206f627365727665645f626c6f636b65643d3120726573746f7265643d310a'},
         'strict existing signal-mask workload oracle')
    final = copy.deepcopy(old)
    for name, row in selection.items():
        need(old[name]['mode'] == 0o100755 and row['mode'] == 0o100700 and old[name]['nlink'] == 1,
             'init guest0755 metadata preserved; authenticated compiler source0700')
        final[name].update(sha256=row['sha256'], size=row['size'])
    verify_delta(old, final, binding)
    return final


def verify_delta(old, final, binding):
    need(len(final) == 62 and set(final) == set(old), 'same exact 62-member namespace')
    need({name for name in old if old[name] != final[name]} == MEMBERS,
         'exact one init final member change')
    for name in old:
        expected = dict(old[name])
        if name == 'init':
            row = binding['collector']
            expected.update(sha256=row['sha256'], size=row['size'])
        need(final[name] == expected, 'exact final bytes/metadata ' + name)
    need(sum(old[name] == final[name] for name in old) == 61, '61 unchanged M05 members')


def rewrite_last_records(raw, replacement_data, ov):
    """Rewrite only final tuple records, retaining every other newc byte.

    Strict accepted parsing runs before and after. No new duplicate member or
    change to the accepted replay allowlist is introduced.
    """
    ov.parse_newc(raw)
    spans = []
    pos = 0
    while pos < len(raw):
        if raw[pos] == 0:
            begin = pos
            while pos < len(raw) and raw[pos] == 0:
                pos += 1
            spans.append((begin, pos, None, None, None))
            continue
        values = ov._fields(raw[pos:pos + 110])
        size, namesize = values[6], values[11]
        ne = pos + 110 + namesize
        name = raw[pos + 110:ne - 1].decode('utf-8')
        if name.startswith('./'):
            name = name[2:]
        ds = (ne + 3) & ~3
        end = (ds + size + 3) & ~3
        spans.append((pos, end, name, ds, values))
        pos = end
    last = {name: i for i, (_, _, name, _, _) in enumerate(spans) if name in MEMBERS}
    need(set(last) == MEMBERS, 'all replacement destinations exist')
    parts = []
    for i, (begin, end, name, ds, values) in enumerate(spans):
        if last.get(name) != i:
            parts.append(raw[begin:end])
            continue
        data = replacement_data[name]
        values[6] = len(data)
        values[12] = sum(data) & 0xffffffff if raw[begin:begin + 6] == b'070702' else 0
        header = raw[begin:begin + 6] + b''.join(('%08x' % value).encode('ascii') for value in values)
        parts.append(header + raw[begin + 110:ds] + data + b'\0' * (-len(data) % 4))
    patched = b''.join(parts)
    ov.parse_newc(patched)
    return patched


def ref(path):
    st = path.stat()
    return dict(path=str(path), sha256=digest(path.read_bytes()), size=st.st_size, mode=st.st_mode)


def write(path, data):
    with path.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def write_json(path, value):
    write(path, (json.dumps(value, indent=2) + '\n').encode())


def stage(binding):
    old = authorities(binding)
    validate_selection({'init': binding['collector']}, old, binding)
    out = Path(binding['output'])
    need(out == HERE / 'actual-stage-successor-1' and not os.path.lexists(out), 'fresh exact owned output')
    need(not any(path.is_symlink() for path in (HERE, *HERE.parents)), 'canonical output parents')
    need(shutil.disk_usage(HERE).free >= binding['host_floor_bytes'] +
         binding['max_output_aggregate_bytes'] + binding['capture_growth_bytes'], 'host floor/full growth')
    need(shutil.disk_usage('/home/holden/mckernel-work/scratch').free >=
         binding['scratch_floor_bytes'], 'scratch floor; source read only')
    ov = module('m05_unchanged_overlay_stage', binding['overlay_source']['path'])
    with ExitStack() as stack:
        base = authenticated(ov, binding['base'], stack)
        selected = {name: authenticated(ov, row, stack)
                    for name, row in binding['replacements'].items()}
        collector = authenticated(ov, binding['collector'], stack)
        payload = authenticated(ov, binding['payload'], stack)
        authenticated(ov, binding['first_boot'], stack)
        authenticated(ov, binding['second_boot'], stack)
        old_manifest = json.loads(authenticated(ov, binding['old_manifest'], stack).data)
        raw = ov._inflate(base.data, binding['max_inflated_base_bytes'])
        before = ov._manifest(ov._replay_records(ov.parse_newc(raw)[0]))
        need(before == old, 'actual predecessor archive exact accepted map')
        del before
        patched = rewrite_last_records(raw, {'init': collector.data}, ov)
        del raw
        gc.collect()
        need(len(patched) <= binding['max_patched_cpio_bytes'], 'patched cpio growth bound')
        after = ov._manifest(ov._replay_records(ov.parse_newc(patched)[0]))
        verify_delta(old, after, binding)
        os.umask(0o077)
        out.mkdir(mode=0o700)
        patched_base = out / 'base.cpio.gz'
        write(patched_base, ov._gzip(patched))
        base_cpio_sha, base_cpio_size = digest(patched), len(patched)
        del patched
        overlay = out / 'lifecycle.cpio.gz'
        om = ov.build_overlay(str(patched_base), payload.path.path, collector.path.path,
             selected['bin/mcexec'].path.path, str(overlay),
             collector_sha256=collector.sha256, mcexec_sha256=selected['bin/mcexec'].sha256,
             payload_sha256=payload.sha256, base_sha256=ref(patched_base)['sha256'],
             base_size=patched_base.stat().st_size, base_cpio_sha256=base_cpio_sha,
             base_cpio_size=base_cpio_size)
        verify_delta(old, om['final_map'], binding)
        om_path = out / 'overlay-manifest.json'
        write_json(om_path, om)
        m = old_manifest
        m['case_id'] = 'native.second-stop.current68.twoCPU.exact67.two-generation'
        m['cleanup_profile'] = binding['cleanup_profile']
        m['artifacts']['mckernel_image'] = binding['replacements']['images/mckernel.img']
        m['artifacts']['mcexec'] = binding['replacements']['bin/mcexec']
        m['modules'] = [binding['replacements'][name] for name in
                        ('modules/ihk.ko', 'modules/ihk-smp-x86_64.ko', 'modules/mcctrl.ko')]
        m['artifacts']['initramfs'] = m['artifacts']['root_base'] = ref(patched_base)
        m['staging'].update(collector=binding['collector'], base_initramfs=ref(patched_base), derived_initramfs=ref(overlay),
             overlay_manifest=ref(om_path), overlay_source=binding['overlay_source'])
        manifest_path = out / 'manifest.json'
        write_json(manifest_path, m)
        for source in [base, collector, payload, *selected.values()]:
            source.verify()
        nd_ref = binding['diagnostic_source']
        need(digest(Path(nd_ref['path']).read_bytes()) == nd_ref['sha256'], 'diagnostic source pin')
        nd = module('m05_unchanged_diagnostic', nd_ref['path'])
        nd.load_manifest(str(manifest_path))
        used = sum(p.stat().st_size for p in out.iterdir())
        need(used < binding['max_output_aggregate_bytes'] - 1024 * 1024, 'aggregate output/receipt bound')
        result = dict(status='PASS_CURRENT68_M05_STAGE_ONLY', manifest=ref(manifest_path),
                      base=ref(patched_base), overlay=ref(overlay), overlay_manifest=ref(om_path),
                      final_map=om['final_map'], changed_members=sorted(MEMBERS), unchanged_members=61,
                      binding_sha256=BINDING_SHA256, aggregate_bytes_before_receipt=used,
                      expected_epochs=binding['expected_epochs'], runtime_release=False, native_acceptance=False)
        write_json(out / 'stage-result.json', result)
        return result


def main():
    ap = argparse.ArgumentParser(allow_abbrev=False)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--preflight-only', action='store_true')
    mode.add_argument('--stage', action='store_true')
    args = ap.parse_args()
    need(os.sched_getaffinity(0) == {0} and resource.getrlimit(resource.RLIMIT_AS)[0] <= 536870912,
         'CPU0/512MiB ordinary profile')
    binding = load_binding()
    if args.preflight_only:
        old = authorities(binding)
        validate_selection({'init': binding['collector']}, old, binding)
        print(json.dumps(dict(status='PASS_EXACT_CURRENT68_M05_SELECTION_ONLY', members=62,
             changed=1, unchanged=61, cpio_transformations=0, runtime_release=False)))
    else:
        result = stage(binding)
        print(json.dumps({k: result[k] for k in ('status', 'changed_members', 'unchanged_members', 'runtime_release')}))


if __name__ == '__main__':
    main()
