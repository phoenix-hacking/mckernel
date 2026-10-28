"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Independent pure source/recipe verification. No compiler, producer or runtime calls.
"""
from pathlib import Path
import datetime, hashlib, importlib.util, io, json, re, resource, sys, unittest
resource.setrlimit(resource.RLIMIT_AS, (2*1024**3, 2*1024**3))
HERE = Path(__file__).resolve().parent
PACKET = HERE.parent / "m14-next118-composition-restart-20261028-1"
def digest(raw): return hashlib.sha256(raw).hexdigest()
def ref(p):
 p=Path(p); raw=p.read_bytes()
 return dict(path=str(p),bytes=len(raw),sha256=digest(raw))
checked=[]
def check_ref(row):
 assert ref(row["path"]) == row, row["path"]
 checked.append(row)
 return Path(row["path"]).read_bytes()
def refs(obj):
 if isinstance(obj,dict):
  if set(obj)=={"path","bytes","sha256"}: check_ref(obj)
  else:
   for value in obj.values(): refs(value)
 elif isinstance(obj,list):
  for value in obj: refs(value)
def load(n): return json.loads((PACKET/n).read_bytes())
ready=load("SOURCE-READY.json")
assert ref(PACKET/"SOURCE-READY.json")["sha256"]=="2271a56ae9668b4a3fb7e41770cd5260fce42c270b80e5f03fa264af468ee421"
refs(ready)
files=load("FILES.json"); refs(files)
inputs=load("INPUTS.json"); refs(inputs)
# A separate line-numbered unified patch applier, independent of composer search.
def apply_unified(before,patch):
 src=before.splitlines(True); lines=patch.splitlines(True); out=[]; cursor=0; index=2
 while index<len(lines):
  m=re.fullmatch(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@[^\n]*\n",lines[index]); assert m
  start=int(m[1])-1; old_n=int(m[2] or 1); new_n=int(m[4] or 1)
  assert start>=cursor
  out.extend(src[cursor:start]); cursor=start; index+=1; old=[]; new=[]
  while index<len(lines) and not lines[index].startswith("@@ "):
   line=lines[index]; assert line[:1] in " +-"
   if line[0] in " -": old.append(line[1:])
   if line[0] in " +": new.append(line[1:])
   index+=1
  assert len(old)==old_n and len(new)==new_n
  assert src[cursor:cursor+len(old)]==old
  out.extend(new);cursor+=len(old)
 out.extend(src[cursor:]);return "".join(out)
maps={n:load("SOURCE-MAP-FROM"+str(n)+".json") for n in [116,117]}
for n,mapping in maps.items():
 refs(mapping); assert mapping["baseline"]==n
 rows=mapping["writes"]; assert len(rows)==(9 if n==116 else 8)
 assert len({r["relative"] for r in rows})==len(rows)
 for row in rows:
  post=check_ref(row["postimage"]).decode()
  if row["preimage"]:
   assert row["preimage_requirement"]=="EXACT_BYTE_REF"
   assert apply_unified(check_ref(row["preimage"]).decode(),check_ref(row["patch"]).decode())==post
  else:
   assert row["preimage_requirement"]=="PATH_ABSENT" and row["patch"] is None
assert {r["relative"]:r["postimage"] for r in maps[117]["writes"]}.items() <= {r["relative"]:r["postimage"] for r in maps[116]["writes"]}.items()
recipe=load("MINIMAL-FOUR-COMMAND-CONTINUATION.NOT-GRANTED.json"); refs(recipe)
old=json.loads(check_ref(inputs["recipe117"]))
commands=recipe["ordered_commands"]; previous=old["ordered_commands"]
assert len(commands)==4
for index,row in enumerate(commands):
 assert row["cwd"]==previous[index]["cwd"] and row["new_output"]==previous[index]["new_output"]
 # Independently reproduce the already accepted JSON encoder format.
 encoded=(json.dumps(row["argv"],sort_keys=True,separators=(",",":"))+"\n").encode()
 assert digest(encoded)==row["argv_sha256"]
 argv=list(row["argv"])
 if index==0:
  pos=argv.index("f06_native_signal_restore_fp_candidate");assert argv[pos-1]=="--cfg"
  del argv[pos-1:pos+1]
 elif index==2: argv.remove("-DMCKERNEL_RUST_F06_NATIVE_SIGNAL_RESTORE_FP")
 assert argv==previous[index]["argv"]
assert recipe["retained_inputs"]==old["retained_inputs"] and len(recipe["retained_inputs"])==8
link=commands[3]["argv"]
objects=[v for v in link if v.endswith(".o")]
assert len(objects)==11 and len(set(objects))==11
retained={v["link_token"] for v in recipe["retained_inputs"]}
produced={"rust/mckernel_rust.o","CMakeFiles/mckernel.img.dir/syscall.c.o","CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o"}
assert retained.isdisjoint(produced) and retained|produced==set(objects)
profile=load("candidate/scripts/f06_origin_command_profile.json")
assert profile["exact_commands"][0]["argv"]==commands[2]["argv"]
assert profile["composed_arch_source_sha256"]==ref(PACKET/"candidate/arch/x86_64/kernel/syscall.c")["sha256"]
assert ("PROFILE_SHA256 = "+json.dumps(ref(PACKET/"candidate/scripts/f06_origin_command_profile.json")["sha256"])) in (PACKET/"candidate/scripts/derive_f06_origin.py").read_text()
assert recipe["prerequisite_origin"]["output"]=="/work/output/build/kernel/rust/f06-origin"
overlay=load("RUST-CLOSED-SOURCE-OVERLAY.NOT-MATERIALIZED.json");refs(overlay)
old_overlay=json.loads(check_ref(inputs["overlay117"]))
a={v["relative"]:v for v in old_overlay["files"]};b={v["relative"]:v for v in overlay["files"]}
assert len(b)==123 and sum(v.endswith(".rs") for v in b)==112
assert set(b)-set(a)=={"f06_native_signal_restore_fp.rs"}
assert {k for k in a if a[k]["source"]!=b[k]["source"]}=={"lib.rs","syscall_policy.rs"}
assert all(a[k]==b[k] for k in a if k not in {"lib.rs","syscall_policy.rs"})
assert overlay["physical_directory_exports_created"]==0
# Import only the pure source unittest module; skip its writing __main__ block.
sys.path.insert(0,str(PACKET))
spec=importlib.util.spec_from_file_location("independent_composition_tests",PACKET/"test_composition118.py")
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
stream=io.StringIO(); result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(module.Composition))
(HERE/"PURE-CONTROLS.stdout").write_text(stream.getvalue())
assert result.wasSuccessful() and result.testsRun==20
leaf=(PACKET/"candidate/kernel/rust/f06_native_signal_restore_fp.rs").read_text().splitlines()
assert "line!() as CInt" in leaf[97] and "line!() as CInt" in leaf[105]
report=dict(scope=ready["scope"],recorded_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),status="PASS_INDEPENDENT_PURE_SOURCE_AND_RECIPE_BINDINGS",source_ready=ref(PACKET/"SOURCE-READY.json"),checks=dict(unique_BYTE_refs=len({(r["path"],r["sha256"]) for r in checked}),cumulative_map_paths=9,incremental_map_paths=8,independent_line_number_patch_application="PASS",literal_argv_delta="only cfg pair in0 and define in2;1/3 exact",fresh_argv_hashes=4,retained_objects=8,raw_link_inputs=11,new_object_slots=3,Rust_source_reference_files=123,Rust_source_reference_rs_files=112,overlay_changed_inherited_files=["lib.rs","syscall_policy.rs"],pure_tests=result.testsRun,pure_failures=len(result.failures),pure_errors=len(result.errors),tracked_alloc_source_line=98,tracked_free_source_line=106),constraints=dict(cpu="0",jobs=1,address_space_bytes=2*1024**3,compiler_calls=0,producer_calls=0,fixture_replays=0,runtime_operations=0,canonical_writes=0),bindings=sorted({r["path"]:r for r in checked}.values(),key=lambda r:r["path"]))
(HERE/"INDEPENDENT-CHECKS.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps({k:v for k,v in report.items() if k!="bindings"},indent=2))
