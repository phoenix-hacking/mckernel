"""Retained-data analysis only. No workload, imports of runtime owners, or trace construction."""
from pathlib import Path
import ast
import base64
import hashlib
import json
import re

BASE = Path('/home/holden/mckernel-work/host-preparation')
OUT = Path(__file__).parent
READ = BASE / 'velocity-intervention-20261023-13/foreground-live-workload-read-1'
RUNTIME = BASE / 'velocity-intervention-20261023-10/qmp-runtime-successor-1/source'
HANDOFF = BASE / 'p12-long-first-round-progress-expert-20261023-1/runtime-sdk8-snapshot-equality-successor-1/capsule-preparation-1/ACTUAL-SNAPSHOT-EQUALITY-COLLECTOR-CAPSULE-HANDOFF.json'
MANIFEST = Path('/home/holden/mckernel-work/scratch/p12q1/m.json')

def sha(data):
    return hashlib.sha256(data).hexdigest()

def pin(path):
    path = Path(path)
    data = path.read_bytes()
    return dict(path=str(path), bytes=len(data), sha256=sha(data))

def need(value, why):
    if not value:
        raise ValueError(why)

def unique(pairs):
    out = {}
    for key, value in pairs:
        need(key not in out, 'duplicate JSON key')
        out[key] = value
    return out

def record(data):
    def constant(value):
        raise ValueError('nonfinite JSON')
    return json.loads(data, object_pairs_hook=unique, parse_constant=constant)

def keys(value, names):
    need(type(value) is dict and set(value) == set(names), 'keys')

def integer(value, minimum=0):
    return type(value) is int and value >= minimum

wrapper = record((READ/'stdout').read_bytes())
raw = base64.b64decode(wrapper['prefix']['base64'], validate=True)
need(sha(raw) == wrapper['prefix']['sha256'], 'prefix digest')
need(len(raw) == wrapper['prefix']['bytes'] == wrapper['prefix']['complete_line_bytes'], 'prefix byte counts')
need(not wrapper['prefix']['capped_before_initial_EOF'] and wrapper['prefix']['unparsed_incomplete_tail_bytes'] == 0, 'uncapped complete prefix')
need(raw.isascii() and b'\0' not in raw and raw.endswith(b'\n'), 'prefix encoding')
serial = raw.decode('ascii')
lines = serial.splitlines()
manifest = record(MANIFEST.read_bytes())
handoff = record(HANDOFF.read_bytes())
rows = {}
for index, line in enumerate(lines):
    if line.startswith('ND_'):
        name, _, data = line.partition(' ')
        rows.setdefault(name, []).append((index, record(data) if data else None))

need(set(rows) == {'ND_PAIR_LONG_PROFILE', 'ND_PAIR_ROUND_START', 'ND_PAIR', 'ND_PAIR_ROUND_END', 'ND_PAIR_LONG_PROGRESS', 'ND_PAIR_LONG_ABORT'}, 'unexpected wire marker')
need(len(rows['ND_PAIR_LONG_PROFILE']) == 1 and rows['ND_PAIR_LONG_PROFILE'][0][1] == manifest['pair_long_session'], 'profile')
starts, reports, ends, progress = [rows[k] for k in ('ND_PAIR_ROUND_START', 'ND_PAIR', 'ND_PAIR_ROUND_END', 'ND_PAIR_LONG_PROGRESS')]
need((len(starts), len(reports), len(ends), len(progress)) == (630, 629, 629, 629), 'round counts')
need(len(rows['ND_PAIR_LONG_ABORT']) == 2, 'abort count')
need(rows['ND_PAIR_LONG_PROFILE'][0][0] < starts[0][0], 'profile order')

closure = {}
for name, entry in handoff['source_closure'].items():
    actual = pin(entry['materialized']['path'])
    need(actual['sha256'] == entry['materialized']['sha256'] == entry['selected']['sha256'], 'source closure '+name)
    need(actual['bytes'] == entry['materialized']['bytes'], 'source size '+name)
    closure[name] = actual
need(len(closure) == 17, 'source closure count')
for key in ('collector', 'capsule'):
    target = {'collector':'collector', 'capsule':'derived_initramfs'}[key]
    need(manifest['staging'][target]['sha256'] == handoff[key]['sha256'], 'manifest '+key)
need(manifest['artifacts']['mckernel_image']['sha256'] == handoff['image']['sha256'], 'manifest kernel')
need(manifest['artifacts']['mcexec']['sha256'] == handoff['launcher']['sha256'], 'manifest launcher')
need({Path(r['path']).name:r['sha256'] for r in manifest['modules']} == handoff['SDK8_modules'], 'manifest modules')
oracle_header = Path(closure['pair_round_oracles.h']['path']).read_text()
for app in manifest['pair']['apps']:
    match = re.search(r'pair_round_stdout_'+str(app['id'])+r'\[\] = \{([^}]+)\}', oracle_header)
    need(bytes(map(int, match.group(1).split(','))).hex() == app['oracle']['stdout_hex'], 'frozen C/manifest oracle equality')

seen = set()
total = 0
previous_end = 0
rounds = []
all_phases = ['round-evidence', 'callback-discover', 'callback-launch', 'callback-load', 'callback-postflight', 'callback-gate', 'callback-report']
for rnd, ((si, start), (ri, report), (ei, end), (pi, step)) in enumerate(zip(starts, reports, ends, progress)):
    for boundary in (start, end):
        keys(boundary, ('round', 'time_ns', 'procfs_empty'))
        need(integer(boundary['round']) and boundary['round'] == rnd and integer(boundary['time_ns'],1) and boundary['procfs_empty'] is True, 'boundary')
    need(si < ri < ei < pi and previous_end <= start['time_ns'] < end['time_ns'], 'round order')
    if rnd:
        need(progress[rnd-1][0] < si, 'interleaved round')
    phases = [line.split(' stage=',1)[1] for line in lines[si+1:ri] if line.startswith('P12_LONG_PHASE round='+str(rnd)+' stage=')]
    need(phases == all_phases, 'callback phases')
    keys(report, ('os','generation','host_cpus','cpus','procfs_empty','apps'))
    need(integer(report['os']) and report['os'] == 0 and integer(report['generation']) and report['generation'] == 1 and report['host_cpus'] == [1,2] and report['cpus'] == [0,1] and report['procfs_empty'] is True, 'report domain')
    need(type(report['apps']) is list and len(report['apps']) == 2, 'app count')
    for app, expected in zip(report['apps'], manifest['pair']['apps']):
        keys(app, ('id','pid','cpu','cwd','argv','env','raw_wait_status','clean','fault','timeout','started_ns','reaped_ns','finished_ns','streams'))
        need(integer(app['id']) and app['id'] == expected['id'] and integer(app['cpu']) and app['cpu'] == expected['cpu'], 'app CPU/id')
        need(integer(app['pid'],1) and app['pid'] not in seen, 'app PID unique')
        seen.add(app['pid'])
        need(all(app[k] == expected[k] for k in ('cwd','argv','env')), 'reported launch metadata')
        need(all(type(app[k]) is int for k in ('raw_wait_status','clean','fault','timeout')) and tuple(app[k] for k in ('raw_wait_status','clean','fault','timeout')) == (0,1,0,0), 'app status')
        need(all(integer(app[k],1) for k in ('started_ns','reaped_ns','finished_ns')), 'app time types')
        need(start['time_ns'] <= app['started_ns'] <= app['reaped_ns'] <= app['finished_ns'] <= end['time_ns'] and app['reaped_ns']-app['started_ns'] <= 10_000_000_000, 'app time order/deadline')
        keys(app['streams'], ('stdout','stderr'))
        for name, stream in app['streams'].items():
            keys(stream, ('hex','eof','truncated','observed','retained','discarded','limit','eof_ns'))
            need(type(stream['hex']) is str and re.fullmatch(r'(?:[0-9a-f]{2})*', stream['hex']) is not None, 'stream hex')
            data = bytes.fromhex(stream['hex'])
            need(all(integer(stream[k]) for k in ('observed','retained','discarded','limit','eof_ns')), 'stream ints')
            need(stream['eof'] is True and stream['truncated'] is False and stream['observed'] == stream['retained'] == len(data) <= 1024 and stream['discarded'] == 0 and stream['limit'] == 1024, 'stream accounting')
            need(data == bytes.fromhex(expected['oracle'][name+'_hex']) and app['started_ns'] <= stream['eof_ns'] <= app['finished_ns'], 'stream oracle/EOF time')
    apps = report['apps']
    low = min(app['started_ns'] for app in apps)
    high = max(app['reaped_ns'] for app in apps)
    overlap = min(app['reaped_ns'] for app in apps)-max(app['started_ns'] for app in apps)
    need(overlap > 0, 'app overlap')
    work = high-low
    total += work
    keys(step, ('round','work_ns','cumulative_work_ns','launches'))
    need(all(integer(v) for v in step.values()) and step == dict(round=rnd, work_ns=work, cumulative_work_ns=total, launches=(rnd+1)*2), 'progress accounting')
    need(end['time_ns']-reports[0][1]['apps'][0]['started_ns'] < manifest['pair_long_session']['wall_ns'], 'round wall bound')
    rounds.append(dict(round=rnd, start_line=si+1, report_line=ri+1, end_line=ei+1, progress_line=pi+1, work_ns=work, overlap_ns=overlap, pids=[a['pid'] for a in apps]))
    previous_end = end['time_ns']
need(starts[-1][1]['round'] == 629 and starts[-1][0] > progress[-1][0], 'failed round exclusion')
need(not any('FAIL' in line or 'ABORT' in line for line in lines[:progress[-1][0]+1]), 'prior failure')
need(total == wrapper['producer_reported_mixed_work_ns'] == wrapper['last_complete_progress']['cumulative_work_ns'] == 3519690949712, 'wrapper total')
need(len(seen) == wrapper['producer_reported_completed_launches'] == 1258, 'wrapper launches')
failure = next(line for line in lines if line.startswith('P12_LONG_FAILURE '))
need('round=629 stage=callback-report pair_stage=trace_retention result=-3 ownership_complete=1 rounds=629 launches=1258 trace_bytes=150512132' in failure, 'failure summary')

# Reuse unchanged pure strict trace functions on the actual failure snapshot only.
# This does not create, splice, or pass any synthetic trace to an oracle.
trace_source = (RUNTIME/'native_diagnostic.py').read_text()
tree = ast.parse(trace_source)
frozen_strict_ref = handoff['source_refs']['native_diagnostic.py']
frozen_strict_pin = pin(frozen_strict_ref['path'])
need(frozen_strict_pin['sha256'] == frozen_strict_ref['sha256'], 'frozen strict checker hash')
frozen_nodes = {node.name: ast.dump(node,include_attributes=False) for node in ast.parse(Path(frozen_strict_ref['path']).read_text()).body if isinstance(node,(ast.ClassDef,ast.FunctionDef))}
current_nodes = {node.name: ast.dump(node,include_attributes=False) for node in tree.body if isinstance(node,(ast.ClassDef,ast.FunctionDef))}
unchanged_functions = {name: frozen_nodes[name] == current_nodes[name] for name in ('DiagnosticError','_need','_pair_trace','_check_begin_cleanup','_pair_body')}
need(all(unchanged_functions.values()), 'unchanged strict functions')
selected = [node for node in tree.body if isinstance(node,(ast.ClassDef,ast.FunctionDef)) and node.name in ('DiagnosticError','_need','_pair_trace','_check_begin_cleanup')]
env = dict(re=re)
exec(compile(ast.Module(body=selected,type_ignores=[]), str(RUNTIME/'native_diagnostic.py'), 'exec'), env)
begin = next(i for i,l in enumerate(lines) if l.startswith('P12_LONG_FAILURE_TRACE_BEGIN '))
finish = next(i for i,l in enumerate(lines) if l.startswith('P12_LONG_FAILURE_TRACE_END '))
snapshot = '\n'.join(lines[begin+1:finish])+'\n'
declared = int(re.search(r'bytes=(\d+)',lines[begin]).group(1))
# Raw serial uses CRLF framing. The original exported snapshot uses LF bytes.
need(len(snapshot.encode()) == declared, 'exact failure snapshot bytes')
present = {int(v) for v in re.findall(r'application(?:_syscall=\w+| SCHEDULE| retirement|_process=\w+| cleanup ACK| procfs \w+) os=0 generation=1 pid=(\d+)(?: |$)', snapshot)}
trace_replay = []
for rnd, (_, report) in enumerate(reports):
    for app in report['apps']:
        if app['pid'] not in present:
            continue
        result = dict(round=rnd, pid=app['pid'], cpu=app['cpu'])
        try:
            env['_pair_trace'](snapshot,app['pid'],app['cpu'],True)
            prefix = r'os=0 generation=1 pid='+str(app['pid'])
            for pattern in (r'application SCHEDULE '+prefix+r' cpu='+str(app['cpu'])+r'\b',*[r'application procfs '+op+' '+prefix+r' tid='+str(app['pid'])+r'\b' for op in ('published','deleted')]):
                need(len(re.findall(pattern,snapshot)) == 1, 'schedule/procfs exact counts')
            result['status'] = 'ACTUAL_FAILURE_SNAPSHOT_PID_TRACE_PASS'
        except (ValueError,env['DiagnosticError']) as error:
            result.update(status='INCOMPLETE_OR_FAIL', reason=str(error))
        trace_replay.append(result)

result = dict(
    scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
    status='CONDITIONAL_SOURCE_BOUND_PRODUCER_CHECKED_COMPLETED_PREFIX_ELIGIBLE',
    qualification_mode='producer_checked_completed_prefix_with_independent_report_replay',
    original_uninterrupted_attempt='FAIL',
    full_native_or_strict_long_trace_acceptance=False,
    independent_all_prefix_raw_trace_replay=False,
    source_stdout=pin(READ/'stdout'),
    raw_prefix=dict(bytes=len(raw),sha256=sha(raw),uncapped=True,partial_tail_bytes=0),
    capture_identity=dict(nonce=wrapper['nonce'],serial_path=wrapper['serial_path'],anchor_before=wrapper['anchor_before'],anchor_after=wrapper['anchor_after'],consistent=wrapper['anchor_identity_consistent']),
    admission_condition='Root must bind this nonce/capture to the admitted actual runtime manifest/source cohort and close identity/retirement. Raw serial has no nonce or artifact digest; wrapper/path alone do not prove actual boot identity.',
    manifest=pin(MANIFEST), source_handoff=pin(HANDOFF), frozen_materialized_source_closure=closure,
    source_bound_manifest_identities=dict(kernel=manifest['artifacts']['mckernel_image'],launcher=manifest['artifacts']['mcexec'],modules=manifest['modules'],collector=manifest['staging']['collector'],capsule=manifest['staging']['derived_initramfs'],apps=[a['payload'] for a in manifest['pair']['apps']]),
    profile=manifest['pair_long_session'],
    independent_report_replay=dict(status='PASS',rounds=629,launches=1258,unique_pids=len(seen),mixed_work_ns=total,mixed_work_seconds='3519.690949712',mixed_work_duration='58m39.690949712s',remaining_to_60min_ns=3600000000000-total,overlap_all_rounds=True,min_overlap_ns=min(r['overlap_ns'] for r in rounds),work_definition='sum(max app.reaped_ns - min app.started_ns), one union span per overlapping two-app round; excludes setup/inter-round/retention time',checks=['strict duplicate-key/nonfinite JSON rejection','exact record schemas and profile','sequential START/ND_PAIR/END/PROGRESS for rounds0..628','all seven callback phases before each report','two apps with distinct global positive PIDs and exact domain/CPU/argv/env/cwd metadata','exact frozen C and selected manifest stdout byte oracles, empty stderr, zero exits/fault/timeouts, clean1','all stream byte/EOF/truncation/accounting/EOF-time values','monotonic app/round bounds, <=10s app deadlines, actual pair overlap','per-round union and cumulative counter arithmetic','no FAIL/ABORT before final credited progress','failed round629 excluded']),
    producer_checked_but_not_all_independently_trace_replayed=['actual assignment nonce/source-generation/CPU route and resource discovery','successful joined supervisor ownership domains and clean descendants','procfs emptiness plus unchanged/empty workspace before/after rounds','settled terminal retirement for both apps','C strict stream/identity gate and global PID ledger','C per-app syscall delivery/return/route/terminal/ACK/retirement/procfs/schedule gate with global retirement-token ledger','trace membership exclusion of foreign application PIDs','immutable per-round trace file and authenticated in-memory copy with trace cap','exact long spool retention write and metadata identity before progress'],
    unsupported_host_strict_predicates_for_all629=[
        dict(predicate='Every app has a nonempty returned set AND a nonempty return_route set.',host='native_diagnostic.py:1113',online_gap='long_support.inc:148..154 requires each present ordinary delivery returned and checks any present routes, but allows no ordinary calls or zero return_route records. ND_PAIR contains no syscall/route counters.34 suffix PIDs independently satisfy the host function; the other1224 are not independently established.'),
        dict(predicate='Exact NATIVE_PAIR_CPU os0/gen1 assigned_host1,2 logical0,1 default_ikc_linux0 readback line exists.',host='native_diagnostic.py:1192',online_gap='pair_discover validates assignment/ranks/resources, but its pair_routes parser does not require this exact text marker. ND_PAIR reports CPU metadata without the raw readback.'),
        dict(predicate='Two startup channel records contain positive cookie, receive/send/remote_cookie pointers, distinct cookies, correct queue byte size and pairwise nonoverlapping queues.',host='native_diagnostic.py:1197..1206',online_gap='pair_assignment.h:pair_routes validates domain/generation/port/rank/physical CPU and the literal cookie= delimiter, then stops; it does not parse/check cookies, pointers, queue lengths or queue disjointness. ND_PAIR has none of those fields.'),
        dict(predicate='All original raw trace bytes have exact enclosing LONG trace begin/end counts, bounded startup projection, all-domain application membership and per-round projection suitable for the unchanged host pair checker.',host='p12_long_session.py:84..149,163..167',online_gap='Online retention/file/spool checks occurred before progress, but the original producer only publishes the full archive after work quota; that phase was not reached. The failure snapshot is a bounded suffix. No full-prefix raw archive or all629 host strict pair pass is claimed.'),
        dict(predicate='Successful original terminal LONG completion and host lifecycle/final physical retirement/restoration.',host='p12_long_session.py:84..97,191..198 plus native host lifecycle owner',online_gap='Original attempt emits failure/ABORT and stays FAIL. Parent/root separately owns final failed-runtime retirement and any admitted continuation.'),
    ],
    producer_gate_source_ranges=dict(long_bridge_inc='95..142; long_pair callback-gate116 precedes callback-report117; long_retain133..142',long_support_inc='63..83 exact streams/PIDs/overlap;85..155 C trace oracle;159..176 gate;39..61 workspace',pair_long_producer_rs='141..207 all checks/retain/report precede progress;213..226 full-trace publication only after quota',long_trace_retention_inc='32..89 historical membership and immutable saved trace',retirement_settlement_inc='10..73 positive settled retirement snapshot',pair_runtime_inc='29..73 assignment/routes/resources;95..105 source report publication',pair_collector_inc='13..57 supervised results;60..103 joined ownership'),
    raw_snapshot=dict(kind='failure_only_current_kernel_snapshot',bytes=declared,sha256=sha(snapshot.encode()),all_prefix_trace=False,pid_trace_replay=trace_replay,strict_functions_source=pin(RUNTIME/'native_diagnostic.py'),frozen_strict_source=frozen_strict_pin,unchanged_function_ast_equality=unchanged_functions,functions=['_pair_trace','_check_begin_cleanup'],method='Unchanged AST function definitions executed on the exact retained failure snapshot, plus exact schedule/leader-procfs counts. Full _pair_body/check_long_session were not weakened, replaced, or claimed to pass.'),
    failure=dict(round=629,result=-3,meaning='Rust Failure::Deadline',credited=False,rounds=629,launches=1258,trace_bytes_reported_for_credited_prefix=150512132,abort_count=2,pair_stage_stale=True,exact_deadline_branch='Not distinguishable between post-callback and later deadline checks from retained serial; callback-report proves preceding C gate/trace_save succeeded.',kernel_crash_proven=False),
    actual_missing_posthoc_evidence=['all629 original per-round raw trace bytes/full long-trace.spool with provenance','independent replay of all629 raw syscall/CPU/ACK/retirement/token/membership records','successful original LONG terminal completion, final restoration and physical retirement (attempt failed; never retroactively supplied)'],
    decision='Eligible to credit exactly3519690949712ns under the user-authorized cumulative60-minute goal once root closes actual runtime/capture identity. This is a qualified completed-prefix exposure decision, not an uninterrupted LONG pass. A separately admitted continuation must supply at least80309050288ns of successful mixed app work plus required final retirement/cleanup evidence.90s successful work would yield3609690949712ns total (60m9.690949712s). Missing whole-prefix archival replay remains an explicit limitation and does not by itself erase source-bound successful in-producer checks.',
)
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'PREFIX-EVIDENCE-REVIEW.json').write_text(json.dumps(result,indent=2)+'\n')
(OUT/'ROUND-REPORT-REPLAY.json').write_text(json.dumps(rounds,indent=2)+'\n')
print(json.dumps(dict(status=result['status'],replay=result['independent_report_replay'],snapshot_status_counts={k:sum(r['status']==k for r in trace_replay) for k in {r['status'] for r in trace_replay}},snapshot_rounds=sorted({r['round'] for r in trace_replay if r['status']=='ACTUAL_FAILURE_SNAPSHOT_PID_TRACE_PASS'}),artifact=str(OUT/'PREFIX-EVIDENCE-REVIEW.json')),indent=2))
