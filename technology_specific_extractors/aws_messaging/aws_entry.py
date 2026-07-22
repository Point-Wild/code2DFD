import core.file_interaction as fi
from output_generators.logger import logger
from technology_specific_extractors.aws_messaging.iac_resolver import (
    parse_localstack_setup,
    parse_env_file,
)
import technology_specific_extractors.nodejs.node_extract as nx


def _load_iac():
    """Reads setup-localstack.sh + .env(.example) from the repo, returns resolved channel info."""
    setup = fi.get_file_as_lines("setup-localstack.sh")
    topic_name, queue_name, has_sub = None, None, False
    for f in setup.values():
        parsed = parse_localstack_setup("".join(f["content"]))
        topic_name = topic_name or parsed["topic_name"]
        queue_name = queue_name or parsed["queue_name"]
        has_sub = has_sub or parsed["has_subscription"]

    env = dict()
    for fname in (".env", ".env.example"):
        for f in fi.get_file_as_lines(fname).values():
            env.update(parse_env_file("".join(f["content"])))

    # Prefer explicit IaC names; fall back to env-derived tail if absent.
    if not topic_name and env.get("SNS_TOPIC_ARN"):
        topic_name = env["SNS_TOPIC_ARN"].split(":")[-1]
    if not queue_name and env.get("SQS_QUEUE_URL"):
        queue_name = env["SQS_QUEUE_URL"].rstrip("/").split("/")[-1]
    return {"topic_name": topic_name, "queue_name": queue_name, "has_subscription": has_sub}


def set_information_flows(dfd) -> dict:
    """Assembles publisher -> sns:<topic> -> sqs:<queue> -> worker."""
    flows = nx.read_flows()

    iac = _load_iac()
    topic = iac["topic_name"] or "unknown-topic"
    queue = iac["queue_name"] or "unknown-queue"
    topic_node = f"aws-sns:{topic}"
    queue_node = f"aws-sqs:{queue}"

    producers = nx.usage_sites(dfd, "PublishCommand", "SNSClient")
    consumers = nx.usage_sites(dfd, "ReceiveMessageCommand", "SQSClient")

    if producers:
        nx.register_external(topic_node, ["message_broker"], "IaC: setup-localstack.sh")
    if consumers:
        nx.register_external(queue_node, ["message_broker"], "IaC: setup-localstack.sh")

    for service, path, line, span in producers:
        if service:
            nx.add_flow(flows, service, topic_node, ["message_producer_sns", "restful_http"],
                        [("Producer Topic", topic)], path, line, span)

    if producers and consumers and iac["has_subscription"]:
        nx.add_flow(flows, topic_node, queue_node, ["message_broker", "restful_http"],
                    [("Subscription", f"{topic}->{queue}")],
                    "IaC: setup-localstack.sh", "sns subscribe", "(0, 0)")

    for service, path, line, span in consumers:
        if service:
            nx.add_flow(flows, queue_node, service, ["message_consumer_sqs", "restful_http"],
                        [("Consumer Queue", queue)], path, line, span)

    nx.write_flows(flows)
    logger.info(f"AWS SNS/SQS: {len(producers)} producers, {len(consumers)} consumers, topic={topic}, queue={queue}")
    return flows
