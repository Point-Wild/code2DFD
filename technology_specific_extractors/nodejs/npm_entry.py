import ast
import glob as _glob
import json
import os
import re
from pathlib import Path

import core.file_interaction as fi
import tmp.tmp as tmp
import output_generators.traceability as traceability

SERVICE_DIR_RE = re.compile(r"services/([^/\s'\"]+)/")
# pnpm-workspace.yaml list entries: `- "apps/*"` / `- 'libs/*'` / `- packages/*`
_PNPM_GLOB_RE = re.compile(r"""^\s*-\s*['"]?([^'"\n#]+?)['"]?\s*$""", re.M)


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


def workspace_globs(package_json_text: str, pnpm_workspace_text: str = "") -> list:
    """Pure: workspace package globs from a monorepo's `package.json` "workspaces"
    (array form `["apps/*"]` or object form `{"packages": ["apps/*"]}`) and/or a
    `pnpm-workspace.yaml` body. Enterprise TS monorepos (nx / turbo / pnpm) declare
    their packages this way rather than via the `services/<name>/` script convention.
    """
    globs = []
    try:
        ws = json.loads(package_json_text).get("workspaces")
    except json.JSONDecodeError:
        ws = None
    if isinstance(ws, list):
        globs.extend(ws)
    elif isinstance(ws, dict):
        globs.extend(ws.get("packages") or [])
    for match in _PNPM_GLOB_RE.finditer(pnpm_workspace_text or ""):
        g = match.group(1).strip()
        if g and g not in globs:
            globs.append(g)
    return globs


def is_service_package(rel_dir: str, has_dockerfile: bool = False) -> bool:
    """Pure heuristic: a workspace package is a deployable *service* (not a shared
    library) if it lives under an `apps/` or `services/` path, or ships a Dockerfile.
    Excludes `libs/*` / `packages/*` shared code.
    """
    segments = [p for p in Path(rel_dir).parts if p not in (".", "")]
    return ("apps" in segments) or ("services" in segments) or has_dockerfile


def _read_repo_file(root_dir: str, name: str) -> str:
    try:
        with open(os.path.join(root_dir, name), "r", encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    except OSError:
        return ""


def workspace_services(root_package_json_text: str, root_dir: str, pnpm_workspace_text: str = "") -> dict:
    """Expand workspace globs on disk (relative to root_dir) and keep the deployable
    service packages. Returns {service_name: rel_dir}. Service name is the package
    directory's basename (so it matches a path component during file attribution).
    """
    services = dict()
    for g in workspace_globs(root_package_json_text, pnpm_workspace_text):
        for pkg_dir in _glob.glob(os.path.join(root_dir, g)):
            if not os.path.isdir(pkg_dir):
                continue
            if not os.path.isfile(os.path.join(pkg_dir, "package.json")):
                continue
            rel = os.path.relpath(pkg_dir, root_dir)
            has_docker = os.path.isfile(os.path.join(pkg_dir, "Dockerfile"))
            if is_service_package(rel, has_docker):
                services[os.path.basename(pkg_dir.rstrip("/"))] = rel
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
    """Registers Node services in the tmp DFD, mirroring maven's set_microservices.

    Discovery order:
      1. Workspace packages (nx / turbo / pnpm monorepos: `apps/*`, `services/*`, ...).
      2. Fall back to the `services/<name>/` npm-script heuristic (single-package repos).
    """
    if tmp.tmp_config.has_option("DFD", "microservices"):
        microservices = ast.literal_eval(tmp.tmp_config["DFD"]["microservices"])
    else:
        microservices = dict()

    text, path = _root_package_json()
    if not text:
        return microservices

    # Resolve the repo root on disk so workspace globs can be expanded.
    local_path = tmp.tmp_config.get("Repository", "local_path") if tmp.tmp_config.has_option("Repository", "local_path") else None

    services, source = dict(), "package.json script"
    if local_path:
        root_dir = os.path.join(local_path, os.path.dirname(path))
        pnpm_text = _read_repo_file(root_dir, "pnpm-workspace.yaml")
        services = workspace_services(text, root_dir, pnpm_text)
        if services:
            source = "workspace"
    if not services:
        services = service_dirs_from_scripts(text)

    for name, service_dir in services.items():
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
        trace = {"item": name, "file": path, "line": f"heuristic ({source})",
                 "span": f"heuristic ({source})"}
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
