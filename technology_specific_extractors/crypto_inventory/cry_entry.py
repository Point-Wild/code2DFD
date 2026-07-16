"""Crypto inventory: annotate each service with the crypto primitives it uses.

Seed of the crypto/moat layer — records WHICH primitive (and algorithm) each service
uses so a blast-radius query can flag legacy ones (e.g. md5) for migration.
Annotation-only: returns information_flows unchanged."""
import os
import re

import core.file_interaction as fi
import technology_specific_extractors.nodejs.node_extract as nx

_PRIMS = ["createHmac", "createHash", "createCipheriv", "createDecipheriv",
          "createSign", "createVerify"]


def _algo_for(rel_path, prim):
    """The algorithm string passed to `prim(...)` in rel_path, e.g. createHmac("md5"...) -> md5."""
    call = re.compile(re.escape(prim) + r"""\(\s*['"]([^'"]+)['"]""")
    for f in fi.get_file_as_lines(os.path.basename(rel_path)).values():
        if f["path"] != rel_path:
            continue
        for line in f["content"]:
            m = call.search(line)
            if m:
                return m.group(1)
    return None


def set_information_flows(dfd):
    flows = nx.read_flows()  # annotation-only; unchanged
    for prim in _PRIMS:
        for service, rel_path, line, span in nx.usage_sites(dfd, prim, descriptor_suffix=""):
            if not service:
                continue
            algo = _algo_for(rel_path, prim)
            nx.annotate_service(service, "crypto",
                                ("Crypto Primitive", f"{prim}({algo})" if algo else prim),
                                rel_path, line, span)
    for service, rel_path, line, span in nx.usage_sites(dfd, "jsonwebtoken", descriptor_suffix=""):
        if service:
            nx.annotate_service(service, "crypto", ("Crypto Primitive", "jwt"), rel_path, line, span)
    nx.write_flows(flows)
    return flows
