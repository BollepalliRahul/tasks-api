# Tasks API — FastAPI → Docker → AWS → CI/CD → CloudWatch

A small backend service, built and deployed the way a real one would be: containerized, provisioned with infrastructure-as-code, deployed automatically on every push, and monitored in production. This repo is the evidence trail for that whole pipeline — from `git push` to a live, observable service running in AWS.

**Live right now:** [http://34.200.217.107:8000/health](http://34.200.217.107:8000/health)

---

## Why this project exists

The core skill this demonstrates: taking code from a laptop to a running, monitored service in the cloud — safely and repeatably, without doing it by hand. Every piece here proves one part of that:

| Piece | What it proves |
|---|---|
| FastAPI app | A real backend service with a database, not just a script |
| Docker + docker-compose | The service runs identically anywhere, with its dependencies |
| Terraform | Cloud infrastructure is provisioned as reviewable code, not clicked together in a console |
| GitHub Actions | Every push to `main` deploys automatically — no manual SSH required |
| CloudWatch | The deployed service is actually watched, not just launched and forgotten |
| [Incident report](incident/INCIDENT.md) | A real failure was caused, detected (or in this case, *not* detected — see below), and resolved, with a documented root cause and follow-up plan |

---

## Architecture

```
 Developer laptop
       │  git push
       ▼
 GitHub (main branch)
       │  triggers on push
       ▼
 GitHub Actions ──── SSH ────▶  EC2 instance (AWS)
                                  ├── Docker: FastAPI container (tasks-api)
                                  └── Docker: Postgres container (db)
                                       ▲
                                       │ provisioned by
                                  Terraform (security group, IAM role, EC2, alarm)
                                       │
                                  CloudWatch (logs + StatusCheckFailed alarm → email)
```

---

## Tech stack

- **Backend:** FastAPI, SQLAlchemy, Pydantic
- **Database:** PostgreSQL 16 (Docker container)
- **Containerization:** Docker, docker-compose
- **Infrastructure:** Terraform (AWS EC2, security groups, IAM, CloudWatch alarms)
- **CI/CD:** GitHub Actions (SSH-based deploy on push to `main`)
- **Monitoring:** Amazon CloudWatch (Logs + Alarms via SNS email notification)

---

## API endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness + readiness check — confirms the app can reach its database |
| POST | `/tasks` | Create a task |
| GET | `/tasks` | List all tasks |
| GET | `/tasks/{id}` | Get a single task by ID |

---

## Run it locally

```bash
git clone https://github.com/BollepalliRahul/tasks-api.git
cd tasks-api
docker compose up --build
```

Then visit `http://localhost:8000/health`.

---

## Infrastructure

The `terraform/` folder provisions everything this app needs in AWS: a security group (firewall rules), an EC2 instance running the app via a self-configuring startup script, an IAM role so the instance can report to CloudWatch, and a CloudWatch alarm wired to an email notification.

```bash
cd terraform
terraform init
terraform apply -var="alert_email=you@example.com"
```

---

## CI/CD

`.github/workflows/deploy.yml` runs on every push to `main`: it SSHes into the EC2 instance, pulls the latest code, and rebuilds the containers. No manual deployment step required after the initial setup.

---

## Incident report

**[→ Read the full incident report](incident/INCIDENT.md)**

I deliberately stopped the API container on the live server to test the monitoring setup. The app went fully down — but the CloudWatch alarm, which only watches EC2 instance health, never triggered, because the underlying server stayed up the whole time. That gap — "infrastructure healthy" isn't the same as "product working" — is the real finding of the exercise, along with a concrete follow-up plan (an application-level health check, not just an instance-level one) to close it.

---

## Known tradeoffs

Built for a portfolio project, not production — flagging the gaps deliberately rather than leaving them to be discovered:

- **Database credentials are plaintext in `docker-compose.yml`.** Fine for local dev; a real deployment would pull these from AWS Secrets Manager or SSM Parameter Store instead.
- **The Terraform IAM user (`terraform-deployer`) uses `AdministratorAccess`.** Convenient for a learning project; a real team would scope this down to only the specific permissions Terraform actually needs (EC2, IAM, CloudWatch, SNS).
- **CloudWatch alarm is instance-level only** (see incident report above) — no application-level health check alarm yet.
- **Single EC2 instance, no load balancer or auto-scaling.** Fine for a demo; a production service would sit behind an ALB with health-check-based routing.

---

## What I'd add next

- An application-level health check (e.g. CloudWatch Synthetics or a scheduled Lambda hitting `/health`)
- Move secrets out of `docker-compose.yml` and into a secrets manager
- Scope the Terraform IAM user down from `AdministratorAccess` to least-privilege
- Add automated tests to the GitHub Actions workflow, run before deploy
