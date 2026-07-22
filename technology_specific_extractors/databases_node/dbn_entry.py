"""Node database-client extractor: pg / mysql2 / mongodb / redis / ORMs -> DB node + edge.
Not exercised by this repo (no DB); validated via unit tests on `db_kind`."""
import technology_specific_extractors.nodejs.node_extract as nx

# (client symbol, db kind) — distinctive symbols only, to avoid ambiguous matches
_DBS = [
    ("MongoClient", "mongodb"),
    ("createPool", "mysql"),
    ("createConnection", "mysql"),
    ("PrismaClient", "database"),
    ("Sequelize", "database"),
    ("DataSource", "database"),
    ("Redis", "redis"),
]


def db_kind(symbol):
    for sym, kind in _DBS:
        if sym == symbol:
            return kind
    return None


def set_information_flows(dfd):
    flows = nx.read_flows()
    for symbol, kind in _DBS:
        for service, rel_path, line, span in nx.usage_sites(dfd, symbol):
            if not service:
                continue
            node = f"database:{kind}"
            nx.register_external(node, ["database"], rel_path)
            nx.add_flow(flows, service, node, ["jdbc", "database"],
                        [("Database", kind)], rel_path, line, span)
    nx.write_flows(flows)
    return flows
