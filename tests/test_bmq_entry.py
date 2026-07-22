from technology_specific_extractors.bullmq_node.bmq_entry import (
    match_queues,
    _QUEUE_RE,
    _WORKER_RE,
)


def test_queue_regex_extracts_name():
    assert _QUEUE_RE.search('const q = new Queue("emails", { connection });').group(1) == "emails"
    assert _QUEUE_RE.search("new Queue('user-registration')").group(1) == "user-registration"
    # TS generic form: new Queue<JobData>("emails")
    assert _QUEUE_RE.search('new Queue<JobData>("emails")').group(1) == "emails"
    # QueueEvents / QueueScheduler are NOT producer queues
    assert _QUEUE_RE.search('new QueueEvents("emails")') is None


def test_worker_regex_extracts_name():
    assert _WORKER_RE.search('new Worker("emails", async (job) => {}, opts)').group(1) == "emails"
    assert _WORKER_RE.search('new Worker<JobData>("emails", processor)').group(1) == "emails"


def test_match_queues_joins_on_queue_name():
    producers = [("api", "emails", "a.ts", 1, (0, 0)), ("api", "sms", "a.ts", 2, (0, 0))]
    consumers = [("worker", "emails", "b.ts", 3, (0, 0))]
    assert match_queues(producers, consumers) == [("api", "worker", "emails")]


def test_match_queues_no_cross_when_names_differ():
    producers = [("api", "emails", "a.ts", 1, (0, 0))]
    consumers = [("worker", "notifications", "b.ts", 3, (0, 0))]
    assert match_queues(producers, consumers) == []
