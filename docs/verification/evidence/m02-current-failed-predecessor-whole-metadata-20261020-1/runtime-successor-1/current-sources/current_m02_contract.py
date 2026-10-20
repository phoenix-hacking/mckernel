"""Known current M02 evidence kinds; returns genuine objects, never old facts."""
from pathlib import Path
import hashlib
import json
import os

SOURCE_KIND = ('mckernel.independent-actual-M02-source-closure-outside-preflight-acceptance.v1',
    'PASS_NO_EFFECT_PREFLIGHT_ONLY',
    'PASS_ACTUAL_COMPLETE_M02_SOURCE_CLOSURE_OWNER_CREATE_INSIDE_QEMU_ARGV_AND_THREE_DRIFT_REFUSALS_ONLY')
POSITIVE_KIND = ('mckernel.independent-native-positive-physical-actual-two-witness-review.v1',
    'PASS_SOURCE_AND_ACTUAL_WHOLE_CONSUMER_CHECKS_ONLY',
    'PASS_EXACT_CURRENT_POSITIVE_NATIVE_OWNER_PHYSICAL_CONSUMER_AND_TWO_WITNESS_CHECKS')

def need(ok, reason):
    if not ok: raise ValueError(reason)

def ref(path):
    p = Path(path); raw = p.read_bytes()
    return dict(path=str(p), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

def checked(row):
    p = Path(row['path']); need(p.resolve(strict=True) == p and not p.is_symlink(), 'canonical full reference')
    raw = p.read_bytes(); need(len(raw) == row.get('bytes', row.get('size')) and hashlib.sha256(raw).hexdigest() == row['sha256'], 'full reference drift')
    if 'mode' in row: need(p.stat().st_mode == row['mode'], 'full reference mode')
    return json.loads(raw)

def kind(obj, expected):
    need(tuple(obj.get(k) for k in ('schema', 'status', 'decision')) == expected, 'wrong genuine evidence kind')
    return obj

def read_source(data, stage_ref, normalization_ref):
    source = kind(checked(data['actual_source_closure_acceptance']), SOURCE_KIND)
    need(source['current_owner'] == data['current_owner'], 'current owner evidence join')
    stage = checked(stage_ref)
    kind(stage, ('mckernel.independent-actual-exit7-init-only-offline-stage-acceptance.v1', 'PASS', 'PASS_ACTUAL_EXIT7_INIT_ONLY_RETIREMENT_GRACE_OFFLINE_STAGE'))
    normalization = checked(normalization_ref)
    kind(normalization, ('mckernel.independent-actual-exit7-native-preparation-acceptance.v1', 'PASS', 'PASS_ACTUAL_EXIT7_BYTE_EXACT_NORMALIZATION_FRESH_PARENT_AND_FULL_OWNER_CREATE_INSIDE_QEMU_ARGV_ONLY'))
    normalized = normalization['actual_normalized_manifest']
    for k in ('path', 'sha256'):
        need(normalized[k] == data['binding']['manifest'][k], 'unchanged S5 normalized manifest')
    physical = checked(data['latest_exclusive_physical'])
    if data.get('physical_reader_kind') == 'CURRENT_CHILD_FAILED_NATIVE':
        acceptance = kind(checked(data['failed_native_reader_actual_acceptance']), (
            'mckernel.independent-actual-M02-current-child-failure-reader-and-LAST-body-acceptance.v1',
            'PASS_SOURCE_AND_ACTUAL_CURRENT_TERMINAL_BODY_CHECKS_ONLY',
            'PASS_EXACT_CURRENT_CHILD_FAILURE_READER_AND_ACTUAL_UNCHANGED_M02_LAST_TERMINAL_BODY_POSITIVE_AND_SIX_PRECISE_REFUSALS_ONLY'))
        reader, context = data['failed_native_reader_candidate'], data['failed_native_reader_context']
        need(acceptance['accepted_reader'] == reader and acceptance['accepted_context'] == context, 'genuine current failed-reader source and context')
        need(acceptance['genuine_bound_roles']['physical_FD'] == data['latest_exclusive_physical'], 'genuine current failed physical role')
        need(acceptance['facts']['decoder_source_acceptance'] is True and acceptance['facts']['whole_source_body_pass'] is True and acceptance['facts']['whole_current_control_deployment_acceptance'] is False, 'source decoder acceptance only; current deployment remains independent')
        ctx = checked(context)
        need(acceptance['genuine_bound_roles']['host_census_acceptance']['path'] == ctx['host_census_acceptance']['path'] and acceptance['genuine_bound_roles']['host_census_acceptance']['sha256'] == ctx['host_census_acceptance']['sha256'], 'genuine fresh census acceptance retained')
        need(acceptance['genuine_bound_roles']['native_release']['path'] == ctx['native_release']['path'] and acceptance['genuine_bound_roles']['native_release']['sha256'] == ctx['native_release']['sha256'] and acceptance['genuine_bound_roles']['metadata_release']['path'] == ctx['metadata_release']['path'] and acceptance['genuine_bound_roles']['metadata_release']['sha256'] == ctx['metadata_release']['sha256'], 'genuine predecessor native and metadata roles remain distinct')
    else:
        need(data.get('physical_reader_kind') in (None, 'NATIVE_POSITIVE'), 'known physical reader selection')
        acceptance = kind(checked(data['positive_reader_actual_acceptance']), POSITIVE_KIND)
        reader, context = data['positive_reader_candidate'], data['positive_reader_context']
        need(acceptance['genuine_current_physical'] == ref(data['latest_exclusive_physical']['path']), 'current physical descriptor')
        need(acceptance['source']['path'] == reader['path'] and acceptance['source']['sha256'] == reader['sha256'], 'current positive reader')
        need(acceptance['context']['path'] == context['path'] and acceptance['context']['sha256'] == context['sha256'], 'current positive context')
    return dict(source_acceptance=source, stage_acceptance=stage, normalization_acceptance=normalization,
                physical_consumer_acceptance=acceptance, physical_reader_source=reader,
                physical_reader_context=context, physical=physical)

def read(data_ref, fresh_ref, stage_ref, normalization_ref, fetched_proof=None, require_publication=False, allow_fixture=False):
    data = checked(data_ref); need(allow_fixture or not data.get('fixture_only',False),'fixture DATA cannot satisfy production'); result = read_source(data, stage_ref, normalization_ref)
    fresh = checked(fresh_ref)
    need(fresh.get('fixture_only',False)==data.get('fixture_only',False),'fixture role mismatch')
    need(allow_fixture or not fresh.get('fixture_only',False),'fixture record cannot satisfy production')
    need(fresh.get('schema') == 'mckernel.m02-actual-fresh-parent-and-full-preflight.v1' and
         fresh.get('status') == 'PASS_ACTUAL_FRESH_PARENT_AND_COMPLETE_NO_EFFECT_PREFLIGHT_ONLY', 'genuine current fresh-parent producer result')
    need(fresh['binding'] == data['binding'] and fresh['current_owner'] == data['current_owner'], 'fresh current binding')
    pre = fresh['actual_full_preflight']
    need(pre['clocks_or_host_effects'] == 0 and pre['native_execution_release'] is None, 'current no-effect preflight')
    for k in ('owner_argv', 'inside_owner_argv', 'container_create_argv', 'qemu_argv'):
        need(pre[k] == data['prospective_full_argv'][k], 'whole current argv: ' + k)
    need(pre['paths']['qmp_socket'] == data['QMP']['path'] and pre['paths']['qmp_socket_bytes'] == 99, 'current QMP99')
    need(fresh['final19_outputs'] == data['final19_outputs'] and fresh['capture_paths'] == data['capture_paths'], 'current complete namespaces')
    full = fresh['parent_full9']; p = Path(data['prospective_parent']); s = p.lstat()
    attrs = {'device':'st_dev','inode':'st_ino','mode':'st_mode','uid':'st_uid','gid':'st_gid','nlink':'st_nlink','size':'st_size','mtime_ns':'st_mtime_ns','ctime_ns':'st_ctime_ns'}
    need(set(full) == set(attrs) and all(full[k] == getattr(s,v) for k,v in attrs.items()), 'actual fresh parent full9')
    need(fresh['parent_empty'] is True and not list(p.iterdir()), 'actual empty parent')
    need(not os.path.lexists(data['prospective_attempt']) and not os.path.lexists(data['prospective_owner_evidence']), 'fresh owned runtime paths')
    legacy = dict(device=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,mode=oct(s.st_mode & 0o7777))
    if require_publication:
        need(fetched_proof is not None, 'current fetched source proof unresolved')
        proof = checked(fetched_proof)
        need(proof.get('verified') is True and proof.get('commit') == proof.get('fetched_commit'), 'actual current fetched proof')
        required = [data['current_owner']] + [x['private'] for x in data['HERE_runtime_sources']]
        source = Path(__file__).resolve().parent
        for name in ('current_m02_contract.py','CURRENT-SOURCE-CONTEXT.json','bind_m03_handshake_native_packet.py','root_manual_snapshot_m03.py','materialize_current_m02_once.py','review_final_205_release.py','machine_assembly_caller.py'):
            required.append(ref(source/name))
        required += [ref(source.parent/'prepare_current_parent_once.py'),data_ref, result['physical_reader_source'], result['physical_reader_context']]
        covered = {(r['sha256'],r.get('bytes',r.get('size'))) for r in proof.get('rows',[])}
        need(all((r['sha256'],r.get('bytes',r.get('size'))) in covered for r in required), 'complete current source publication coverage')
    result.update(data=data, fresh=fresh, preflight=pre, binding=fresh['binding'], parent_legacy=legacy,
        parent_stat_fields={v:full[k] for k,v in attrs.items()})
    return result
