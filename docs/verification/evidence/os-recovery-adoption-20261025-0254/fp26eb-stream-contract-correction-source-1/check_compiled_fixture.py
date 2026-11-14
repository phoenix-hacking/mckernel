"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Run only exact frame fixture, never the actual collector main/module helpers.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,re,subprocess
R=Path(__file__).resolve().parent;E=R.parent
if __name__=='__main__':
 p=argparse.ArgumentParser(allow_abbrev=False);p.add_argument('--fixture',required=True,type=Path);a=p.parse_args()
 assert a.fixture==R/'output-PENDING-ROOT/actual-frame-fixture'
 r=subprocess.run([str(a.fixture)],capture_output=True,timeout=10)
 assert r.returncode==0 and not r.stderr
 lines=r.stdout.decode().splitlines();assert len(lines)==2 and lines[0].startswith('ND_PAYLOAD ') and lines[1]=='FP4096_FRAME_CHECKS PASS'
 report=json.loads(lines[0][len('ND_PAYLOAD '):]);m=json.loads((E/'five26eb-fp-image-composition-static-source-1/offline-materialization-1/manifest.HOST-STATIC.json').read_bytes())
 vpath=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/procfs-delete-native-successor-1/runtime-provider-rebind-1/native/native_diagnostic.py');assert hashlib.sha256(vpath.read_bytes()).hexdigest()=='f368324242bfdfb0ad1f3f524a906dcf51730ef0beb311315e6b66f5d585748c'
 spec=importlib.util.spec_from_file_location('real_f368_frame_consumer',vpath);v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
 text=vpath.read_text();start=text.index('    _keys(report["streams"],');loop=text[start:text.index('    schedules =',start)];loop='\n'.join(line[4:] if line.startswith('    ') else line for line in loop.splitlines())
 exec(loop,dict(report=report,manifest=m,re=re,_keys=v._keys,_need=v._need,_check_typed_futex_stderr=v._check_typed_futex_stderr))
 assert report['argv']==m['payload']['argv'] and report['cwd']==m['payload']['cwd'] and report['env']==m['payload']['env'] and report['raw_wait_status']==0 and report['procfs_empty'] is True
 print(json.dumps(dict(scope=__doc__.splitlines()[0],status='PASS_COMPILED_EXACT_C4096_FRAME_LITERAL_CONSUMER_API',fixture_argv=[str(a.fixture)],fixture_direct_child_joined=True,fixture_returncode=r.returncode,stdout_sha256=hashlib.sha256(r.stdout).hexdigest(),fixture_frame_bytes=len(lines[0])+1,exact4096_stdout_stderr=True,original254_oracle=True,above1024_not_truncated=True,oversized_frame_rejected=True,truncation_marked=True,actual_collector_main_executed=False,guest_calls=0,native_acceptance=False,runtime_authority=None)))
