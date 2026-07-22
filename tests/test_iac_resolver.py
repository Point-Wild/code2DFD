from technology_specific_extractors.aws_messaging.iac_resolver import (
    parse_localstack_setup,
    parse_env_file,
)

SETUP_SH = '''#!/usr/bin/env bash
TOPIC_NAME="${TOPIC_NAME:-hmac-256-events}"
QUEUE_NAME="${QUEUE_NAME:-hmac-256-events-worker}"
TOPIC_ARN=$(aws_local sns create-topic --name "$TOPIC_NAME" --query 'TopicArn' --output text)
QUEUE_URL=$(aws_local sqs create-queue --queue-name "$QUEUE_NAME" --query 'QueueUrl' --output text)
aws_local sns subscribe \\
  --topic-arn "$TOPIC_ARN" \\
  --protocol sqs \\
  --notification-endpoint "$QUEUE_ARN"
  export SNS_TOPIC_ARN='$TOPIC_ARN'
  export SQS_QUEUE_URL='$QUEUE_URL'
'''

ENV_FILE = '''AWS_REGION=us-east-1
SNS_TOPIC_ARN=arn:aws:sns:us-east-1:000000000000:hmac-256-events
SQS_QUEUE_URL=http://localhost:4566/000000000000/hmac-256-events-worker
'''


def test_parse_localstack_setup():
    result = parse_localstack_setup(SETUP_SH)
    assert result["topic_name"] == "hmac-256-events"
    assert result["queue_name"] == "hmac-256-events-worker"
    assert result["has_subscription"] is True


def test_parse_env_file():
    env = parse_env_file(ENV_FILE)
    assert env["SNS_TOPIC_ARN"].endswith("hmac-256-events")
    assert env["SQS_QUEUE_URL"].endswith("hmac-256-events-worker")
