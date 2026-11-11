"""Five actual pure named-manifest guard calls; no live admission imports."""
import ast
import copy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110/native-functional-a2f-cohort-binding-publicabi-max-1/candidate/package/native_resource_admission.py')
SOURCE_SHA = '1e7ced654a476c1e978c65e6f91b57088a8803917f9dc68ab69481dade8c1462'

def observe(guard, name, manifest):
    try:
        result = guard(None, manifest)
    except KeyError as exc:
        return dict(name=name, exception=type(exc).__name__, key=exc.args[0])
    except Exception as exc:
        return dict(name=name, exception=type(exc).__name__, message=str(exc))
    return dict(name=name, returned_none=result is None, exception=None)

def main():
    raw = SOURCE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SOURCE_SHA
    tree = ast.parse(raw.decode("utf-8"), filename=str(SOURCE))
    declarations = [node for node in tree.body if isinstance(node, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id in ("EXPECTED", "MODULES") for t in node.targets)]
    assert len(declarations) == 2
    need = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "need"]
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "NativeAdmission"]
    assert len(need) == len(classes) == 1
    methods = [node for node in classes[0].body if isinstance(node, ast.FunctionDef) and node.name == "_named_manifest"]
    assert len(methods) == 1
    projection = copy.deepcopy(classes[0])
    projection.body = [copy.deepcopy(methods[0])]
    unit = ast.Module(body=copy.deepcopy(declarations + need) + [projection], type_ignores=[])
    namespace = {"__name__": "actual_pure_native_named_manifest_guard"}
    exec(compile(unit, str(SOURCE), "exec"), namespace)
    guard = namespace["NativeAdmission"]._named_manifest
    selected = json.loads((HERE / "SELECTED-MANIFEST.json").read_text())
    cases = []
    cases.append(observe(guard, "selected_a2f_same_artifact_module_and_named_command_tuple", copy.deepcopy(selected)))
    stale = copy.deepcopy(selected)
    stale["artifacts"]["mckernel_image"]["sha256"] = "c66492d44e2e71a072114f637cd04dff5feb77bd2216c42ef69f7a56944c7a5f"
    cases.append(observe(guard, "stale_old_c664_image", stale))
    wrong = copy.deepcopy(selected)
    wrong["artifacts"]["mckernel_image"]["sha256"] = "0" * 64
    cases.append(observe(guard, "mismatched_image_digest", wrong))
    missing = copy.deepcopy(selected)
    del missing["artifacts"]["mckernel_image"]
    cases.append(observe(guard, "missing_image_member_invalid", missing))
    wrong_payload = copy.deepcopy(selected)
    wrong_payload["artifacts"]["payload"]["sha256"] = "0" * 64
    cases.append(observe(guard, "new_image_wrong_payload_remains_rejected", wrong_payload))
    print(json.dumps(dict(scope="PURE_ACTUAL_NAMED_MANIFEST_GUARD_ONLY", NativeAdmission_constructed=False,
                         native_or_account_or_resource_action=False, cases=cases), sort_keys=True, separators=(",", ":")))

if __name__ == "__main__":
    main()
