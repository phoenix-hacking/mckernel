"""Read-only retained26 reconstruction; no compiler or daemon execution.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
from pathlib import Path
import hashlib,json

def validate(root,cases_path,manifest_path,prefix_root=Path('/retained-prefix'),mock_root=Path('/retained-mock-build')):
    from pinned_helpers import helper
    prefix=helper('prefix');audit=helper('audit');rustio=helper('rustio')
    need=prefix.need;root=Path(root);manifest=json.loads(Path(manifest_path).read_bytes())
    prefix.verify_files(root,manifest['current_files'])
    prep_path=Path(manifest['source30_preparation']['path']);raw=prep_path.read_bytes()
    need(hashlib.sha256(raw).hexdigest()==manifest['source30_preparation']['sha256'],'source30 preparation changed')
    prep=json.loads(raw);prefix.verify_files(prefix_root,prep['retained_prefix_files']);prefix.verify_files(mock_root,prep['retained_mock_files'])
    cases=json.loads(Path(cases_path).read_bytes());results=prefix.load(prefix_root,cases)
    prefix.join(root,'Rust-daemon-build',0)
    command=json.loads((root/'Rust-daemon-build.command.json').read_bytes());recorded=json.loads((root/'Rust-daemon-build/command.json').read_bytes())
    need(recorded['argv']==command['argv'] and recorded['cwd']==command['cwd'],'actual compiler command differs')
    baseline=json.loads((Path(mock_root)/'Rust-daemon-build.command.json').read_bytes())['argv']
    rustio.validate_receipt(json.loads((root/'Rust-output-preflight.ACTUAL.json').read_bytes()),prep['container_output'],root,command,8,baseline)
    need((root/'mock.o').read_bytes()==(Path(mock_root)/'mock.o').read_bytes(),'retained observer object differs')
    need((root/'ring-C').read_bytes()==(Path(prefix_root)/'ring-C').read_bytes(),'retained C helper differs')
    expected={'Rust-daemon-build'}|{'%02d-Rust'%i for i in range(8,26)}
    need({p.parent.name for p in root.glob('*/whole-join.json')}==expected,'exact successful compiler plus18 cases required')
    for i,case in enumerate(cases[8:],8):
        label='%02d-Rust'%i;p=prefix.join(root,label,case['status'])
        proof=audit.validate((root/(label+'.joined-tasks.ndjson')).read_bytes(),p['pid'],p['start'])
        need(proof==json.loads((root/(label+'.joined-tasks.proof.json')).read_bytes()),'retained joined-task proof differs')
        m=json.loads((root/(label+'.resources.json')).read_bytes());trace=(root/(label+'.trace')).read_text().splitlines()
        ok=p['returncode']==case['status'] and prefix.closed(m,case['expected_unreleased_leases'])
        if 'expected_gets'in case:ok=ok and m['get']==case['expected_gets']
        if 'expected_syslog_messages'in case:ok=ok and m['syslog_messages']==case['expected_syslog_messages']
        if case['status']==0 and case['expect_mon']:ok=ok and m['detect']>=1
        if case['name']=='release-failure-not-claimed-restored':ok=ok and m['release_attempts']==1 and m['released']==0
        if case['name']=='configured-facility':ok=ok and any('facility=144'in line for line in trace)
        if 'expected_event_read_fault' in case:ok=ok and any(('injected '+case['expected_event_read_fault']) in line for line in trace)
        need(ok,'retained current oracle failed: '+case['name'])
        results.append(dict(name=case['name'],passed_contract=True,Rust_status=p['returncode'],Rust_resources=m,reference=None,restoration_claim=False if case['expected_unreleased_leases'] else 'host mock only, no native credit',evidence_origin='RETAINED_ACTUAL_1f97_SUFFIX_8_25'))
    return results
