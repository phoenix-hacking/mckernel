
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Exact F05 successor appended AFTER the complete f368 evaluator/wrapper chain.
# Historical BEGIN_PROCESS_CASES and both audit/cleanup implementations stay intact.
F05_CASE = "M14-05-05-owned-processvm-v2-204B"
F05_PROFILE = "begin-cleanup-real-ack-owned-processvm-v2-204B-v1"
F05_SOURCE_SHA = "7fa47f37a4006c4050c94409405da48c7bb959d813ec6523f15a54f55b5c8142"
F05_BINDING = None  # ROOT_FINALIZER_BINDING: v2 is non-runnable until exact HOST binding
F05_ORACLE_SHA = "c38ea126ec9f146eb0f0caf6bdc2a212d58230c4802b1112c65b8faa007e338a"
F05_HOST_STATUS = "PASS_F05_V2_OWNED_LINUX_REFERENCE_ONLY"
F05_SOURCE_SIZE = 11703
F05_ORACLE_SIZE = 2097
F05_STDOUT = (
    b"OWNED_F05 v2 children=1 clone_child_settid=1 parent_tid_unchanged=1\n"
    b"traceme=0 sigstop=19 peek=0 poke=0 readback=0 cross_4k_word=1\n"
    b"child_verified=1 private_unchanged=1 child_exit=0 reaped=1\n"
    b"OWNED_F05 PASS\n"
)
F05_ORACLE = {"stdout_hex": F05_STDOUT.hex(), "stderr_hex": "", "exit_code": 0}
F05_MODULE_SHAS = (
    "daced2910f2391f15f1963399838c5089ef7ac6be8f6614db88ff8443c48900c",
    "887dc3567e6035c921588e61b45b41a8ef32a972d142fe2ba82ec48442353b12",
    "57546af5110c0674b307e5ac5a328228abbe784f890f69521db5f594f21f6ae8",
)
_f05_previous_cleanup_profile = _validate_cleanup_profile
_f05_previous_validate_manifest = _validate_manifest
_f05_previous_process_case = _begin_process_case
_f05_previous_evaluate = evaluate


def _f05_bound_ref(ref, size, sha, label):
    _need(ref.get("size") == size and ref.get("sha256") == sha, label + " frozen identity")
    return _ref(ref, label)


def _f05_binding():
    _need(type(F05_BINDING) is dict, "F05 v2 unknown HOST binding; non-runnable template")
    binding = F05_BINDING
    _keys(binding, ("schema_version", "status", "case_id", "source", "oracle", "payload",
                    "host_qualification", "static_elf"))
    _need(binding["schema_version"] == 1 and binding["status"] == "SEALED_EXACT_V2_HOST_TUPLE" and
          binding["case_id"] == F05_CASE and binding["static_elf"] ==
          {"class": 64, "machine": 62, "type": 2, "interp": False, "needed": False},
          "F05 v2 exact finalized binding")
    _f05_bound_ref(binding["source"], F05_SOURCE_SIZE, F05_SOURCE_SHA, "F05 v2 source")
    _f05_bound_ref(binding["oracle"], F05_ORACLE_SIZE, F05_ORACLE_SHA, "F05 v2 oracle")
    for name in ("payload", "host_qualification"):
        _need(type(binding[name].get("size")) is int and binding[name]["size"] > 0 and
              isinstance(binding[name].get("sha256"), str) and SHA.fullmatch(binding[name]["sha256"]),
              "F05 v2 actual " + name + " required")
        _ref(binding[name], "F05 v2 " + name)
    _need(binding["payload"]["sha256"] != "be508daa7549a50312306bb1064d4df9fe738dc9d7ba6dd32d58e8a1d97258a2" and
          binding["host_qualification"]["sha256"] != "ca6f2ee37dde1da02ffb1d001a9c6457fdf4fbefe20017e45e34a9f12796e604",
          "F05 v2 cannot reuse historical v1 HOST/payload")
    return binding


def _validate_cleanup_profile(profile, modules):
    if profile.get("id") != F05_PROFILE:
        return _f05_previous_cleanup_profile(profile, modules)
    _keys(profile, ("schema_version", "id", "consumer", "provider", "modules",
                    "child_trace_cases", "case_binding"))
    _need(type(profile["schema_version"]) is int and profile["schema_version"] == 1 and
          profile["child_trace_cases"] == [F05_CASE], "F05 v2 exact cleanup scope")
    for name in ("consumer", "provider"):
        _need(profile[name] == BEGIN_CLEANUP_SOURCE_REFS[name], "F05 BEGIN source identity")
        _ref(profile[name], "F05 BEGIN " + name)
    _need(type(modules) is list and len(modules) == 3 and profile["modules"] == modules and
          tuple(row["sha256"] for row in modules) == F05_MODULE_SHAS, "F05 module tuple")
    actual = _f05_binding()
    _need(profile["case_binding"] == {"source": actual["source"], "oracle": actual["oracle"],
          "host_qualification": actual["host_qualification"], "payload_timeout_ms": 10000},
          "F05 v2 exact source/HOST/10s profile")
    return dict(profile)


def _f05_contract(manifest):
    _need(manifest["case_id"] == F05_CASE and "pair" not in manifest,
          "F05 exact single-parent case ID")
    actual = _f05_binding()
    profile = manifest.get("cleanup_profile", {})
    _need(profile.get("id") == F05_PROFILE, "F05 explicit cleanup profile required")
    _validate_cleanup_profile(profile, manifest["modules"])
    _need(manifest["payload"] == {
        "argv": ["/bin/mcexec", "-t", "1", "0", "/apps/app"],
        "cwd": "/case/work", "env": {"PATH": "/usr/bin:/bin", "COKERNEL_PATH": "/apps"},
        "oracle": F05_ORACLE, "stdout_limit_bytes": 1024, "stderr_limit_bytes": 1024,
    }, "F05 frozen launch/oracle/stream contract")
    _need(manifest["artifacts"]["payload"] == actual["payload"], "F05 v2 exact payload tuple")
    collector = manifest["staging"]["collector"]
    _need(collector["size"] == 1021320 and collector["sha256"] ==
          "c020a8e0ab43e222caf901d92bfecb2a8d8cf20ea0b539910a17a578f1fd12fc",
          "F05 retained 1024-byte/10s collector")
    oracle = json.loads(Path(actual["oracle"]["path"]).read_text(), object_pairs_hook=_pairs)
    _need(oracle["source"]["sha256"] == F05_SOURCE_SHA and
          {key: oracle[key] for key in F05_ORACLE} == F05_ORACLE and
          oracle["raw_clone_flags_hex"] == "0x01200011" and
          oracle["child_forwarded_witness"]["syscall"] == 1 and
          oracle["child_observed_host_terminal"] == 231, "F05 v2 frozen semantic oracle")
    host = json.loads(Path(actual["host_qualification"]["path"]).read_text(), object_pairs_hook=_pairs)
    _need(host["status"] == F05_HOST_STATUS and host["source"]["sha256"] == F05_SOURCE_SHA and
          host["source"]["bytes"] == F05_SOURCE_SIZE and
          host["executable"]["sha256"] == actual["payload"]["sha256"] and
          host["executable"]["bytes"] == actual["payload"]["size"] and
          host["oracle"]["sha256"] == F05_ORACLE_SHA, "F05 v2 exact HOST joins")
    results = host["results"]
    _need(type(results) is list and len(results) == 3, "F05 HOST qualification stages")
    for index, row in enumerate(results):
        _need(row["index"] == index and type(row["returncode"]) is int and row["returncode"] == 0 and
              row["direct_child_joined"] is True and row["group_absent"] is True and
              row["remaining_group_members"] == row["unexpected_group_members"] == [] and
              row["timed_out"] is False and row["closed_streams"] is True and
              row["error"] is None and row["retirement_error"] is None,
              "F05 HOST positive process/stream joins")
    for name, expected in (("stdout", F05_STDOUT), ("stderr", b"")):
        capture = results[2]["captures"][name]
        _need(capture["sha256"] == hashlib.sha256(expected).hexdigest() and
              capture["size"] == len(expected), "F05 HOST exact " + name)
        _ref({"path": capture["path"], "sha256": capture["sha256"], "size": capture["size"],
              "mode": stat.S_IFREG | int(capture["mode"], 8)}, "F05 HOST " + name)


def _f05_case_profile_guard(manifest):
    new_case = manifest.get("case_id") == F05_CASE
    new_profile = manifest.get("cleanup_profile", {}).get("id") == F05_PROFILE
    old_case = manifest.get("case_id") == "M14-05-05-owned-processvm-204B"
    old_binary = manifest.get("artifacts", {}).get("payload", {}).get("sha256") == "be508daa7549a50312306bb1064d4df9fe738dc9d7ba6dd32d58e8a1d97258a2"
    _need(not old_case and not old_binary, "F05 v1 unsupported proposal cannot enter v2 capability")
    binary_sha = F05_BINDING["payload"]["sha256"] if type(F05_BINDING) is dict else None
    frozen_binary = binary_sha is not None and manifest.get("artifacts", {}).get("payload", {}).get("sha256") == binary_sha
    frozen_output = manifest.get("payload", {}).get("oracle", {}).get("stdout_hex") == F05_STDOUT.hex()
    _need(new_case == new_profile and (not (frozen_binary or frozen_output) or new_case),
          "F05 case/profile identity mismatch or historical relabeling")
    return new_case


def _validate_manifest(obj):
    # Exact new-ID binding is mandatory; old identities retain their literal chain.
    new_case = _f05_case_profile_guard(obj)
    validated = _f05_previous_validate_manifest(obj)
    if new_case:
        _f05_contract(validated)
    return validated


def _begin_process_case(manifest):
    if manifest.get("case_id") == F05_CASE:
        return manifest.get("cleanup_profile", {}).get("id") == F05_PROFILE
    return _f05_previous_process_case(manifest)


def _f05_trace(serial):
    # Keep the retained exactly-one parent SCHEDULE rule, with no child filtering.
    schedules = []
    for line in serial.splitlines():
        if "application SCHEDULE " in line:
            match = re.search(r"application SCHEDULE os=(\d+) generation=(\d+) pid=(\d+) cpu=(\d+)\s*$", line)
            _need(match is not None, "F05 malformed schedule")
            schedules.append(tuple(map(int, match.groups())))
    _need(len(schedules) == 1 and schedules[0][:2] == (0, 1) and schedules[0][2] > 0 and
          schedules[0][3] == 0, "F05 exactly one positive parent schedule")
    parent = schedules[0][2]
    prefix = "os=0 generation=1 pid=" + str(parent)
    _, children = _audit_begin_children(serial, prefix)  # Unchanged full audit.
    _need(len(children) == 1, "F05 exactly one linked positive distinct child")
    child = children[0]
    lines = serial.splitlines()
    publication = {}; deletion = {}
    for position, line in enumerate(lines):
        for operation, rows in (("published", publication), ("deleted", deletion)):
            if "application procfs " + operation + " " not in line:
                continue
            match = re.search(r"application procfs " + operation +
                              r" os=(\d+) generation=(\d+) pid=(\d+) tid=(\d+)\s*$", line)
            _need(match is not None, "F05 malformed procfs lifecycle")
            os_id, generation, pid, tid = map(int, match.groups())
            _need((os_id, generation) == (0, 1) and pid in (parent, child) and tid == pid and
                  pid not in rows, "F05 foreign/duplicate procfs lifecycle")
            rows[pid] = position
    _need(set(publication) == set(deletion) == {parent, child}, "F05 complete owned procfs lifecycle")
    delivered = {}; returned = {}
    for position, line in enumerate(lines):
        match = re.search(r"application_syscall=(delivered|returned) os=0 generation=1 pid=(\d+) "
                          r"worker=(\d+) delivery=(\d+) cpu=(\d+) (?:number|value)=(-?\d+)\s*$", line)
        if match:
            kind, pid, worker, delivery, cpu, value = match.groups()
            row = (int(pid), int(worker), int(delivery))
            (delivered if kind == "delivered" else returned)[row] = (int(value), position)
    terminal = [(row, position) for row, (number, position) in delivered.items()
                if row[0] == child and number in (60, 231)]
    _need(len(terminal) == 1 and delivered[terminal[0][0]][0] == 231,
          "F05 v2 guest exit60 must forward sole host terminal231")
    child_terminal = terminal[0][1]
    writes = [(row, begin) for row, (number, begin) in delivered.items()
              if row[0] == child and number == 1]
    _need(len(writes) == 1 and writes[0][0] in returned and
          returned[writes[0][0]][0] == 0 and
          publication[child] < writes[0][1] < returned[writes[0][0]][1] < child_terminal,
          "F05 v2 actual child write1 RET0 before terminal231")
    # fd2/count0 and pre-TRACEME/self-stop order are frozen source/oracle facts.
    # Host delivery rows do not log syscall arguments or local SIGSTOP entry.
    parent_terminal = [position for row, (number, position) in delivered.items()
                       if row[0] == parent and number == 231]
    _need(len(parent_terminal) == 1 and publication[child] < child_terminal < deletion[child] <
          parent_terminal[0], "F05 child lifetime/parent terminal order")
    # The actual RET must join a parent wait4 delivery and name this linked child.
    # A stop wait4 can also return child; only a RET after forwarded terminal231 is a reap.
    reaps = [position for row, (value, position) in returned.items()
             if row[0] == parent and value == child and row in delivered and delivered[row][0] == 61 and
             delivered[row][1] < position and child_terminal < position < parent_terminal[0]]
    _need(len(reaps) == 1, "F05 exact successful parent wait4/reap after child terminal")
    # Retain the parent real-ACK/terminal/retirement contract literally.
    _check_begin_cleanup(serial, prefix, parent_terminal[0])


def evaluate(manifest, observation):
    new_case = _f05_case_profile_guard(manifest)
    if new_case:
        _f05_contract(manifest)
        _f05_trace(observation["serial"])
    # Invoke the final retained evaluate wrapper, not an AST-extracted old name.
    return _f05_previous_evaluate(manifest, observation)
