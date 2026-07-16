import ast
import json
import re
from pathlib import Path

import core.file_interaction as fi
import tmp.tmp as tmp
import output_generators.traceability as traceability

SERVICE_DIR_RE = re.compile(r"services/([^/\s'\"]+)/")


def service_dirs_from_scripts(package_json_text: str) -> dict:
    """Pure: parse package.json text, return {service_name: 'services/<name>'}.
    Service names are inferred from `services/<name>/...` paths in npm scripts.
    """
    try:
        data = json.loads(package_json_text)
    except json.JSONDecodeError:
        return dict()
    services = dict()
    for command in (data.get("scripts") or {}).values():
        for match in SERVICE_DIR_RE.finditer(str(command)):
            name = match.group(1)
            services[name] = f"services/{name}"
    return services


def _root_package_json():
    """Returns (text, path) of the shallowest package.json, or (None, None)."""
    files = fi.get_file_as_lines("package.json")
    best = None
    for f in files.values():
        depth = len(Path(f["path"]).parts)
        if best is None or depth < best[0]:
            best = (depth, "".join(f["content"]), f["path"])
    return (best[1], best[2]) if best else (None, None)


def set_microservices(dfd) -> dict:
    """Registers Node services in the tmp DFD, mirroring maven's set_microservices."""
    if tmp.tmp_config.has_option("DFD", "microservices"):
        microservices = ast.literal_eval(tmp.tmp_config["DFD"]["microservices"])
    else:
        microservices = dict()

    text, path = _root_package_json()
    if not text:
        return microservices

    for name, service_dir in service_dirs_from_scripts(text).items():
        id_ = max(microservices.keys(), default=-1) + 1
        microservices[id_] = {
            "name": name,
            "image": "image_placeholder",
            "type": "internal",
            "pom_path": service_dir,
            "properties": list(),
            "stereotype_instances": list(),
            "tagged_values": list(),
        }
        trace = {"item": name, "file": path, "line": "heuristic (package.json script)",
                 "span": "heuristic (package.json script)"}
        traceability.add_trace(trace)

    tmp.tmp_config.set("DFD", "microservices", str(microservices).replace("%", "%%"))
    return microservices


def detect_microservice(file_path: str, dfd) -> str:
    """Non-interactive: attribute a file to a service whose name is a path component."""
    if not tmp.tmp_config.has_option("DFD", "microservices"):
        return False
    microservices = ast.literal_eval(tmp.tmp_config["DFD"]["microservices"])
    names = {microservices[i]["name"] for i in microservices}
    for part in Path(file_path).parts:
        if part in names:
            return part
    return False
