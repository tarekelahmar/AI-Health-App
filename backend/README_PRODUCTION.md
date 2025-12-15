# Production Readiness Notes (STEP L)

This repo is MVP-first. These are the minimum production steps so you don't ship a fragile toy.

## 1) Environments

**Dev (local):**

- local Postgres (Docker) OR RDS dev instance

- `ENABLE_LLM_TRANSLATION=false`

- `ENABLE_SCHEDULER=true` (optional)

**Staging:**

- same infra as prod

- seed synthetic demo users only

- feature flags enabled gradually

**Production:**

- private DB

- strict auth

- background workers separated from API

## 2) Health Endpoints

- `GET /api/v1/health/live`

- `GET /api/v1/health/ready` (checks DB)

Use these for load balancer checks and deploy gates.

## 3) Daily Loop Job

MVP uses APScheduler inside the API app (acceptable short-term).

Enable:

```
ENABLE_SCHEDULER=true
SCHEDULER_USER_IDS=1
SCHEDULER_CRON_HOUR=7
```

Production: move to a worker container + queue or cron.

## 4) DB Migrations

You must make Alembic authoritative for prod.

Right now some flows rely on `init_db()` creating tables. For prod:

1) Stop using `init_db()` to create schema automatically

2) Use `alembic upgrade head` in deploy pipeline

## 5) Safety

Safety is now enforced on:

- Intervention creation (blocks unsafe)

- Experiment start (blocks high-risk)

- Protocol safety summary (aggregates warnings)

Do not allow the LLM to create interventions directly.

## 6) Observability (next after STEP L)

- structured logs (JSON)

- request ids

- metrics: latency/error rate/job success

- tracing: OpenTelemetry

