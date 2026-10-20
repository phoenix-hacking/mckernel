"""Single captured no-root child: real saved evidence, then pure normalization."""
from pathlib import Path
import hashlib,importlib.util,json
D=Path(__file__).resolve().parent

def load(name,row):
    raw=Path(row['path']).read_bytes()
    assert len(raw)==row['size'] and hashlib.sha256(raw).hexdigest()==row['sha256']
    assert Path(row['path']).stat().st_mode==row['mode']
    spec=importlib.util.spec_from_file_location(name,row['path'])
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result

def main():
    cfg=json.loads((D/'ORDINARY-CHAIN-INPUTS.json').read_bytes())
    saved=D/'ordinary-check-1'
    assert not saved.exists();saved.mkdir(mode=0o700)
    load('exact_saved_current_physical_checks',cfg['checks']).main()
    load('exact_current_exit7_normalizer',cfg['normalizer']).main()
    result=dict(status='PASS_SAVED_PHYSICAL_CHECKS_AND_NORMALIZATION_ONLY',witnesses=5,root_operations=0,guest_runs=0,runtime_release=None)
    with (D/'ORDINARY-CHAIN-RESULT.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps(result))

if __name__=='__main__':main()
