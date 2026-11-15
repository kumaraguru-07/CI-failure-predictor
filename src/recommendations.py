"""Advisory CI ordering; mandatory checks remain required for every band."""
import math

def recommend_ci(risk,context=None):
    priorities = {
        "LOW":["Use the standard CI order."],
        "MEDIUM":["Run fast unit checks early.", "Run the remaining required checks in the normal pipeline."],
        "HIGH":["Run fast failure-detecting checks early.", "Prioritize the full required test suite and integration checks.", "Review the prediction signals before merging."]}
    if risk not in priorities:
        raise ValueError("Expected LOW, MEDIUM or HIGH risk")
    actions = list(priorities[risk])
    evidence = {}
    rules = {
        "dependency_file_changed":"Run dependency resolution and compatibility checks early.",
        "configuration_file_changed":"Validate changed configuration before expensive jobs.",
        "ci_workflow_changed":"Validate the modified workflow and its permissions.",
        "docker_file_changed":"Validate the modified container build configuration."}
    for name,action in rules.items():
        value = (context or {}).get(name)
        if value is None or isinstance(value,(int,float)) and math.isnan(value):
            evidence[name] = "unknown"
        elif not isinstance(value,(int,float)) or value not in (0,1):
            raise ValueError(f"{name} must be 0, 1 or missing")
        else:
            evidence[name] = "changed" if value==1 else "unchanged"
            if value==1:
                actions.append(action)
    return {"risk_level":risk, "priority":actions,"change_evidence":evidence,
        "mandatory_checks_required":True,
        "skip_tests":False,
        "merge_permission":"Prediction does not authorize merging; required checks must pass."}
