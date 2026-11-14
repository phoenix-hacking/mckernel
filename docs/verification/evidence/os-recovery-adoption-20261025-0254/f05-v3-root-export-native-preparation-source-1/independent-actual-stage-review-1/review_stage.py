#!/usr/bin/env python3
"""Offline functional OS artifact review; no execution of staged programs."""
import ast
import datetime
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import stat

P = Path(__file__).resolve().parent.parent
D = Path(__file__).resolve().parent
E = P.parent
seen = {}

def digest(b):
    return hashlib.sha256(b).hexdigest()

def read(p):
    p = Path(p)
    assert p.is_absolute() and p.resolve(strict=True) == p
    a = p.lstat()
    assert stat.S_ISREG(a.st_mode) and a.st_nlink == 1
    b = p.read_bytes()
    z = p.lstat()
    assert all(getattr(a,k) == getattr(z,k) for k in ('st_dev','st_ino','st_mode','st_nlink','st_uid','st_gid','st_size','st_mtime_ns','st_ctime_ns')) and len(b) == a.st_size
    seen[str(p)] = dict(path=str(p), bytes=len(b), sha256=digest(b))
    return b

def load(p):
    return json.loads(read(p))

def checkref(r):
    b = read(r['path'])
    assert len(b) == r.get('bytes', r.get('size')) and digest(b) == r['sha256']
    if 'mode' in r:
        mode = stat.S_IFREG | int(r['mode'],8) if isinstance(r['mode'],str) else r['mode']
        assert Path(r['path']).lstat().st_mode == mode
    return b

def inflate(b):
    with gzip.GzipFile(fileobj=io.BytesIO(b)) as f:
        out = f.read(80 * 1024 * 1024 + 1)
        assert len(out) <= 80 * 1024 * 1024 and f.read(1) == b''
    return out

def parse(b):
    """Independent complete newc parser, without extracting archive paths."""
    out, pos, archive, opened, trailers = [], 0, 0, False, []
    while pos < len(b):
        if not opened and b[pos] == 0:
            while pos < len(b) and b[pos] == 0:
                pos += 1
            if pos == len(b):
                break
            assert pos % 4 == 0
        h = b[pos:pos+110]
        assert len(h) == 110 and h[:6] in (b'070701', b'070702')
        assert re.fullmatch(b'[0-9a-fA-F]{104}', h[6:])
        v = [int(h[n:n+8], 16) for n in range(6, 110, 8)]
        ino, mode, uid, gid, nl, mt, size, dm, dn, rm, rn, ns, cs = v
        assert 2 <= ns <= 4096
        namebytes = b[pos+110:pos+110+ns]
        assert len(namebytes) == ns and namebytes[-1:] == b'\0' and b'\0' not in namebytes[:-1]
        name = namebytes[:-1].decode('utf-8')
        ds = (pos+110+ns+3) & ~3
        end = (ds+size+3) & ~3
        assert end <= len(b) and not any(b[pos+110+ns:ds]) and not any(b[ds+size:end])
        data = b[ds:ds+size]
        assert cs == (0 if h[:6] == b'070701' else sum(data) & 0xffffffff)
        if name == 'TRAILER!!!':
            assert [mode,uid,gid,nl,mt,size,dm,dn,rm,rn] == [0,0,0,1,0,0,0,0,0,0]
            trailers.append(pos)
            opened = False
            archive += 1
        else:
            name = name[2:] if name.startswith('./') else name
            assert name and not name.startswith('/') and '\\' not in name
            assert name == '.' or all(x not in ('', '.', '..') for x in name.split('/'))
            typ = stat.S_IFMT(mode)
            assert mode & ~0xffff == 0 and typ in (stat.S_IFREG,stat.S_IFDIR,stat.S_IFLNK,stat.S_IFCHR,stat.S_IFBLK,stat.S_IFIFO) and nl > 0
            assert typ in (stat.S_IFREG,stat.S_IFLNK) or size == 0
            assert typ in (stat.S_IFCHR,stat.S_IFBLK) or (rm == rn == 0)
            assert typ != stat.S_IFLNK or (data and b'\0' not in data)
            assert name != '.' or typ == stat.S_IFDIR
            # This actual finite archive has no regular-file hardlinks.
            assert typ != stat.S_IFREG or nl == 1
            out.append(dict(name=name,mode=mode,uid=uid,gid=gid,nlink=nl,mtime=mt,size=size,
                            sha256=digest(data),rdevmajor=rm,rdevminor=rn,data=data,archive=archive))
            opened = True
        pos = end
    assert trailers and not opened
    return out, trailers

def replay(records):
    final = {}
    for r in records:
        name = r['name']
        if name in final:
            assert name in ('apps','case','case/work','init','apps/app','bin/mcexec')
            assert stat.S_IFMT(final[name]['mode']) == stat.S_IFMT(r['mode'])
        pieces = name.split('/')
        for n in range(1,len(pieces)):
            assert stat.S_ISDIR(final['/'.join(pieces[:n])]['mode'])
        final[name] = r
    return final

def metadata(final):
    fields = ('mode','uid','gid','nlink','mtime','size','sha256','rdevmajor','rdevminor')
    return {k:{f:r[f] for f in fields} for k,r in sorted(final.items())}

def literals(path):
    tree = ast.parse(read(path))
    result = {}
    for n in tree.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0],ast.Name):
            try:
                result[n.targets[0].id] = ast.literal_eval(n.value)
            except (ValueError,TypeError):
                pass
    return result

manifest = load(P/'ROOT-ACTUAL-V3-MANIFEST.BASE-JOIN-CORRECTED.json')
owner = load(P/'ROOT-ACTUAL-OWNER-MANIFEST-QUALIFICATION.json')
assert digest(checkref(owner['manifest'])) == digest(checkref(owner['repository_manifest']))
assert owner['status'] == 'PASS_ACTUAL_V3_LITERAL_OWNER_BOUND_MANIFEST' and owner['runtime_authority'] is None
adopt = load(P/'ROOT-ACTUAL-RUNTIME-SOURCE-ADOPTION.json')
for pair in adopt['files']:
    assert checkref(pair['adopted']) == checkref(pair['source'])
assert adopt['runtime_authority'] is None and adopt['native_acceptance'] is False
source_review = load(P/'independent-context-overlay-source-review-1/REVIEW.json')
assert source_review['decision'].startswith('PASS')
receipt = load(P/'root-overlay-materialization-1/overlay.json')
result = load(P/'root-overlay-materialization-1/ROOT-ACTUAL-COMPOSITION-RESULT.json')
checkref(result['overlay_receipt'])
join = json.loads(checkref(result['join']))
assert join['returncode'] == 0 and join['direct_child_joined'] and join['group_absent'] and join['closed_streams']
assert join['remaining_group_members'] == join['unexpected_group_members'] == []
assert join['timed_out'] is False and join['error'] is None and join['retirement_error'] is None
assert checkref(join['captures']['stdout']) == read(P/'root-overlay-materialization-1/overlay.json')
assert checkref(join['captures']['stderr']) == b''
raw = checkref(manifest['staging']['derived_initramfs'])
assert digest(raw) == receipt['output_sha256'] == 'c4a78b897f3a7d3cdb99229b275e37f6392387b25d6775a3f2569b77ac396ad7'
for f,v in receipt['output_identity'].items():
    assert getattr(Path(manifest['staging']['derived_initramfs']['path']).lstat(),f) == v
base = checkref(manifest['staging']['base_initramfs'])
assert manifest['staging']['base_initramfs'] == manifest['artifacts']['initramfs'] == manifest['artifacts']['root_base']
basecpio, full = inflate(base), inflate(raw)
assert len(basecpio) == receipt['base_cpio_size'] == 44428264 and digest(basecpio) == receipt['base_cpio_sha256']
assert full[:len(basecpio)] == basecpio
suffix = full[len(basecpio):]
assert digest(suffix) == receipt['overlay_sha256']
base_records, bt = parse(basecpio)
records, ft = parse(full)
over, ot = parse(suffix)
assert [x['name'] for x in over] == ['apps','case','case/work','init','apps/app','bin/mcexec']
assert len(ot) == 1 and len(ft) == len(bt) + 1
for n,r in enumerate(over):
    assert r['archive'] == 0 and r['uid'] == r['gid'] == r['mtime'] == 0
    assert r['mode'] == (0o40755 if n < 3 else 0o100755)
    assert r['nlink'] == (2 if n < 3 else 1)
assert metadata(replay(records)) == receipt['final_map'] == metadata(replay(base_records+over))
final = replay(records)
expected = {'init':manifest['staging']['collector'], 'apps/app':manifest['artifacts']['payload'],
 'bin/mcexec':manifest['artifacts']['mcexec'],'images/mckernel.img':manifest['artifacts']['mckernel_image'],
 'bin/native-boot':manifest['artifacts']['native_boot'],'lib64/libc.so.6':manifest['artifacts']['libc'],
 'lib64/ld-linux-x86-64.so.2':manifest['artifacts']['loader']}
expected.update({'modules/'+Path(x['path']).name:x for x in manifest['modules']})
for name,ref in expected.items():
    assert final[name]['sha256'] == ref['sha256'] and final[name]['size'] == ref['size']
    assert final[name]['mode'] == (0o100755 if name in ('init','apps/app') else ref['mode'])
for name,key in [('init','collector'),('apps/app','payload'),('bin/mcexec','mcexec')]:
    assert final[name]['data'] == checkref(expected[name])
for key,row in receipt['sources'].items():
    path = Path(row['path'])
    for f,v in row['identity'].items():
        assert getattr(path.lstat(),f) == v
    assert row['sha256'] == digest(read(path))
ev = literals(P/'root-adopted-native-runtime-1/native_diagnostic.py')
assert ev['F05_CASE'] == manifest['case_id'] == 'M14-05-05-owned-processvm-v3-causal-204B'
binding = ev['F05_SUPERVISOR_BINDING']
assert binding['collector'] == manifest['staging']['collector']
assert binding['collector']['sha256'] == '908f147ef0a61959becc20820d6e889aaf5eb4418adda0c99f13b3c3e6cf72a1'
for key in ('root_adoption','binding_facts','source_ready','source_qualification','host_qualification','interface'):
    checkref(binding[key])
interface = json.loads(checkref(binding['interface']))
assert binding['native_qualification'] is None and binding['runtime_release'] is None
assert manifest['payload']['argv'] == interface['payload_argv'] == ['/bin/mcexec','-t','1','0','/apps/app']
assert manifest['payload']['env'] == interface['payload_env'] == {'PATH':'/usr/bin:/bin','COKERNEL_PATH':'/apps'}
assert manifest['payload']['cwd'] == interface['payload_cwd'] == '/case/work'
assert manifest['payload']['stdout_limit_bytes'] == manifest['payload']['stderr_limit_bytes'] == 1024
assert manifest['cleanup_profile']['case_binding']['payload_timeout_ms'] == 10000
assert manifest['cleanup_profile']['child_trace_cases'] == [manifest['case_id']]
assert manifest['cleanup_profile']['modules'] == manifest['modules']
assert ev['F05_BINDING']['payload'] == manifest['artifacts']['payload']
assert manifest['profile'] == dict(memory_mib=8192,name='native-diagnostic-4vcpu-8192mib',numa_nodes=2,vcpus=4)
host = json.loads(checkref(binding['host_qualification']))
launcher_proof = json.loads(checkref(source_review['launcher_source_object_config_proof']))
assert all(launcher_proof['selected_binary'][k] == manifest['artifacts']['mcexec'][k] for k in ('path','sha256','size','mode'))
preserved = [P/'ROOT-OWNER-REPO-MANIFEST-FIRST-REFUSAL.json',P/'ROOT-OWNER-BASE-JOIN-FIRST-REFUSAL.json']
for p in preserved:
    assert load(p)['workload_started'] is False
mapping = D/'OBSERVED-FINAL-MAP.json'
mapping.write_text(json.dumps(metadata(final),indent=2,sort_keys=True)+'\n')
read(mapping)
review = dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
 independent=True, reviewer='/root/custody_release_review', at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 decision='PASS_EXACT_ACTUAL_F05_V3_STAGE_SOURCE_AND_ARTIFACT_ONLY',
 case_id=manifest['case_id'], archive=manifest['staging']['derived_initramfs'],
 manifest=owner['manifest'], repository_manifest=owner['repository_manifest'],
 overlay_receipt=seen[str(P/'root-overlay-materialization-1/overlay.json')],
 archive_validation=dict(full_gzip_valid=True,uncompressed_bytes=len(full),base_cpio_bytes=len(basecpio),
  base_prefix_byte_identical=True,base_records=len(base_records),full_records=len(records),
  final_members=len(final),base_trailers=len(bt),full_trailers=len(ft),suffix_bytes=len(suffix),
  suffix_sha256=digest(suffix),suffix_exact_six_members=[r['name'] for r in over],
  complete_final_map_match=True,regular_hardlinks_present=False,member_sources=expected),
 joins=join,
 collector_case_eligibility=dict(eligible_case_only=manifest['case_id'],collector_case_argv=[],
  activation='rdinit=/init; no case arguments. Compiled selected Rust main uses fixed payload argv/env/cwd and does not dispatch other cases.',
  qualification='Exact actual908f new Rust supervisor, source81bb/4485 and actual36-control HOST9b54; no c020 identity reuse.',
  interface=binding['interface'],payload_argv=manifest['payload']['argv'],payload_env=manifest['payload']['env'],
  payload_cwd=manifest['payload']['cwd'],limits=interface['limits'],source_and_config_proof=source_review['launcher_source_object_config_proof']),
 source_and_manifest=dict(root_owner_status=owner['status'],owner=owner['owner'],evaluator=owner['evaluator'],
  reused_independent_source_review=adopt['independent_review'],actual_five_literal_adoptions_equal=True,
  old139_plus4_pins='Reuse independently accepted source5411 and actual Root normal owner API73456; no unchanged139 rehash or owner replay.',
  supervisor_binding=binding,preserved_metadata_refusals=[seen[str(p)] for p in preserved]),
 conclusions=[
  'Independent full gzip/newc read validates complete archive and all members, unchanged complete44428264B base prefix, exact six-member suffix and complete final map; no archive extraction.',
  'Final init5725328B=908f, app5627368B=125c, launcherdca, image60e62 and exact daced/887dc/57546 modules match manifest and preserved base. Init/app archive0755 is explicit original composition contract; source collector100700 and payload100555 retained.',
  'Only matching fixed v3 case is eligible. Exact compiled-source fixed payload argv, two env, cwd,10000ms and1024-byte streams bind actualHOST/artifact qualification. Native PID1 behavior, kmsg causality, old235/227 and complete native retirement are unproven.',
  'Working launcherdca025 remains mixed C with selected source/object/config c7fe proof; static stage acceptance does not claim M15 retirement.',
  'Original strict235/227/v2 failure and both metadata refusals remain preserved. No new quotas, oracle changes, native prerequisite or circular prior-native acceptance requirement.'],
 runtime_authority=None,source_authority=None,capability=None,runtime_release=None,native_acceptance=False,
 actual_stage_acceptance=True,actual_native_qualification=None,
 actions=dict(offline_reads_archive_decode_hash_AST_only=True,compiler_tests_workload_queries_guard_cleanup_Git=0,subagents=0),
 references=list(seen.values()))
out = D/'REVIEW.json'
out.write_text(json.dumps(review,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(review=str(out),bytes=out.stat().st_size,sha256=digest(out.read_bytes()),
                     archive_members=len(final),full_records=len(records),uncompressed_bytes=len(full))))
