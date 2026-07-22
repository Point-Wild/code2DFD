"""kafkajs broker extractor: producer.send({topic}) / consumer.subscribe({topic}),
matched producer->consumer on topic (mirrors the SNS/SQS matcher). Guarded to run only
if `kafkajs` is imported (clean no-op elsewhere). Validated via unit tests on `match_topics`."""
import core.file_interaction as fi
import core.technology_switch as tech_sw
import technology_specific_extractors.nodejs.node_extract as nx


def _uses_kafkajs():
    return len(fi.search_keywords("kafkajs")) > 0


def _endpoints(dfd, method_kw):
    """[(service, topic, rel_path, line, span)] for lines calling `.<method_kw>(`."""
    out = []
    for f in fi.search_keywords(method_kw).values():
        service = tech_sw.detect_microservice(f["path"], dfd)
        for i, line in enumerate(f["content"]):
            if method_kw in line:
                m = nx.re.search(r"""topic\s*:\s*['"]([^'"]+)['"]""", line)
                topic = m.group(1) if m else nx.string_arg_on_line(f["path"], i)
                out.append((service, topic, f["path"], i, (0, 0)))
    return out


def match_topics(producers, consumers):
    """[(producer_service, consumer_service, topic)] where a producer topic == a consumer topic.
    producers/consumers are iterables of (service, topic, ...)."""
    flows = []
    for ps, pt, *_ in producers:
        for cs, ct, *_ in consumers:
            if pt and pt == ct:
                flows.append((ps, cs, pt))
    return flows


def set_information_flows(dfd):
    flows = nx.read_flows()
    if not _uses_kafkajs():
        return flows
    producers = _endpoints(dfd, "producer.send")
    consumers = _endpoints(dfd, "consumer.subscribe")
    for ps, cs, topic in match_topics(producers, consumers):
        node = f"kafka:{topic}"
        nx.register_external(node, ["message_broker"], "kafkajs")
        if ps:
            nx.add_flow(flows, ps, node, ["message_producer_kafka", "restful_http"],
                        [("Producer Topic", topic)], "kafkajs", 0, (0, 0))
        if cs:
            nx.add_flow(flows, node, cs, ["message_consumer_kafka", "restful_http"],
                        [("Consumer Topic", topic)], "kafkajs", 0, (0, 0))
    nx.write_flows(flows)
    return flows
