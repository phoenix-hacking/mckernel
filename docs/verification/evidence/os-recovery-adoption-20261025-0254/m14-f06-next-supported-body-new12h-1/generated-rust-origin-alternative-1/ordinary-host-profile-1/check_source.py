"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure source/profile regression only: no main runner, producer or compiler entry.
"""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNNER = HERE.parents[2] / "ordinary-host-new12h-runner-source-1/run_new12h_host.py"


def main():
    expected = "6e98a1fbcbce2e822a815a05516287e7122cbd8e06d43277134b27b70cf3ad34"
    assert hashlib.sha256(RUNNER.read_bytes()).hexdigest() == expected
    spec = importlib.util.spec_from_file_location("existing_host_runner_source", RUNNER)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    profile = json.loads((HERE / "PROFILE.NOT-GRANTED.json").read_text())
    plan = json.loads((HERE / "PLAN.SOURCE-ONLY.json").read_text())
    checks = []
    runner.validate_profile(profile)
    checks.append("retained runner validates exact six-command profile")
    runner.verify(profile["inputs"] + [leaf["plan"] for leaf in profile["leaves"]])
    checks.append("all source/tool/header/helper and plan pins authenticate")
    assert profile["commands"] == plan["commands"] and len(plan["commands"]) == 6
    for target in [profile["capture_root"]] + [leaf["output"] for leaf in profile["leaves"]]:
        assert not Path(target).exists(), "fresh output/capture already exists"
    assert plan["output_root"] != profile["capture_root"]
    assert all(leaf["output"] not in command["argv"]
               for leaf in profile["leaves"] for command in plan["commands"])
    checks.append("fresh output/capture names have no executable-directory collision")
    for field in ["argv", "purpose"]:
        changed = copy.deepcopy(profile)
        if field == "argv":
            changed["commands"][0][field].append("--unreviewed")
        else:
            changed["commands"][0][field] = "unqualified purpose"
        try:
            runner.validate_profile(changed)
        except ValueError:
            pass
        else:
            raise AssertionError("changed command binding should fail")
    checks.append("argv/purpose drift rejected by retained pure validator")
    tree = ast.parse((HERE / "expect_negative_guard.py").read_text())
    assignments = {node.targets[0].id: node.value for node in tree.body
                   if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)}
    assert ast.literal_eval(assignments["ARGV"]) == plan["negative_raw_compiler_argv"]
    assert plan["negative_raw_compiler_argv"][0] == "/usr/bin/gcc-9"
    assert Path(plan["negative_raw_compiler_argv"][-1]).name == "guard-negative.o"
    assert profile["leaves"][-1]["expected_stdout"] == (
        "PASS expected original __FILE__ binding drift; no output object\n")
    checks.append("negative fixture compiler argv and exact diagnostic oracle bind")
    assert profile["leaves"][0]["expected_stdout"] == (
        "PASS F06 alloc832/free8 original-C ABI and provenance\n")
    assert profile["leaves"][1]["expected_stdout"] == ""
    assert "-I" + str(HERE / "future-host-output-1/generated") in plan["commands"][2]["argv"]
    checks.append("840-case parity and positive/negative guard stdout oracles preserved")
    result = dict(scope=__doc__.splitlines()[0], status="PASS_PURE_SOURCE_ONLY",
                  checks=checks, input_pins=len(profile["inputs"]),
                  actual_compiler_or_fixture_commands=0, execution_grant=False,
                  profile_sha256=hashlib.sha256((HERE / "PROFILE.NOT-GRANTED.json").read_bytes()).hexdigest())
    (HERE / "SOURCE-CHECK-RESULT.json").write_text(json.dumps(result, indent=2) + "\n")
    print("PASS pure source checks6; compiler/fixture execution0; grant absent")


if __name__ == "__main__":
    main()
