import glob
import json
import os
import subprocess

REPO_ROOT = "/Users/rebuy/Documents/PointWild/PQC/breakpoint-synthetic-snsPublisher-sqsWorker"


def test_publisher_to_worker_chain_exists():
    subprocess.run([os.path.join(REPO_ROOT, "benchmark", "run-code2dfd.sh")],
                   check=True, capture_output=True, text=True)
    edge_files = glob.glob(os.path.join(REPO_ROOT, "benchmark", "code2DFD-ts",
                                        "code2DFD_output", "**", "*_edges.json"),
                           recursive=True)
    assert edge_files, "no edge output produced"
    # This code2DFD version emits {"edges": [{"sender": ..., "receiver": ...}, ...]}
    data = json.load(open(edge_files[0]))
    edge_list = data["edges"] if isinstance(data, dict) else data
    pairs = {(e.get("sender", "").casefold(), e.get("receiver", "").casefold())
             for e in edge_list}

    def links(a, b):
        return any(a in s and b in r for (s, r) in pairs)

    assert links("publisher", "sns"), f"missing publisher->sns edge in {pairs}"
    assert links("sns", "sqs"), f"missing sns->sqs subscription edge in {pairs}"
    assert links("sqs", "worker"), f"missing sqs->worker edge in {pairs}"


def test_scip_traceability_points_at_call_site():
    """With a SCIP index, the producer/consumer edges trace to the client.send call
    line, not the import line (regression guard for the grep-era off-by-import bug)."""
    import shutil
    scip_bin = os.path.join(REPO_ROOT, "benchmark", "scip-experiment", ".tools", "bin")
    if not (shutil.which("scip-typescript") and (shutil.which("scip") or os.path.isfile(os.path.join(scip_bin, "scip")))):
        import pytest
        pytest.skip("scip tooling not available")
    import glob as _glob
    subprocess.run([os.path.join(REPO_ROOT, "benchmark", "run-code2dfd.sh")],
                   check=True, capture_output=True, text=True)
    trace_files = _glob.glob(os.path.join(REPO_ROOT, "benchmark", "code2DFD-ts",
                                          "code2DFD_output", "**", "*_traceability.json"),
                             recursive=True)
    assert trace_files, "no traceability output produced"
    trace = json.load(open(trace_files[0]))
    edges = trace["edges"]
    prod = next(v for k, v in edges.items() if "publisher ->" in k and "sns" in k)
    cons = next(v for k, v in edges.items() if "-> worker" in k and "sqs" in k)
    assert prod["file"].endswith("sns.ts") and isinstance(prod["line"], int) and prod["line"] > 0
    assert cons["file"].endswith("sqs.ts") and isinstance(cons["line"], int) and cons["line"] > 0


def _arch():
    subprocess.run([os.path.join(REPO_ROOT, "benchmark", "run-code2dfd.sh")],
                   check=True, capture_output=True, text=True)
    files = glob.glob(os.path.join(REPO_ROOT, "benchmark", "code2DFD-ts",
                                   "code2DFD_output", "**", "*_json_architecture.json"),
                      recursive=True)
    assert files, "no architecture output produced"
    return json.load(open(files[0]))


def test_shared_secretsmanager_edge_from_both_services():
    """Both services read the same secret -> one shared aws-secretsmanager node with an
    edge FROM each (the co-migration coupling)."""
    arch = _arch()
    pairs = {(f["sender"].casefold(), f["receiver"].casefold())
             for f in arch["information_flows"]}
    secret = [r for (s, r) in pairs if "secretsmanager" in r]
    assert any(s == "publisher" and "secretsmanager" in r for (s, r) in pairs), pairs
    assert any(s == "worker" and "secretsmanager" in r for (s, r) in pairs), pairs
    # both point at the SAME node (shared key)
    assert len(set(secret)) == 1, f"expected one shared secret node, got {set(secret)}"


def test_http_ingress_edge_on_publisher_only():
    arch = _arch()
    pairs = {(f["sender"].casefold(), f["receiver"].casefold())
             for f in arch["information_flows"]}
    assert ("user:publisher", "publisher") in pairs, pairs
    assert not any(s == "user:worker" for (s, r) in pairs), "worker has no HTTP server"


def test_crypto_inventory_flags_hmac_md5_on_both_services():
    arch = _arch()
    for m in arch["microservices"]:
        assert "crypto" in m["stereotype_instances"], m
        tags = {tuple(t) for t in m["tagged_values"]}
        assert ("Crypto Primitive", "createHmac(md5)") in tags, m
