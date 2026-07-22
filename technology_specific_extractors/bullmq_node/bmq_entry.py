"""BullMQ broker extractor: `new Queue("q")` (+ .add) producer / `new Worker("q", ...)`
consumer, matched producer->consumer on the queue name. BullMQ is the dominant Node/TS
job-queue library (Redis-backed) in enterprise monorepos (e.g. novu). Guarded to run only
if `bullmq` is imported (clean no-op elsewhere). Validated via unit tests on `match_queues`.

Note: some codebases wrap `new Queue`/`new Worker` in a shared base class in a library
package; there the constructor call lives in a lib (not a service) and won't be attributed
to a producer/consumer service. That is the same shared-abstraction limitation as the other
node brokers, not specific to BullMQ."""
import re

import core.file_interaction as fi
import core.technology_switch as tech_sw
import technology_specific_extractors.nodejs.node_extract as nx

# First quoted arg to `new Queue(...)` / `new Worker(...)`, tolerating a TS generic
# (`new Queue<JobData>("q")`). Deliberately does NOT match `new QueueEvents(...)` /
# `new QueueScheduler(...)` — those aren't producer queues.
_QUEUE_RE = re.compile(r"""new\s+Queue(?:<[^>]*>)?\s*\(\s*['"]([^'"]+)['"]""")
_WORKER_RE = re.compile(r"""new\s+Worker(?:<[^>]*>)?\s*\(\s*['"]([^'"]+)['"]""")


def _uses_bullmq():
    return len(fi.search_keywords("bullmq")) > 0


def _endpoints(dfd, keyword, pattern):
    """[(service, queue, rel_path, line, span)] for lines where `pattern` (group(1)=queue name)
    matches; `keyword` narrows the file scan via grep (no trailing '(' — see search_keywords)."""
    out = []
    for f in fi.search_keywords(keyword).values():
        service = tech_sw.detect_microservice(f["path"], dfd)
        for i, line in enumerate(f["content"]):
            m = pattern.search(line)
            if m:
                out.append((service, m.group(1), f["path"], i, (0, 0)))
    return out


def match_queues(producers, consumers):
    """[(producer_service, consumer_service, queue)] where a producer queue == a consumer queue.
    producers/consumers are iterables of (service, queue, ...)."""
    flows = []
    for ps, pq, *_ in producers:
        for cs, cq, *_ in consumers:
            if pq and pq == cq:
                flows.append((ps, cs, pq))
    return flows


def set_information_flows(dfd):
    flows = nx.read_flows()
    if not _uses_bullmq():
        return flows
    producers = _endpoints(dfd, "new Queue", _QUEUE_RE)
    consumers = _endpoints(dfd, "new Worker", _WORKER_RE)
    for ps, cs, queue in match_queues(producers, consumers):
        node = f"bullmq:{queue}"
        nx.register_external(node, ["message_broker"], "bullmq")
        if ps:
            nx.add_flow(flows, ps, node, ["message_producer_bullmq", "restful_http"],
                        [("Producer Queue", queue)], "bullmq", 0, (0, 0))
        if cs:
            nx.add_flow(flows, node, cs, ["message_consumer_bullmq", "restful_http"],
                        [("Consumer Queue", queue)], "bullmq", 0, (0, 0))
    nx.write_flows(flows)
    return flows
