"""HTTP client extractor: axios / fetch / got calls become a service -> target REST flow.
Target resolves to a known service (name/host in the URL) else an `external-website` node.
Not exercised by this repo (no outbound HTTP); validated via unit tests on `resolve_target`."""
import ast

import tmp.tmp as tmp
import technology_specific_extractors.nodejs.node_extract as nx

_CLIENTS = ["axios", "fetch", "got"]


def _service_names():
    if not tmp.tmp_config.has_option("DFD", "microservices"):
        return []
    ms = ast.literal_eval(tmp.tmp_config["DFD"]["microservices"])
    return [ms[k]["name"] for k in ms]


def resolve_target(url, service_names):
    """Resolve an outbound URL to a known service (by name/host substring) or external."""
    if not url:
        return "external-website"
    for name in service_names:
        if name and name in url:
            return name
    return "external-website"


def set_information_flows(dfd):
    flows = nx.read_flows()
    names = _service_names()
    for client in _CLIENTS:
        for service, rel_path, line, span in nx.usage_sites(dfd, client, descriptor_suffix=""):
            if not service:
                continue
            url = nx.string_arg_on_line(rel_path, line)
            target = resolve_target(url, names)
            if target == "external-website":
                nx.register_external(target, ["external_website", "entrypoint", "exitpoint"], rel_path)
            nx.add_flow(flows, service, target, ["restful_http"],
                        [("URL", url or "unknown")], rel_path, line, span)
    nx.write_flows(flows)
    return flows
