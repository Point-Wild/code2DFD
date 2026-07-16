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
