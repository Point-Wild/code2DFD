from technology_specific_extractors.nodejs.npm_entry import service_dirs_from_scripts

PACKAGE_JSON = '''{
  "name": "breakpoint-synthetic-sns-pub-sqs-worker",
  "scripts": {
    "publisher:dev": "tsx watch --env-file-if-exists=services/publisher/.env services/publisher/src/index.ts",
    "worker:dev": "tsx watch --env-file-if-exists=services/worker/.env services/worker/src/index.ts",
    "typecheck": "tsc --noEmit"
  }
}'''


def test_service_dirs_from_scripts_finds_publisher_and_worker():
    result = service_dirs_from_scripts(PACKAGE_JSON)
    assert result == {"publisher": "services/publisher", "worker": "services/worker"}
