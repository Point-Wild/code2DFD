import os
from technology_specific_extractors.nodejs import node_extract

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "scip_sample.json")


def test_add_flow_and_read():
    flows = {}
    node_extract.add_flow(flows, "a", "b", ["restful_http"], [("k", "v")], "f.ts", 1, (0, 1))
    assert flows[0]["sender"] == "a" and flows[0]["receiver"] == "b"
    assert flows[0]["tagged_values"] == [("k", "v")]
    assert "restful_http" in flows[0]["stereotype_instances"]


def test_scip_index_from_env(monkeypatch):
    node_extract._TRIED = False
    node_extract._INDEX = None
    monkeypatch.setenv("SCIP_INDEX_PATH", FIXTURE)
    idx = node_extract.scip_index()
    assert idx is not None
    assert idx.occurrences("PublishCommand#")
    node_extract._TRIED = False
    node_extract._INDEX = None


class _FakeOcc:
    def __init__(self, rel_path, line, span):
        self.rel_path, self.line, self.span = rel_path, line, span


class _FakeIndex:
    """Minimal SCIP index stub: returns preset occurrences per descriptor."""
    def __init__(self, occ_by_descriptor):
        self._occ = occ_by_descriptor

    def send_sites(self, client_class):
        return []

    def occurrences(self, descriptor):
        return self._occ.get(descriptor, [])


def test_usage_sites_falls_back_to_grep_when_scip_has_no_match(monkeypatch):
    """Regression: an index that lacks the descriptor (e.g. a package moniker like
    `axios`) must degrade to grep, not silently return nothing."""
    monkeypatch.setattr(node_extract, "scip_index", lambda: _FakeIndex({}))
    monkeypatch.setattr(node_extract.fi, "search_keywords",
                        lambda kw: {0: {"path": "services/x/a.ts",
                                        "content": ["import axios from 'axios'", "axios.get('/y')"]}})
    monkeypatch.setattr(node_extract.tech_sw, "detect_microservice", lambda p, d: "x")
    sites = node_extract.usage_sites(None, "axios", descriptor_suffix="")
    assert sites, "expected grep fallback to find the usage"
    assert sites[0][0] == "x" and sites[0][1] == "services/x/a.ts"


def test_usage_sites_prefers_scip_and_skips_grep_when_index_matches(monkeypatch):
    """Guard: when the index resolves the descriptor, grep must NOT run."""
    idx = _FakeIndex({"PublishCommand#": [_FakeOcc("services/x/a.ts", 5, (0, 3))]})
    monkeypatch.setattr(node_extract, "scip_index", lambda: idx)
    grep_called = {"hit": False}

    def _boom(kw):
        grep_called["hit"] = True
        return {}

    monkeypatch.setattr(node_extract.fi, "search_keywords", _boom)
    monkeypatch.setattr(node_extract.tech_sw, "detect_microservice", lambda p, d: "x")
    sites = node_extract.usage_sites(None, "PublishCommand")
    assert sites[0][1] == "services/x/a.ts" and sites[0][2] == 5
    assert grep_called["hit"] is False, "grep must not run when SCIP resolves the descriptor"
