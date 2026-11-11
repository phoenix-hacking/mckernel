import ast,datetime,hashlib,importlib.util,json,os,pathlib,shutil,sys,time,traceback
ROOT=pathlib.Path("/home/holden/mckernel");HERE=pathlib.Path("/home/holden/mckernel-work/m14-blocker-resolution-20261110/native-signal-four-contract-tests-p04source-max-1/correction-1/source-order-correction-1");OUT=HERE/"execution-1"
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(n,d):(OUT/n).write_text(json.dumps(d,indent=2,sort_keys=True)+"\n")
request=HERE/"REQUEST.json";assert sha(request)=="73ad79e6354bf6bc79fe80e619d8931097d87bef61b43e5f52b8b4cd471bf276"
review=pathlib.Path(sys.argv[1]);assert sha(review)==sys.argv[2];assert json.loads(review.read_text())["decision"].startswith("GO")
q=json.loads(request.read_text());assert not OUT.exists();OUT.mkdir(mode=0o700);started=now();owner=None;phase=None;current_argv=None;results=[];admitted=False
try:
 inputs=pathlib.Path(q["inputs"]["path"]);assert sha(inputs)==q["inputs"]["sha256"];bound=json.loads(inputs.read_text())
 for x in bound["files"]+list(bound["package_sources"].values())+[bound["retained_scope"],bound["interpreter"]]:
  p=pathlib.Path(x["path"]);assert p.is_file() and sha(p)==x["sha256"] and p.stat().st_size==x["bytes"],str(p)
 shared=pathlib.Path("/home/holden/mckernel-work/m15-original-integration-20261110T0708Z/exact-build-route-1/config-build-1/kernel-modules-1/artifact-qualification-1/module-export-contract-reconciliation-1/reader-successor-1/run_once.py");assert sha(shared)=="983b8c3ceabcd8dc4d2e1999d75e6edbef91145a5f2ab18bfa1a2dfa6639c822"
 tree=ast.parse(shared.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ("guard","overhead")],type_ignores=[]),str(shared),"exec"))
 stamp=guard();mem=int(next(s.split()[1] for s in pathlib.Path("/proc/meminfo").read_text().splitlines() if s.startswith("MemAvailable:")))*1024;over=overhead();cap=q["profile"]["max_address_space_bytes"];growth=q["profile"]["output_disk_reservation_bytes"];GiB=2**30
 assert mem>=26*GiB and over+cap<=4*GiB and shutil.disk_usage(ROOT).free>=16*GiB+growth and shutil.disk_usage(HERE).free>=12*GiB+growth
 output=pathlib.Path(q["fresh_output_root"]);assert not output.exists();output.mkdir(mode=0o700);pathlib.Path(q["private_tmp"]).mkdir(mode=0o700)
 save("ADMISSION.json",dict(at=now(),guard_updated_at=stamp,MemAvailable_bytes=mem,all_current_overhead_bytes=over,new_job_bytes=cap,CPU=q["profile"]["cpu"],new_jobs=1,aggregate_HOST_bytes=4*GiB,aggregate_jobs_max=3,other_current_payloads=[],source_or_native_or_UNKNOWN_holds_released=False,request_sha256=sha(request),review_sha256=sha(review)));admitted=True
 helper=pathlib.Path(q["ownership"]["helper"]["path"]);assert sha(helper)==q["ownership"]["helper"]["sha256"];spec=importlib.util.spec_from_file_location("exact_owned_process",str(helper));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);owner=module.Owner(OUT)
 for index,c in enumerate(q["commands"]):
  phase=c["id"];current_argv=c["argv"];guard();r=owner.run(c["argv"],env=os.environ.copy(),cwd=q["cwd"],timeout=c["wall_seconds"],label=q["ownership"]["labels"][index]);rec=owner.records[-1]
  assert int(rec["leader"])>0 and int(rec["leader_birth"])>0 and rec["leader_parent_joined"] and rec["whole_descendants_joined"] and rec["streams_closed"] and not rec["timed_out"] and not rec["leader_group_signalled"] and not rec["adopted_reaps"] and not rec["adopted_kills"] and not rec["remaining_direct_children"] and rec["error"] is None,rec
  assert r.returncode==c["expected_exit"]==rec["status"],phase
  if c.get("required_stdout")=="empty":assert r.stdout==b""
  if c.get("required_stderr")=="empty":assert r.stderr==b""
  if "required_output" in c:
   p=pathlib.Path(c["required_output"]);assert p.stat().st_size>0 and p.read_bytes()[:4]==b"\x7fELF";save("EXECUTABLE.json",dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p),mode=oct(p.stat().st_mode&0o777)))
  if "required_stdout_json" in c:assert json.loads(r.stdout)==c["required_stdout_json"]
  results.append(dict(id=phase,argv=current_argv,cwd=q["cwd"],exit=r.returncode,ownership=rec));save("PARTIAL.json",dict(started_at=started,results=results))
 remaining=pathlib.Path("/proc/self/task/%d/children"%os.getpid()).read_text().split();assert len(owner.records)==q["ownership"]["record_count"] and not remaining
 save("RESULT.json",dict(status="PASS_TWO_REMAINING_NATIVE_CONTRACTS_PENDING_SAVED_QUALIFICATION",started_at=started,finished_at=now(),request_sha256=sha(request),review_sha256=sha(review),results=results,all_waits_streams_joined=True,remaining_direct_children=remaining,actual_kernel_CPU_offload_hostwait_native_executed=False,original_acceptance=False));save("INNER-CLOSURE.json",dict(at=now(),inner_two_remaining_families_joined=True,new_job_bytes=cap,new_job_count=1,Root_full_tool_completion_still_required_before_release=True,other_holds_unchanged=True));print(json.dumps(dict(status="PASS",commands=2,families=2,finished_at=now())))
except BaseException as exc:
 try:save("RESULT.json",dict(status="FAILED_PRESERVED_NO_UNCHANGED_RETRY",started_at=started,finished_at=now(),phase=phase,argv=current_argv,error=type(exc).__name__+": "+str(exc),traceback=traceback.format_exc(),admitted=admitted,results=results,ownership=owner.records if owner else [],original_acceptance=False,automatic_resource_release=False))
 except BaseException:pass
 raise
