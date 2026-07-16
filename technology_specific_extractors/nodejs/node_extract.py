"""Shared machinery for Node/TS extractors: SCIP-first (grep fallback) symbol
resolution + DFD emit helpers. Extractors stay thin and uniform."""
import ast
import os
import re

import core.file_interaction as fi
import core.technology_switch as tech_sw
import tmp.tmp as tmp
import output_generators.traceability as traceability
from output_generators.logger import logger
from technology_specific_extractors.aws_messaging.scip_resolver import ScipIndex

_INDEX = None
_TRIED = False


def scip_index():
    global _INDEX, _TRIED
    if _TRIED:
        return _INDEX
    _TRIED = True
    path = os.environ.get("SCIP_INDEX_PATH")
    if path and os.path.isfile(path):
        try:
            _INDEX = ScipIndex.load(path)
        except Exception as e:
            logger.info(f"SCIP index load failed ({e}); grep fallback")
            _INDEX = None
    return _INDEX


def usage_sites(dfd, command_class, client_class=None, descriptor_suffix="#"):
    """[(service, rel_path, line, span)] where command_class is used.

    `descriptor_suffix` is "#" for classes (default) or "" for free functions
    (e.g. node:crypto's createHmac, which has no class descriptor)."""
    index = scip_index()
    if index is not None:
        by_file = {}
        if client_class:
            for s in index.send_sites(client_class):
                by_file.setdefault(s.rel_path, s)
        cmd_by_file = {}
        for o in index.occurrences(command_class + descriptor_suffix):
            cur = cmd_by_file.get(o.rel_path)
            if cur is None or o.line > cur.line:
                cmd_by_file[o.rel_path] = o
        out = []
        for rel_path in sorted(set(by_file) | set(cmd_by_file)):
            occ = by_file.get(rel_path) or cmd_by_file[rel_path]
            out.append((tech_sw.detect_microservice(rel_path, dfd), rel_path, occ.line, occ.span))
        return out
    out = []
    for f in fi.search_keywords(command_class).values():
        service = tech_sw.detect_microservice(f["path"], dfd)
        for i, line in enumerate(f["content"]):
            if command_class in line:
                m = re.search(re.escape(command_class), line)
                out.append((service, f["path"], i, m.span() if m else (0, 0)))
                break
    return out


def read_flows():
    if tmp.tmp_config.has_option("DFD", "information_flows"):
        return ast.literal_eval(tmp.tmp_config["DFD"]["information_flows"])
    return dict()


def write_flows(flows):
    tmp.tmp_config.set("DFD", "information_flows", str(flows).replace("%", "%%"))


def add_flow(flows, sender, receiver, stereotypes, tags, file, line, span):
    id_ = max(flows.keys(), default=-1) + 1
    flows[id_] = {"sender": sender, "receiver": receiver,
                  "stereotype_instances": list(stereotypes), "tagged_values": list(tags)}
    traceability.add_trace({"item": f"{sender} -> {receiver}", "file": file,
                            "line": line, "span": str(span)})
    return id_


def register_external(name, stereotypes, file):
    if tmp.tmp_config.has_option("DFD", "external_components"):
        ext = ast.literal_eval(tmp.tmp_config["DFD"]["external_components"])
    else:
        ext = dict()
    if not any(ext[i]["name"] == name for i in ext):
        id_ = max(ext.keys(), default=-1) + 1
        ext[id_] = {"name": name, "type": "external_component",
                    "stereotype_instances": list(stereotypes), "tagged_values": []}
        traceability.add_trace({"item": name, "file": file, "line": "heuristic", "span": "heuristic"})
    tmp.tmp_config.set("DFD", "external_components", str(ext).replace("%", "%%"))


def annotate_service(name, stereotype, tag, file, line, span):
    if not tmp.tmp_config.has_option("DFD", "microservices"):
        return
    ms = ast.literal_eval(tmp.tmp_config["DFD"]["microservices"])
    for k in ms:
        if ms[k]["name"] == name:
            ms[k].setdefault("stereotype_instances", [])
            if stereotype not in ms[k]["stereotype_instances"]:
                ms[k]["stereotype_instances"].append(stereotype)
            if tag:
                ms[k].setdefault("tagged_values", []).append(tag)
            traceability.add_trace({"parent_item": name, "item": stereotype,
                                    "file": file, "line": line, "span": str(span)})
    tmp.tmp_config.set("DFD", "microservices", str(ms).replace("%", "%%"))


def string_arg_on_line(rel_path, line):
    """First quoted string literal on the given 0-indexed line of rel_path, or None."""
    for f in fi.get_file_as_lines(os.path.basename(rel_path)).values():
        if f["path"] == rel_path and 0 <= line < len(f["content"]):
            m = re.search(r"""['"]([^'"]+)['"]""", f["content"][line])
            return m.group(1) if m else None
    return None
