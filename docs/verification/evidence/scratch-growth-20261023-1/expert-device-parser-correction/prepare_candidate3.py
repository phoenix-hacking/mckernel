"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast,difflib,hashlib,json,os
D=Path(__file__).resolve().parent;assert os.sched_getaffinity(0)=={7};OLD=D.parent/'maintenance-source'
a=(OLD/'grow_scratch.py').read_bytes();assert hashlib.sha256(a).hexdigest()=='932f92710d7fb5dfd7bc4e66eedb9684059dd9b328bad7ae3a7c3edf872b3a84'
(D/'candidate2.grow_scratch.py').write_bytes(a);s=a.decode()
fn="""def parse_major_minor(value):
    require(type(value) is str and len(value) <= 64, 'typed bounded major:minor required')
    matched = re.fullmatch(r'[ \\t]*([0-9]+):([0-9]+)[ \\t]*', value, re.ASCII)
    require(matched is not None, 'ASCII decimal major:minor required')
    return int(matched.group(1), 10), int(matched.group(2), 10)


"""
b=s.replace('def snapshot(run, sizes):',fn+'def snapshot(run, sizes):',1)
x="loop['maj:min'] == '%d:%d' % (os.major(devmeta.st_rdev), os.minor(devmeta.st_rdev))";y="loop['back-maj:min'] == '%d:%d' % (os.major(meta.st_dev), os.minor(meta.st_dev))"
assert b.count(x)==b.count(y)==1
b=b.replace(x,"parse_major_minor(loop['maj:min']) == (os.major(devmeta.st_rdev), os.minor(devmeta.st_rdev))").replace(y,"parse_major_minor(loop['back-maj:min']) == (os.major(meta.st_dev), os.minor(meta.st_dev))")
(D/'grow_scratch.py').write_text(b);ast.parse(b)
(D/'EXPERT-PRESCRIBED-ONLY.diff').write_text(''.join(difflib.unified_diff(s.splitlines(True),b.splitlines(True),fromfile='candidate2/grow_scratch.py',tofile='candidate3/grow_scratch.py')))
(D/'test_grow_scratch.py').write_bytes((OLD/'test_grow_scratch.py').read_bytes())
P=Path('/home/holden/mckernel-work/host-preparation/scratch-growth-20261023-1/readonly-qualification-attempt-1/stdout');r=P.read_bytes();assert hashlib.sha256(r).hexdigest()=='89879ebbf68f96b29bab8d6d0df89262fb3d8f13fcaa34e8aba5b21dfc8cd98e';(D/'FAILED-READONLY-REPORT1.raw.json').write_bytes(r)
report=json.loads(r);cmd=next(x for x in report['commands']if x['argv'][0]=='/usr/sbin/losetup');raw=cmd['stdout'].encode();assert len(raw)==243 and hashlib.sha256(raw).hexdigest()=='85e8255ca5de124d3c02bd341ea7bc1885220bca5300e7ca6809574c16ec6283';(D/'ACTUAL-LOSETUP1.raw.json').write_bytes(raw)
print(json.dumps(dict(candidate3_sha256=hashlib.sha256(b.encode()).hexdigest(),bytes=len(b.encode()),rawfixture_bytes=len(raw),expert_prescribed_changes='new typed ASCII parser + two tuple comparisons only',root_operations=0)))
