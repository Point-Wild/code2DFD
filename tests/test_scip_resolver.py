import os
from core.scip_resolver import ScipIndex

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "scip_sample.json")


def test_occurrences_suffix_match_ignores_filename_collision():
    idx = ScipIndex.load(FIXTURE)
    occ = idx.occurrences("PublishCommand#")
    lines = sorted(o.line for o in occ)
    assert lines == [0, 18]
    assert all(o.rel_path == "services/publisher/src/sns.ts" for o in occ)


def test_occurrences_are_zero_for_bad_descriptor():
    idx = ScipIndex.load(FIXTURE)
    assert idx.occurrences("NoSuchSymbol#") == []


def test_send_sites_follows_instance_to_call_site():
    idx = ScipIndex.load(FIXTURE)
    sites = idx.send_sites("SNSClient")
    assert len(sites) == 1
    assert sites[0].rel_path == "services/publisher/src/sns.ts"
    assert sites[0].line == 17


def test_send_sites_ignores_import_line_module_symbol_collision():
    """Regression: the import-line SNSClient type-ref + whole-file module def on line 0
    must NOT be followed to the module's cross-file import in index.ts. Only the real
    `new SNSClient()` constructor on line 2 seeds instance-following."""
    idx = ScipIndex.load(FIXTURE)
    sites = idx.send_sites("SNSClient")
    assert all(s.rel_path == "services/publisher/src/sns.ts" for s in sites)
    assert not any(s.rel_path.endswith("index.ts") for s in sites)
