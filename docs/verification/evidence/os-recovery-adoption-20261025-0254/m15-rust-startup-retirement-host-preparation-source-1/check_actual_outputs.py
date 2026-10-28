"""Functional OS only; no security testing. Qualify retained full HOST outputs, never run."""
import argparse,hashlib,importlib.util,json,re
from pathlib import Path
D=Path(__file__).resolve().parent

def need(ok,why):
 if not ok:raise ValueError(why)
def check_tests(raw,names):
 text=raw.decode('utf-8');lines=text.splitlines();count=len(names)
 need(sum(line==f'running {count} tests' for line in lines)==1,'exact finite harness count')
 actual=[]
 for line in lines:
  m=re.fullmatch(r'test ([A-Za-z0-9_:]+) \.\.\. ok',line)
  if m:actual.append(m.group(1));continue
  if not line or line==f'running {count} tests':continue
  need(re.fullmatch(r'test result: ok\. '+str(count)+r' passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in [0-9]+(?:\.[0-9]+)?s',line) is not None,'unexpected test output retained as failure')
 need(sorted(actual)==sorted(names) and len(set(actual))==count,'exact named controls, nofilter/ignore')
 need(sum(line.startswith('test result:') for line in lines)==1,'one full harness result')
 return True

def check_readelf(raw):
 text=raw.decode('utf-8');need(re.search(r'Class:\s+ELF64\b',text) and re.search(r'Machine:\s+Advanced Micro Devices X86-64\b',text) and re.search(r'Type:\s+EXEC\b',text),'actual expected ELF64 x86-64 ET_EXEC')
 need(not re.search(r'^\s*INTERP\s',text,re.M) and '(NEEDED)' not in text,'static executable noINTERP/NEEDED');return True

def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--bound-recipe',required=True);a.add_argument('--bound-recipe-sha256',required=True);a.add_argument('--capture-root',required=True);args=a.parse_args();path=Path(args.bound_recipe);raw=path.read_bytes();need(hashlib.sha256(raw).hexdigest()==args.bound_recipe_sha256,'exact boundrecipe');p=json.loads(raw);root=Path(args.capture_root)
 for i in range(5):need((root/('step'+str(i))/'stderr').read_bytes()==b'','all compiler/test/readelf diagnostics retained and empty')
 check_tests((root/'step2/stdout').read_bytes(),p['expected_test_names']);check_readelf((root/'step4/stdout').read_bytes())
 overlay=p['retained_overlay_source'];need(hashlib.sha256(Path(overlay['path']).read_bytes()).hexdigest()==overlay['sha256'],'retained ELFvalidator source');spec=importlib.util.spec_from_file_location('retained_collector_ELF_validator',overlay['path']);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m._check_collector(Path(p['production_output']).read_bytes())
 print(json.dumps(dict(status='PASS_FINITE_HOST_OUTPUTS_AND_STATIC_ELF_ONLY',actual_count=len(p['expected_test_names']),actual_collector_sha256=hashlib.sha256(Path(p['production_output']).read_bytes()).hexdigest(),native_acceptance=False,runtime_authority=None)))
if __name__=='__main__':main()
