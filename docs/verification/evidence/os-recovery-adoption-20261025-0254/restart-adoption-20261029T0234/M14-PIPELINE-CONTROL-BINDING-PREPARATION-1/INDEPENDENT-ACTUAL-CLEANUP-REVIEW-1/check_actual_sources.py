"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Independent exact source checks and TEST_ONLY pure receipt predicates. No guard call.
"""
import ast, copy, hashlib, importlib.util, json
from pathlib import Path

D = Path(__file__).resolve().parent
P = D.parent
B = P.parents[1]
checks = []
def check(value, label):
    if not value: raise AssertionError(label)
    checks.append(label)
def ref(path):
    path = Path(path).resolve(); raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module
def rejected(call, label):
    try: call()
    except (ValueError, KeyError, TypeError): checks.append(label); return
    raise AssertionError('accepted '+label)

bundle = json.loads((P/'ACTUAL-GUARDIAN-CONSTRUCTOR-INPUTS.json').read_text())
values = {}
for key in ('armed','config','packet','bridge'):
    check(ref(bundle[key]['path']) == bundle[key], 'actual input bytes '+key)
    values[key] = json.loads(Path(bundle[key]['path']).read_text())
armed, config, packet, bridge = [values[k] for k in ('armed','config','packet','bridge')]
constructor = load(P/'rebind_actual_M14_guardian_source.py', 'independent_source_constructor')
original = (B/'restart-operation-guard-source-20261028-1/guardian_guard.py').read_text()
guardian_path = P/'new-guardian-source-1/guardian_guard.py'
guardian = guardian_path.read_text()
check(constructor.render(original, bundle, armed, config, packet, bridge) == guardian,
      'actual guardian exactly reproduced by source-only constructor')
for name, sha in packet['private'].items():
    check(ref(Path(bundle['packet']['path']).parent/name)['sha256'] == sha, 'packet private '+name)
for name, sha in packet['canonical'].items():
    check(ref(Path('/home/holden/mckernel/scripts')/name)['sha256'] == sha, 'packet canonical '+name)

# Normalize only declared identity expressions and the two actual receipt literals.
class Normalize(ast.NodeTransformer):
    def visit_Name(self,n):
        return n
    def visit_Constant(self,n):
        if n.value == 'LIVE_CONTINUED_CAMPAIGN_GUARDIAN_20MIN_STEERING_AND_RETAINED_PHONE': n.value='LIVE_SAME_WINDOW_M14_EXCLUSIVE_CONTROLS'
        if n.value == 'original_window_unchanged_sha256': n.value='original_window_sha256'
        return n
old = original.replace("owner.get('ppid') == 2111551", "owner.get('ppid') == GUARDIAN_LAUNCH_PPID").replace("armed['actors']['guardian']['ppid'] == 1311", "armed['actors']['guardian']['ppid'] == GUARDIAN_RECORDED_PPID").replace("expected = dict(INITIAL, guardian=(2111552, '101236067'),\n                    monitor=(2111966, '101243270'), phone=(1894242, '96505809'))", 'expected = EXPECTED_ACTORS').replace('recorded = dict(guardian=1311,monitor=2111963,phone=1311)', 'recorded = AUX_RECORDED_PPIDS')
oldfunc = {n.name:ast.dump(Normalize().visit(n), include_attributes=False) for n in ast.parse(old).body if isinstance(n,ast.FunctionDef)}
newfunc = {n.name:ast.dump(n, include_attributes=False) for n in ast.parse(guardian).body if isinstance(n,ast.FunctionDef)}
check(oldfunc == newfunc, 'every guardian function AST unchanged after exact declared identity and receipt substitutions')
g = load(guardian_path, 'independent_guardian_pure_values_only')
g.validate_control_config(config)
check(g.validate_arm_reference(bundle['armed']) == bundle['armed'], 'actual arm reference and controller config pure predicates')
# This is a synthetic observe function: it proves predicates, never live admission.
fixture = {a['pid']:dict(a,ppid=1311 if n in ('guardian','monitor','phone') else a['ppid']) for n,a in armed['actors'].items()}
fixture[1311]=dict(pid=1311,start='596',ppid=1,comm='systemd',state='S')
g.validate_armed(armed, fixture.get)
check(True,'TEST_ONLY pure actual receipt with allowed auxiliary reparent')
for key, value in [('status','LIVE_CONTINUED_CAMPAIGN_GUARDIAN_20MIN_STEERING_AND_RETAINED_PHONE'),('native_release',True),('thread_id','01a183ec-72e5-7400-8f48-b4efb8725520')]:
    bad=copy.deepcopy(armed);bad[key]=value
    rejected(lambda:g.validate_armed(bad,fixture.get),'TEST_ONLY refusal '+key)
for key in ('monotonic_deadline','boot_deadline'):
    bad=copy.deepcopy(armed);bad['earliest_control_caps'][key]+=1
    rejected(lambda:g.validate_armed(bad,fixture.get),'TEST_ONLY refusal cap increase '+key)
badfixture=copy.deepcopy(fixture);badfixture[armed['actors']['monitor']['pid']]['ppid']=2300390
rejected(lambda:g.validate_armed(armed,badfixture.get),'TEST_ONLY refusal auxiliary still under launch shell')

oldroot=B/'CURRENT118-normal-retirement-preparation-1/compatibility-source-1'
oldb=json.loads((oldroot/'BINDINGS.json').read_text())
newroot=P/'current-guardian-source-1'
newb=json.loads((newroot/'BINDINGS.json').read_text())
check({k for k in oldb if oldb[k]!=newb[k]} == {'guardian','output_root_parent','cutoffs'} and set(oldb)==set(newb),'cleanup binding delta exactly guardian/output/cutoffs')
check(newb['guardian']==ref(guardian_path) and newb['output_root_parent']==str(newroot),'exact actual guardian and output parent')
cutoff=load(P/'cutoff_bindings.py','independent_cutoff_values_only')
clock=json.loads((constructor.NEWSC/'bootstrap/initial-watch-clock.json').read_text())
check(newb['cutoffs']==cutoff.bind_cutoffs(oldb['cutoffs'],armed,clock)==[1793253600.0,1035703.5689321246,1051041.695980609],'exact componentwise earliest actual/old/bootstrap caps')
oldexec=(oldroot/'retire_exact_current118_stopped_container.py').read_text()
newexec=(newroot/'retire_exact_current118_stopped_container.py').read_text()
check(newexec == oldexec.replace(ref(oldroot/'BINDINGS.json')['sha256'],ref(newroot/'BINDINGS.json')['sha256']), 'executor sole BINDINGS_SHA replacement')
oldfiles=json.loads((oldroot/'RUNTIME-FILES.json').read_text()); files=json.loads((newroot/'RUNTIME-FILES.json').read_text())
check(set(files)==set(oldfiles) and len(files)==12,'exact runtime12 roles')
check({k for k in files if files[k]!=oldfiles[k]}=={'executor','bindings','guardian'},'exact runtime12 delta')
for key,row in files.items(): check(ref(row['path'])==row,'runtime byte authentication '+key)
result=dict(scope=constructor.__doc__.splitlines()[0],status='PASS_EXACT_SOURCE_AND_TEST_ONLY_PURE_PREDICATES',checks=checks,check_count=len(checks),files=files,bindings=ref(newroot/'BINDINGS.json'),actual_inputs=ref(P/'ACTUAL-GUARDIAN-CONSTRUCTOR-INPUTS.json'),guard_calls=0,live_observations=0,commands_started=0,current_free=False,native_custody_released=False,execution_authority=None)
(D/'CHECKS.ACTUAL.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(status=result['status'],checks=len(checks),result=ref(D/'CHECKS.ACTUAL.json'))))
