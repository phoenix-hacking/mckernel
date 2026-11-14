"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib, json, difflib

D = Path(__file__).resolve().parent
E = Path('/home/holden/mckernel/docs/verification/evidence/native235-zombie-reaper-20261023-1/begin-cleanup-correction-1/terminal-control-next-native-preparation-2/v3-restoration-preparation-1/consumer-correction-1')
OLD = Path('/home/holden/mckernel-work/host-preparation/native-second-stop-case-preparation-20261021-1/current053d-normalization-runtime-preparation-1/runtime-source-1/two-generation-namespace-4')
ND = Path('/home/holden/mckernel-work/host-preparation/p-m05-v3-matched-first-restoration-binding-20261023-1/sdk5-successor-1/runtime-first-restoration-1/native_diagnostic.py')
sha = lambda b: hashlib.sha256(b).hexdigest()

def save(name, before, after):
    (D/'original').mkdir(exist_ok=True)
    (D/'original'/name).write_text(before)
    (D/name).write_text(after)
    (D/(name+'.diff')).write_text(''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile=str(OLD/name), tofile=str(D/name))))

base = (OLD/'reboot_workload_capture.py').read_text()
assert sha(base.encode()) == '67b8af6b76e92aeaad831756934dec41dd35906a88e41de3c11972f222aba3ba'
s = base
addition = '''BEGIN_ND = {nd!r}
BEGIN_ND_SHA = '059c40c95b2306265f21bce2a77c49edc7baeb4792e977b189770fc0d21685f1'
BEGIN_AUDIT = [re.compile(PREFIX + module + operation + IDENTITY + suffix) for module, operation, suffix in (
    (r'mcctrl: ', r'application_process=cleanup_requested ', r' intent_errno=-?[0-9]+'),
    (r'ihk_smp_x86_64: IHK-SMP: ', r'application cleanup ACK ', r' token=[0-9]+ errno=-?[0-9]+ abandoned=[01]'),
)]

def begin_diagnostic(manifest):
    if manifest is None or 'cleanup_profile' not in manifest:
        return None
    diagnostic = bound('reboot_workload_begin_nd', BEGIN_ND, BEGIN_ND_SHA)
    diagnostic._validate_cleanup_profile(manifest['cleanup_profile'], manifest['modules'])
    return diagnostic


def workload_view(serial, generation, manifest=None):'''.format(nd=str(ND))
s = s.replace('def workload_view(serial, generation):', addition)
s = s.replace("    markers = ('application_syscall=',", "    begin = begin_diagnostic(manifest)\n    patterns = AUDIT + BEGIN_AUDIT if begin is not None else AUDIT\n    markers = ('application_syscall=',")
s = s.replace("'application retirement', 'application_process=', 'application procfs')", "'application retirement', 'application_process=', 'application procfs')\n    if begin is not None:\n        markers += ('application cleanup ACK',)")
s = s.replace('for kind, pattern in enumerate(AUDIT)', 'for kind, pattern in enumerate(patterns)')
s = s.replace('for kind in range(8)', 'for kind in range(11 if begin is not None else 8)')
s = s.replace('for kind in (2, 3, 4):', 'for kind in ((3, 4) if begin is not None else (2, 3, 4)):')
old = """        need(len(exits) == 1 and scheduled[0][0] < events[3][0][0] < exits[0] <
             events[4][0][0] < terminal[0] < events[2][0][0] and
             all(exits[0] < position for position, _, _ in retirement), 'per-epoch retirement order')"""
new = """        need(len(exits) == 1 and scheduled[0][0] < events[3][0][0] < exits[0] <
             events[4][0][0] < terminal[0] and
             all(exits[0] < position for position, _, _ in retirement), 'per-epoch retirement order')
        if begin is None:
            need(terminal[0] < events[2][0][0], 'per-epoch legacy release order')
        else:
            need(not events[2], 'BEGIN profile cannot substitute a legacy release row')
            epoch_view = ''.join(line for found, line in classified if found is None or found == epoch)
            # Invoke the accepted checker on the exact epoch, with its own exit.
            terminal_index = next(i for i, line in enumerate(epoch_view.splitlines())
                                  if 'application_syscall=delivered ' in line and
                                  re.search(r'os=0 generation=' + epoch + r' pid=' + pid +
                                            r' worker=[0-9]+ delivery=[0-9]+ cpu=0 number=231$', line))
            begin._check_begin_cleanup(epoch_view, 'os=0 generation=' + epoch + ' pid=' + pid,
                                       terminal_index)"""
assert old in s
s = s.replace(old, new)
s = s.replace("diagnostic = bound('reboot_workload_nd', ND, ND_SHA256)", "diagnostic = begin_diagnostic(manifest) or bound('reboot_workload_nd', ND, ND_SHA256)")
s = s.replace('workload_view(serial, 1)', 'workload_view(serial, 1, manifest)')
old = """    for pattern in (r'application retirement ' + prefix + r' token=\d+ errno=0\b',
                    r'application_process=release ' + prefix + r' cleanup_errno=0\b',"""
# Preserve regex backslashes in the original source text.
old = old.replace('\x08', r'\b')
new = """    legacy_lifecycle = () if 'cleanup_profile' in manifest else (
                    r'application retirement ' + prefix + r' token=\d+ errno=0\b',
                    r'application_process=release ' + prefix + r' cleanup_errno=0\b')
    for pattern in (*legacy_lifecycle,""".replace('\x08', r'\b')
assert old in s
s = s.replace(old, new)
s = s.replace('diagnostic._check_syscall_trace(workload_view(serial, 2), prefix)', "diagnostic._check_syscall_trace(workload_view(serial, 2, manifest), prefix, 'cleanup_profile' in manifest)")
save('reboot_workload_capture.py', base, s)

base = (OLD/'second_stop_capture.py').read_text()
assert sha(base.encode()) == 'e7529b22c268e627cce5385428d68b779089514dd0f40761b26a20bf691b20b7'
s = base.replace(str(OLD/'reboot_workload_capture.py'), str(D/'reboot_workload_capture.py')).replace('67b8af6b76e92aeaad831756934dec41dd35906a88e41de3c11972f222aba3ba', sha((D/'reboot_workload_capture.py').read_bytes()))
save('second_stop_capture.py', base, s)
base = (ND.parent/'case_evaluator.py').read_text()
assert sha(base.encode()) == '082b7d74b6604d65075911907a19a12a1a0602ca0e4fdfa1ac59ebae1400ef5c'
s = base.replace(str(OLD/'second_stop_capture.py'), str(D/'second_stop_capture.py')).replace('e7529b22c268e627cce5385428d68b779089514dd0f40761b26a20bf691b20b7', sha((D/'second_stop_capture.py').read_bytes())).replace("first.workload_view(observation['serial'],1)", "first.workload_view(observation['serial'],1,manifest)")
save('case_evaluator.py', base, s)
record = {'scope': __doc__, 'status': 'SOURCE_PREPARED_NO_TEST_EXECUTION_GRANT', 'files': {name: sha((D/name).read_bytes()) for name in ['reboot_workload_capture.py', 'second_stop_capture.py', 'case_evaluator.py']}, 'native059c_unchanged': sha(ND.read_bytes()), 'change': 'Declared validated cleanup_profile only selects accepted intent/realACK/retirement checks for both epochs. Legacy checks unchanged. Original resource/reboot/secondstop counters and strict workload assertions remain.', 'next': 'Full nested consumer controlled fixture and negative lifecycle/resource tests after explicit CPU grant.'}
(D/'SOURCE-PREPARATION.json').write_text(json.dumps(record, indent=2)+'\n')
for q in D.rglob('*'):
    if q.is_file():
        out = E/q.relative_to(D); out.parent.mkdir(parents=True, exist_ok=True); out.write_bytes(q.read_bytes())
print(json.dumps(record))
