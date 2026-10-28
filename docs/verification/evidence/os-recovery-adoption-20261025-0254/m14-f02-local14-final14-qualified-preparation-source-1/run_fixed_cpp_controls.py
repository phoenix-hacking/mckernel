"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exactly eight proposed CPP checks; no retries, shell or generic control generation.
"""
import hashlib,json,subprocess,sys
from pathlib import Path

def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
 plan=Path(sys.argv[1]);x=json.loads(plan.read_text());out=plan.parent/'HOST-output-proposed-1'
 assert len(x['commands'])==8 and x['runtime_authority'] is None
 records=[]
 for row in x['commands']:
  stdout=out/(row['name']+'.stdout');stderr=out/(row['name']+'.stderr')
  with stdout.open('xb') as a,stderr.open('xb') as b:
   child=subprocess.Popen(row['argv'],stdout=a,stderr=b);rc=child.wait(timeout=60)
  error=stderr.read_text();target=Path(row['argv'][-1])
  record=dict(name=row['name'],argv=row['argv'],returncode=rc,positive_wait=True,streams_closed=True,stdout=ref(stdout),stderr=ref(stderr),preprocessed_output=ref(target) if target.exists() else None)
  records.append(record)
  (out/'CPP-CONTROL-PREFIX.json').write_text(json.dumps(dict(scope=x['scope'],records=records),indent=2)+'\n')
  if row['expected_reject']:assert rc!=0 and row['diagnostic'] in error,(row['name'],rc,error)
  else:assert rc==0 and not error and target.is_file(),(row['name'],rc,error)
 (out/'CPP-CONTROL-RESULT.json').write_text(json.dumps(dict(scope=x['scope'],status='PASS_FIXED_SELECTED_REJECTION_AND_OPTIONOFF_CPP_ONLY',records=records,nondefault_object_link_native_acceptance=False),indent=2)+'\n')
 print('F02 CPP selected rejection/optionOFF preprocessing PASS')
if __name__=='__main__':main()
