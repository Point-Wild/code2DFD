"""amqplib broker extractor: channel.sendToQueue(q) / channel.consume(q), matched
producer->consumer on queue. Guarded to run only if `amqplib` is imported (no-op elsewhere).
Validated via unit tests on `match_queues`."""
import core.file_interaction as fi
import core.technology_switch as tech_sw
import technology_specific_extractors.nodejs.node_extract as nx


def _uses_amqplib():
    return len(fi.search_keywords("amqplib")) > 0


def _endpoints(dfd, method_kw):
    """[(service, queue, rel_path, line, span)] for lines calling `.<method_kw>(`."""
    out = []
    for f in fi.search_keywords(method_kw).values():
        service = tech_sw.detect_microservice(f["path"], dfd)
        for i, line in enumerate(f["content"]):
            if method_kw in line:
                queue = nx.string_arg_on_line(f["path"], i)
                out.append((service, queue, f["path"], i, (0, 0)))
    return out


def match_queues(producers, consumers):
    """[(producer_service, consumer_service, queue)] where producer queue == consumer queue."""
    flows = []
    for ps, pq, *_ in producers:
        for cs, cq, *_ in consumers:
            if pq and pq == cq:
                flows.append((ps, cs, pq))
    return flows


def set_information_flows(dfd):
    flows = nx.read_flows()
    if not _uses_amqplib():
        return flows
    producers = _endpoints(dfd, "sendToQueue")
    consumers = _endpoints(dfd, "consume")
    for ps, cs, queue in match_queues(producers, consumers):
        node = f"rabbitmq:{queue}"
        nx.register_external(node, ["message_broker"], "amqplib")
        if ps:
            nx.add_flow(flows, ps, node, ["message_producer_rabbitmq", "restful_http"],
                        [("Producer Queue", queue)], "amqplib", 0, (0, 0))
        if cs:
            nx.add_flow(flows, node, cs, ["message_consumer_rabbitmq", "restful_http"],
                        [("Consumer Queue", queue)], "amqplib", 0, (0, 0))
    nx.write_flows(flows)
    return flows
