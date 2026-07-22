import re

_ASSIGN_RE = re.compile(r'^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.+?)\s*$')


def _clean_value(raw: str) -> str:
    """Strips quotes and bash default-expansion, e.g. "${TOPIC_NAME:-hmac-256-events}" -> hmac-256-events."""
    v = raw.strip().strip('"').strip("'")
    m = re.search(r'\$\{[A-Za-z_][A-Za-z0-9_]*:-([^}]*)\}', v)
    if m:
        return m.group(1)
    return v


def parse_localstack_setup(text: str) -> dict:
    """Pure: extract topic name, queue name, and whether an SNS->SQS subscription exists."""
    topic_name = None
    queue_name = None
    for line in text.splitlines():
        m = _ASSIGN_RE.match(line)
        if m and m.group(1) == "TOPIC_NAME":
            topic_name = _clean_value(m.group(2))
        elif m and m.group(1) == "QUEUE_NAME":
            queue_name = _clean_value(m.group(2))
    has_subscription = ("sns subscribe" in text) or ("sns\n" in text and "subscribe" in text)
    return {
        "topic_name": topic_name,
        "queue_name": queue_name,
        "has_subscription": bool(has_subscription),
    }


def parse_env_file(text: str) -> dict:
    """Pure: parse KEY=VALUE lines into a dict, ignoring comments/blank lines."""
    env = dict()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = _ASSIGN_RE.match(line)
        if m:
            env[m.group(1)] = _clean_value(m.group(2))
    return env
