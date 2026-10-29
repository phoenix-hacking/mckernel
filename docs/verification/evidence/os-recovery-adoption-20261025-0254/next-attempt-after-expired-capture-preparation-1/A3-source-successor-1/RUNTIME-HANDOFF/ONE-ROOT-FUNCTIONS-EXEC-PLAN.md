Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Prospective Root-only plan, not executed. Complete PRECLOCK-FIXED-DATA-ORDER and actual new independent PREWARM first. Root MUST NOT launch approver. Existing independent owner alone uses independent_finite_owner_only argv under its new Root authorization and retains its own process/join. Do not reuse A2 hard-coded run_finite_once.py.

This single Root cell runs only exact existing physical→holder→fill→held→oncepublisher paths. All paths/bootstrap arguments are absolute. It creates no production framework. Source original120s physical/resource/Hot/publisher checks and600s finite wait are unchanged. Other reservations and all fixed metadata/publication are finished beforeclock. Holders andfiniteowners get no new automatic CPU-kill timer.

On phasefailure, stored holder/tool handles remain owned by Root; no auto signal, recapture, retry, oldnonce reuse, timestamp renewal, sourcechange or globalcontrol change. Root separately reconciles/withdraws only its own new operation if actually unlaunched. Only original holder consumes READY/starts runner. Actual exit/raw files must be retained; no current/nativeclearance inferred.

```javascript
const scope="Functional McKernel OS/apps and Rust/assembly migration only; no security testing.";
const SQ=String.fromCharCode(39), BS=String.fromCharCode(92);
const q=s=>SQ+s.split(SQ).join(SQ+BS+SQ+SQ)+SQ;
async function complete(argv,phase){
 text(scope+" "+phase);
 let r=await tools.exec_command({cmd:argv.map(q).join(" "),yield_time_ms:1000,max_output_tokens:1200});
 if(r.session_id)store("CURRENT118_A3_"+phase+"_session",r.session_id);
 while(r.session_id&&r.exit_code===undefined){
  if(r.output)notify({phase,output:r.output});
  r=await tools.write_stdin({session_id:r.session_id,chars:"",yield_time_ms:1000,max_output_tokens:1200});
 }
 text({phase,result:r});
 if(r.exit_code!==0)throw new Error(phase+" failed; preserve custody/handles/evidence; no retry/publication");
 return r;
}
const plan={
  "commands": {
    "physical": [
      "/usr/bin/taskset",
      "-c",
      "0",
      "/usr/bin/prlimit",
      "--as=2147483648:2147483648",
      "--cpu=60:60",
      "--core=0:0",
      "--",
      "/home/holden/anaconda3/bin/python3",
      "-I",
      "-B",
      "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/next-attempt-after-expired-capture-preparation-1/A3-source-successor-1/cohort/root_capture_once.py",
      "--bindings",
      "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/next-attempt-after-expired-capture-preparation-1/A3-source-successor-1/cohort/ROOT-ACTUAL-CAPTURE-PUBLISH-BINDINGS.json",
      "--handoff",
      "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT118-CLEARPTE-SIGNALFP-BUILD-ADMISSION-3/FINITE-REVIEW-HANDOFF",
      "--phase",
      "physical"
    ],
    "holder": [
      "/usr/bin/taskset",
      "-c",
      "0",
      "/usr/bin/prlimit",
      "--as=2147483648:2147483648",
      "--core=0:0",
      "--",
      "/home/holden/anaconda3/bin/python3",
      "-I",
      "-B",
      "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT118-CLEARPTE-SIGNALFP-BUILD-ADMISSION-3/hold_and_run_build_only.py",
      "--bootstrap-grant",
      "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT118-CLEARPTE-SIGNALFP-BUILD-ADMISSION-3/ROOT-HOLDER-BOOTSTRAP-GRANT.json"
    ],
    "fill": [
      "/usr/bin/taskset",
      "-c",
      "0",
      "/usr/bin/prlimit",
      "--as=2147483648:2147483648",
      "--cpu=60:60",
      "--core=0:0",
      "--",
      "/home/holden/anaconda3/bin/python3",
      "-I",
      "-B",
      "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/next-attempt-after-expired-capture-preparation-1/A3-source-successor-1/cohort/ROOT-PREWRITTEN-RESOURCE-INPUT-FILL.py"
    ],
    "held": [
      "/usr/bin/taskset",
      "-c",
      "0",
      "/usr/bin/prlimit",
      "--as=2147483648:2147483648",
      "--cpu=60:60",
      "--core=0:0",
      "--",
      "/home/holden/anaconda3/bin/python3",
      "-I",
      "-B",
      "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/next-attempt-after-expired-capture-preparation-1/A3-source-successor-1/cohort/root_capture_once.py",
      "--bindings",
      "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/next-attempt-after-expired-capture-preparation-1/A3-source-successor-1/cohort/ROOT-ACTUAL-CAPTURE-PUBLISH-BINDINGS.json",
      "--handoff",
      "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT118-CLEARPTE-SIGNALFP-BUILD-ADMISSION-3/FINITE-REVIEW-HANDOFF",
      "--phase",
      "held"
    ],
    "publisher": [
      "/usr/bin/taskset",
      "-c",
      "0",
      "/usr/bin/prlimit",
      "--as=2147483648:2147483648",
      "--cpu=60:60",
      "--core=0:0",
      "--",
      "/home/holden/anaconda3/bin/python3",
      "-I",
      "-B",
      "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/next-attempt-after-expired-capture-preparation-1/A3-source-successor-1/cohort/publish_after_independent_pass_once.py",
      "--bindings",
      "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/next-attempt-after-expired-capture-preparation-1/A3-source-successor-1/cohort/ROOT-ACTUAL-CAPTURE-PUBLISH-BINDINGS.json",
      "--handoff",
      "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT118-CLEARPTE-SIGNALFP-BUILD-ADMISSION-3/FINITE-REVIEW-HANDOFF"
    ]
  },
  "preclock": [
    "/home/holden/anaconda3/bin/python3",
    "-I",
    "-B",
    "-c",
    "from pathlib import Path\nimport json,time\nA=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT118-CLEARPTE-SIGNALFP-BUILD-ADMISSION-3');C=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/next-attempt-after-expired-capture-preparation-1/A3-source-successor-1/cohort');H=A/\"FINITE-REVIEW-HANDOFF\"\nN='e984210ca59641b299cf42d392eb953b'\nfor p in [C/\"ROOT-ACTUAL-OTHER-RESERVATIONS.json\",C/\"ROOT-ACTUAL-CAPTURE-PUBLISH-BINDINGS.json\",C/\"REVIEWER-ACTUAL-BINDINGS.json\",A/\"PROFILE.SOURCE-ONLY.json\",A/\"ROOT-ACTUAL-STATIC-SOURCE-PUBLICATION.json\",A/\"ROOT-HOLDER-BOOTSTRAP-GRANT.json\",H/\"PREWARM_READY.json\"]:assert p.is_file(),str(p)\nr=json.loads((C/\"ROOT-ACTUAL-OTHER-RESERVATIONS.json\").read_bytes());assert r[\"author\"]==\"/root\"and r[\"actual_reservations_attested\"]is True and(r[\"other_reserved_memory_bytes\"],r[\"other_reserved_pids\"],r[\"aggregate_pid_budget\"])==(2147483648,64,576)\nb=json.loads((C/\"ROOT-ACTUAL-CAPTURE-PUBLISH-BINDINGS.json\").read_bytes());p=json.loads((H/\"PREWARM_READY.json\").read_bytes());assert b[\"nonce\"]==p[\"nonce\"]==N and b[\"admission\"]==p[\"admission\"]==str(A)\nfor name in [\"HOLDER\",\"ROOT-PREHOLDER-PHYSICAL-1.json\",\"ROOT-ACTUAL-RESOURCE-INPUT-1.json\",\"ROOT-ACTUAL-BUILD-RESOURCE-AUTHORITY.json\",\"ROOT-EXECUTION-INPUT.GRANT-PENDING-REVIEW.json\",\"OUTPUT\",\"ROOT-ACTUAL-ONE-BUILD-ONLY-GRANT.json\"]:assert not(A/name).exists(),name\nprint(\"PRECLOCK_FIXED_DATA_PRESENT\")\n"
  ],
  "ready": [
    "/home/holden/anaconda3/bin/python3",
    "-I",
    "-B",
    "-c",
    "from pathlib import Path\nimport json,time\nA=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT118-CLEARPTE-SIGNALFP-BUILD-ADMISSION-3');C=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/next-attempt-after-expired-capture-preparation-1/A3-source-successor-1/cohort');H=A/\"FINITE-REVIEW-HANDOFF\"\nN='e984210ca59641b299cf42d392eb953b'\nphysical=json.loads((A/\"ROOT-PREHOLDER-PHYSICAL-1.json\").read_bytes());p=A/\"HOLDER/HOLDER.READY.json\"\nwhile not p.exists():\n assert 0<=time.time()-physical[\"observed_clocks\"][0]<=120,\"original physical120s elapsed\"\n time.sleep(.02)\nv=json.loads(p.read_bytes());assert v[\"nonce\"]==N and v[\"holder\"][\"fd\"]==3 and v[\"bootstrap\"][\"path\"]==str(A/\"ROOT-HOLDER-BOOTSTRAP-GRANT.json\")\nprint(json.dumps(v[\"holder\"]))\n"
  ],
  "passed": [
    "/home/holden/anaconda3/bin/python3",
    "-I",
    "-B",
    "-c",
    "from pathlib import Path\nimport json,time\nA=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT118-CLEARPTE-SIGNALFP-BUILD-ADMISSION-3');C=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/next-attempt-after-expired-capture-preparation-1/A3-source-successor-1/cohort');H=A/\"FINITE-REVIEW-HANDOFF\"\nN='e984210ca59641b299cf42d392eb953b'\np=H/\"INDEPENDENT-FINITE-REVIEW.PASS.json\";r=json.loads((A/\"ROOT-ACTUAL-BUILD-RESOURCE-AUTHORITY.json\").read_bytes())\nwhile not p.exists():\n assert 0<=time.time()-r[\"observed_at_epoch\"]<=120,\"original resource120s elapsed\"\n assert not(H/\"FINITE-COMPLETION.FAILURE.json\").exists(),\"independent owner failed\"\n time.sleep(.02)\nv=json.loads(p.read_bytes());assert v[\"nonce\"]==N and v[\"decision\"]==\"PASS_EXACT_BUILD_ONLY_EXECUTION\"and v[\"independent\"]is True and v[\"implementation_ownership\"]is False\nprint(v[\"approved_input_sha256\"])\n"
  ]
};
await complete(plan.preclock,"preclock");
await complete(plan.commands.physical,"physical");
const holder=await tools.exec_command({cmd:plan.commands.holder.map(q).join(" "),yield_time_ms:1000,max_output_tokens:1200});
text({phase:"holder_started",result:holder});
if(!holder.session_id||holder.exit_code!==undefined)throw new Error("holder ended before READY; no retry");
const holderSession=holder.session_id;store("CURRENT118_A3_holder_session",holderSession);
await complete(plan.ready,"holder_ready");
await complete(plan.commands.fill,"resource_input_fill");
await complete(plan.commands.held,"held");
await complete(plan.passed,"actual_independent_hot_PASS");
await complete(plan.commands.publisher,"once_publisher");
let joined=await tools.write_stdin({session_id:holderSession,chars:"",yield_time_ms:1000,max_output_tokens:1600});
while(joined.session_id&&joined.exit_code===undefined){
 if(joined.output)notify({phase:"holder_runner",output:joined.output});
 joined=await tools.write_stdin({session_id:holderSession,chars:"",yield_time_ms:1000,max_output_tokens:1600});
}
text({phase:"actual_original_holder_tool_join",result:joined});
```
