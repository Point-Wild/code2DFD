"""HTTP ingress extractor: express / fastify / koa route registrations become an
external `user:<service>` entrypoint node -> service edge, tagged with the routes."""
import re

import core.file_interaction as fi
import core.technology_switch as tech_sw
import technology_specific_extractors.nodejs.node_extract as nx

# SCIP class#method descriptors for express route registration
_ROUTE_DESCRIPTORS = ["IRouter#post", "IRouter#get", "IRouter#put", "IRouter#delete",
                      "IRouter#patch", "Application#post", "Application#get",
                      "Application#put", "Application#delete", "Application#patch"]
# grep fallback keywords
_ROUTE_KW = [".post(", ".get(", ".put(", ".delete(", ".patch("]
_QUOTED = re.compile(r"""['"]([^'"]+)['"]""")


def _routes_by_service(dfd):
    routes = {}  # service -> [(rel_path, line, span, path_str)]
    index = nx.scip_index()
    if index is not None:
        for desc in _ROUTE_DESCRIPTORS:
            for o in index.occurrences(desc):
                svc = tech_sw.detect_microservice(o.rel_path, dfd)
                if not svc:
                    continue
                routes.setdefault(svc, []).append(
                    (o.rel_path, o.line, o.span, nx.string_arg_on_line(o.rel_path, o.line)))
        return routes
    for kw in _ROUTE_KW:
        for f in fi.search_keywords(kw).values():
            svc = tech_sw.detect_microservice(f["path"], dfd)
            if not svc:
                continue
            for i, line in enumerate(f["content"]):
                if kw in line:
                    m = _QUOTED.search(line)
                    routes.setdefault(svc, []).append((f["path"], i, (0, 0), m.group(1) if m else None))
    return routes


def set_information_flows(dfd):
    flows = nx.read_flows()
    for service, hits in _routes_by_service(dfd).items():
        paths = sorted({h[3] for h in hits if h[3]})
        node = f"user:{service}"
        nx.register_external(node, ["entrypoint", "external_entity"], hits[0][0])
        nx.add_flow(flows, node, service, ["restful_http", "entrypoint"],
                    [("Routes", ", ".join(paths) or "unknown")],
                    hits[0][0], hits[0][1], hits[0][2])
    nx.write_flows(flows)
    return flows
