from technology_specific_extractors.nodejs.npm_entry import (
    service_dirs_from_scripts,
    workspace_globs,
    is_service_package,
)

PACKAGE_JSON = '''{
  "name": "breakpoint-synthetic-sns-pub-sqs-worker",
  "scripts": {
    "publisher:dev": "tsx watch --env-file-if-exists=services/publisher/.env services/publisher/src/index.ts",
    "worker:dev": "tsx watch --env-file-if-exists=services/worker/.env services/worker/src/index.ts",
    "typecheck": "tsc --noEmit"
  }
}'''

# Enterprise monorepo shape (nx + pnpm workspaces), like novu.
WORKSPACE_PKG_JSON = '''{
  "name": "@acme/root",
  "workspaces": { "packages": ["apps/*", "libs/*", "packages/*", "enterprise/packages/*"] },
  "scripts": { "build:api": "nx build @acme/api-service" }
}'''

WORKSPACE_ARRAY_JSON = '{"workspaces": ["packages/*", "services/*"]}'

PNPM_WORKSPACE_YAML = '''packages:
  - "apps/*"
  - 'libs/*'
  - packages/*
'''


def test_service_dirs_from_scripts_finds_publisher_and_worker():
    result = service_dirs_from_scripts(PACKAGE_JSON)
    assert result == {"publisher": "services/publisher", "worker": "services/worker"}


def test_workspace_globs_object_form():
    assert workspace_globs(WORKSPACE_PKG_JSON) == ["apps/*", "libs/*", "packages/*", "enterprise/packages/*"]


def test_workspace_globs_array_form():
    assert workspace_globs(WORKSPACE_ARRAY_JSON) == ["packages/*", "services/*"]


def test_workspace_globs_from_pnpm_yaml():
    # No workspaces in package.json; globs come from pnpm-workspace.yaml.
    assert workspace_globs('{"name":"x"}', PNPM_WORKSPACE_YAML) == ["apps/*", "libs/*", "packages/*"]


def test_workspace_globs_none():
    assert workspace_globs('{"name":"x","scripts":{}}') == []


def test_is_service_package_apps_and_services_are_services():
    assert is_service_package("apps/api") is True
    assert is_service_package("apps/worker") is True
    assert is_service_package("services/publisher") is True


def test_is_service_package_libs_and_packages_are_not():
    assert is_service_package("libs/dal") is False
    assert is_service_package("packages/client") is False


def test_is_service_package_dockerfile_makes_it_a_service():
    # A package outside apps/services still counts if it ships a Dockerfile.
    assert is_service_package("packages/gateway", has_dockerfile=True) is True
