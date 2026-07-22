"""Unit tests for the pure cores of the fixture-only extractors (HTTP client, DB,
kafkajs, amqplib) — these do not fire on the synthetic repo, so their logic is
validated here in isolation."""
from technology_specific_extractors.http_client.hcl_entry import resolve_target
from technology_specific_extractors.databases_node.dbn_entry import db_kind
from technology_specific_extractors.kafka_node.kfn_entry import match_topics
from technology_specific_extractors.rabbitmq_node.rmn_entry import match_queues


def test_resolve_target_known_service_vs_external():
    names = ["worker", "billing"]
    assert resolve_target("http://worker:4000/x", names) == "worker"
    assert resolve_target("https://api.stripe.com/charge", names) == "external-website"
    assert resolve_target(None, names) == "external-website"


def test_db_kind_mapping():
    assert db_kind("MongoClient") == "mongodb"
    assert db_kind("createPool") == "mysql"
    assert db_kind("PrismaClient") == "database"
    assert db_kind("SNSClient") is None


def test_kafka_match_topics():
    producers = [("publisher", "orders")]
    consumers = [("worker", "orders"), ("audit", "other")]
    assert match_topics(producers, consumers) == [("publisher", "worker", "orders")]


def test_rabbitmq_match_queues():
    producers = [("api", "jobs")]
    consumers = [("runner", "jobs")]
    assert match_queues(producers, consumers) == [("api", "runner", "jobs")]
