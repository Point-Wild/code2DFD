"""AWS service extractor: SecretsManager / KMS / S3 / DynamoDB.

Each (service, resource) becomes an external node + a call edge. The SecretsManager
node is keyed by the SECRET NAME, so two services reading the same secret collapse to
one node -> the shared-key coupling that matters for crypto blast radius.
"""
import os
import re

import core.file_interaction as fi
import technology_specific_extractors.nodejs.node_extract as nx

_QUOTED = re.compile(r"""['"]([^'"]+)['"]""")

# (client_class, command_class, node_prefix, resource_keywords, default_resource)
_SERVICES = [
    ("SecretsManagerClient", "GetSecretValueCommand", "aws-secretsmanager",
     ["SECRET_NAME", "SecretId", "secretName"], "secret"),
    ("KMSClient", "EncryptCommand", "aws-kms", ["KeyId", "keyId", "KEY_ID"], "key"),
    ("KMSClient", "DecryptCommand", "aws-kms", ["KeyId", "keyId", "KEY_ID"], "key"),
    ("S3Client", "GetObjectCommand", "aws-s3", ["Bucket", "BUCKET"], "bucket"),
    ("S3Client", "PutObjectCommand", "aws-s3", ["Bucket", "BUCKET"], "bucket"),
    ("DynamoDBClient", "GetItemCommand", "aws-dynamodb", ["TableName", "TABLE"], "table"),
    ("DynamoDBClient", "PutItemCommand", "aws-dynamodb", ["TableName", "TABLE"], "table"),
]


def _resource_id(rel_path, keywords, default):
    """The resource identifier literal (secret name / bucket / table), read from a line
    that mentions one of `keywords`. Skips npm-package strings (imports)."""
    for f in fi.get_file_as_lines(os.path.basename(rel_path)).values():
        if f["path"] != rel_path:
            continue
        for line in f["content"]:
            if any(k in line for k in keywords):
                m = _QUOTED.search(line)
                if m and not m.group(1).startswith("@") and "aws-sdk" not in m.group(1):
                    return m.group(1)
    return default


def set_information_flows(dfd):
    flows = nx.read_flows()
    for client_class, command_class, prefix, kw, default in _SERVICES:
        for service, rel_path, line, span in nx.usage_sites(dfd, command_class, client_class):
            if not service:
                continue
            resource = _resource_id(rel_path, kw, default)
            node = f"{prefix}:{resource}"
            nx.register_external(node, ["aws_service"], rel_path)
            nx.add_flow(flows, service, node, ["restful_http", "aws_service_call"],
                        [("AWS Service", prefix.split("-", 1)[-1]), ("Resource", resource)],
                        rel_path, line, span)
    nx.write_flows(flows)
    return flows
