# File: `.agent-skills/tradepilot-devops-safety/SKILL.md`

# TradePilot DevOps Safety

## Purpose

Protect TradePilot AI development, testing, deployment, and operational environments from destructive commands, port conflicts, shared-resource collisions, secret exposure, and accidental production mutation.

This skill is mandatory for tasks involving:

* Docker;
* Docker Compose;
* local production-like environments;
* VPS deployment;
* container deployment;
* databases;
* persistent volumes;
* evidence storage;
* environment variables;
* gateways;
* health checks;
* service restarts;
* migrations;
* infrastructure cleanup.

---

## When to Use

Use this skill when a task requires any of the following:

* creating or modifying Docker Compose files;
* starting, stopping, rebuilding, or restarting containers;
* creating isolated local test infrastructure;
* configuring PostgreSQL;
* configuring evidence storage;
* checking or assigning ports;
* creating Docker volumes or networks;
* changing environment variables;
* running migrations;
* diagnosing container health;
* testing production-like behavior;
* changing deployment configuration;
* operating on a VPS that hosts multiple projects.

---

## Required Context

Before making changes, read:

* `.agent-skills/shared/PROJECT_INVARIANTS.md`;
* `.agent-skills/tradepilot-product-guardian/SKILL.md`;
* `.agent-skills/tradepilot-repository-navigator/SKILL.md`;
* current Docker Compose files;
* environment examples;
* deployment documentation;
* health-check definitions;
* storage configuration;
* current service and port topology.

Do not assume the machine is dedicated to TradePilot AI.

---

## Source of Truth

Identify the authoritative source for:

* Compose project name;
* service names;
* exposed and internal ports;
* database connection strings;
* evidence-storage paths;
* volume names;
* network names;
* provider configuration;
* gateway routes;
* migration commands;
* health-check endpoints;
* production environment values.

Environment example files are documentation, not proof of active runtime configuration.

Never print secret values while inspecting configuration.

---

## Mandatory Workflow

### 1. Classify the Environment

Explicitly identify the target environment:

* local development;
* local isolated production-like smoke test;
* shared VPS;
* staging;
* production;
* CI.

Do not reuse production infrastructure for local testing.

---

### 2. Inspect Existing Infrastructure

Before starting services, inspect:

* active containers;
* Compose projects;
* bound host ports;
* existing networks;
* existing volumes;
* available disk space when relevant;
* target database names;
* target evidence-storage paths;
* current Git branch and working tree;
* existing environment files.

Prefer read-only inspection commands.

---

### 3. Define Isolation Boundaries

For local production-like testing, define unique values for:

* Compose project name;
* host ports;
* PostgreSQL database;
* PostgreSQL user when practical;
* Docker volumes;
* Docker network;
* evidence-storage root;
* temporary test artifacts;
* environment file.

Recommended naming pattern:

```text
tradepilot-smoke
tradepilot_smoke_db
tradepilot-smoke-postgres-data
tradepilot-smoke-evidence
tradepilot-smoke-network
```

Do not reuse production volume names.

---

### 4. Perform Port Collision Checks

Before binding a host port:

* inspect whether it is already in use;
* identify the owning process or container;
* choose an unused alternative when necessary;
* document the selected mapping.

Do not stop unrelated services to free a preferred port.

Internal container ports may remain consistent with production architecture, while host ports should remain isolated.

---

### 5. Validate Environment Variables

Classify variables into:

* required;
* optional;
* secret;
* local-only;
* production-only;
* derived.

Validate that:

* required variables are present;
* the database URL points to the isolated database;
* evidence paths point to isolated storage;
* provider configuration uses the intended Gemini model;
* frontend and gateway URLs match the selected ports;
* no production database or storage path is referenced;
* secrets are not committed;
* `.env.example` contains placeholders only.

Never copy real credentials into tracked files.

---

### 6. Start Services Safely

Prefer targeted commands:

```text
docker compose \
  -p <isolated-project> \
  -f <compose-file> \
  up -d <services>
```

After startup, inspect:

* container status;
* health status;
* startup logs;
* network attachment;
* volume attachment;
* actual port mappings.

Do not assume a running container is a healthy application.

---

### 7. Use Targeted Restarts

When configuration or code changes affect only selected services:

* rebuild or restart only those services;
* preserve healthy unrelated services;
* avoid restarting shared infrastructure unnecessarily.

Examples:

* frontend-only change: rebuild frontend;
* worker-only change: restart worker;
* backend environment change: restart backend and dependent worker if required;
* gateway route change: restart gateway.

---

### 8. Protect Persistent Data

Before operations affecting volumes or databases:

* confirm the exact target;
* confirm the environment;
* confirm the resource is isolated;
* determine whether data preservation is required.

Never delete:

* volumes through broad wildcard commands;
* shared volumes;
* production database volumes;
* evidence-storage volumes;
* shared Docker networks.

---

### 9. Run Migrations Safely

Before running a migration:

* inspect pending migrations;
* confirm the target database URL;
* ensure the database is isolated or explicitly approved;
* assess backward compatibility;
* record the current migration revision.

After the migration:

* verify the applied revision;
* run relevant database tests;
* confirm application health.

Do not generate or apply unrelated migrations during a smoke-test task.

---

### 10. Shut Down and Clean Up Safely

For isolated local smoke-test infrastructure:

```text
docker compose \
  -p <isolated-project> \
  -f <compose-file> \
  down
```

Delete volumes only when:

* the task explicitly requires complete removal;
* the volume names have been verified as isolated;
* no test evidence needs to be preserved.

Prefer leaving isolated volumes in place when repeated testing is expected.

---

## Prohibited Actions

Do not run:

```text
docker system prune
docker system prune -a
docker volume prune
docker network prune
docker container prune
docker rm -f $(docker ps -aq)
docker volume rm $(docker volume ls -q)
```

Do not:

* stop unrelated containers;
* reuse production databases for testing;
* reuse production evidence storage;
* overwrite production environment files;
* expose secrets in logs or reports;
* bind ports without checking collisions;
* delete shared networks;
* execute broad cleanup commands;
* modify host firewall rules unless explicitly required and approved;
* mutate production data directly;
* claim isolation without verifying actual runtime configuration.

---

## Safety Validation Checklist

### Before Startup

Confirm:

* environment identified;
* Compose project name is unique;
* host ports checked;
* database isolated;
* evidence storage isolated;
* volumes isolated;
* network isolated;
* secrets remain untracked;
* no production URL is referenced.

### After Startup

Confirm:

* expected services are running;
* health checks pass;
* expected ports are bound;
* the correct database is connected;
* the correct evidence path is mounted;
* provider configuration is visible without exposing secrets;
* unrelated projects remain unaffected.

### After Completion

Confirm:

* services are left in the intended state;
* temporary files are documented;
* Git working tree is checked;
* no secret files were added;
* no unrelated infrastructure changed.

---

## Escalation Rules

Stop and request direction when:

* an environment appears to reference production;
* a target port belongs to an unknown critical service;
* volume ownership is unclear;
* migration compatibility is uncertain;
* the only proposed solution requires destructive cleanup;
* production and local credentials cannot be distinguished;
* a shared infrastructure dependency would be modified;
* the task requires direct production data mutation.

Present safe alternatives and explain their consequences.

---

## Expected Pre-Implementation Output

Before editing or executing infrastructure commands, report:

```text
Environment:
Existing infrastructure:
Isolation plan:
Port plan:
Database target:
Evidence-storage target:
Environment-file plan:
Services affected:
Safety risks:
Expected contract impact:
```

---

## Expected Completion Output

Use:

```text
.agent-skills/shared/EXIT_REPORT_TEMPLATE.md
```

Additionally report:

* Compose project name;
* Compose file;
* host port mappings;
* database name;
* volume names;
* Docker network;
* evidence-storage path;
* service health;
* migration status;
* cleanup status;
* impact on unrelated projects;
* exact infrastructure commands executed;
* final Git working-tree status.

---

## Contract Impact Requirement

Every task must explicitly classify its impact as one of:

* no contract change;
* backward-compatible infrastructure change;
* breaking infrastructure change;
* environment-only change;
* deployment-only change;
* test-only change.

Do not omit this section.

---

## Verification Evidence Requirement

Every infrastructure verification claim must include its evidence.

Examples:

```text
Claim: PostgreSQL is healthy
Evidence: docker compose ps and successful database readiness check
```

```text
Claim: Evidence storage is isolated
Evidence: resolved container mount and host path inspection
```

```text
Claim: No unrelated project was affected
Evidence: before-and-after container and port comparison
```

Do not report only `PASS` without the supporting command or observation.

---

## Residual Risk Requirement

Do not default to:

```text
Risks: None
```

Instead distinguish:

* blocking risks;
* non-blocking residual risks;
* untested operational behavior;
* environment-specific uncertainty.

Use:

```text
No blocking risks identified.
```

only when justified, followed by any realistic residual risks.

---

## Exit Criteria

This skill is complete when:

* no production resource was used unintentionally;
* all local test resources are isolated;
* no unrelated service was stopped or modified;
* all bound ports were checked;
* secrets remain protected;
* service health was verified;
* cleanup actions were targeted and safe;
* infrastructure state is documented;
* verification claims include evidence;
* residual risks are reported realistically.
