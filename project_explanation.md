# Base Image Automation Agent - Project Explanation

## Overview

The **Base Image Automation Agent** is a Python-based tool designed to automate base image compliance and remediation for applications deployed on **AWS ECS** and **OpenShift (APaaS)**.

It ensures that all active services are running on approved, up-to-date base images (e.g., `rhel8.java8`) by validating against real-time Red Hat data and automatically creating GitLab pipelines for remediation.

---

## Architecture

```
base-image/
├── config/
│   ├── .env.example          # Infrastructure configuration (GitLab, AWS, OSE endpoints)
│   └── sample_otel.json      # Sample input (Service candidates)
├── scripts/
│   └── run_agent.py          # CLI entry point
├── src/
│   ├── base_image_agent.py   # Main orchestrator (Validates Deployment)
│   ├── common/               # Config loading, data models, utilities
│   ├── discovery/            # Modules for OTEL, AWS ECS, and OpenShift discovery
│   ├── compliance/           # Real-time compliance logic (Red Hat API)
│   ├── remediation/          # GitLab pipeline creation logic
│   └── reporting/            # JSON/CSV reporting module
└── requirements.txt          # Python dependencies
```

---

## Workflow Steps

### 1. Service Discovery (OTEL)
- Parses candidate services from OTEL JSON export.
- Extracts metadata: service name, image version, platform (AWS/OSE), region.
- **Dynamic Parsing**: Adapts to any OTEL JSON structure.

### 2. Real-Time Platform Validation (Mandatory)
- Before checking compliance, the agent verifies if the service is **ACTIVE**.
- **AWS**: Connects to ECS via Boto3 (using internal credential portal), checks if service exists.
- **OpenShift**: Connects to Cluster via API (using token), checks for Deployment/DeploymentConfig.
- *Services not found in live environment are skipped.*

### 3. Compliance Check (Real-Time)
- Queries **Red Hat Container Catalog API** (`GET /images/{id}/versions`) for the latest version of the base image (e.g., `rhel8`).
- Compares the running service's base image version against the live Red Hat data.
- Calculates version age (N, N-1, N-2, etc.).

### 4. Remediation (Pipeline Creation)
- For non-compliant active services, the agent **creates a new GitLab pipeline**.
- Endpoint: `POST /projects/:id/pipeline`
- Branch: User-specified (default: `main`)
- Variables: Injects `BASE_IMAGE_UPGRADE=true` and `TARGET_TAG={latest}`.
- *This creates a fresh CI/CD run to rebuild the application with the new base image.*

### 5. Reporting
- Generates JSON and CSV reports in `output/` directory.
- Lists compliant vs. non-compliant services, pipeline IDs, and validation status.

---

## Setup & Usage

### 1. Environment Setup
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configuration
Copy `config/.env.example` to `config/.env` and configure:
- `GITLAB_PRIVATE_TOKEN` - **Required** for pipeline creation.
- `AWS_PORTAL_URL` - Required for AWS validation.
- `OSE_PRIMARY_ENDPOINT` - Required for OpenShift validation.
- `REDHAT_API_URL` - Red Hat Catalog API (default provided).

### 3. Running the Agent

**Dry Run (Default)** - Validation & Compliance Check Only
```bash
python scripts/run_agent.py --input config/sample_otel.json
```

**Live Remediation** - Create Pipelines for Non-Compliant Services
```bash
python scripts/run_agent.py --input config/sample_otel.json --trigger
```

---

## Integration Points

| System | Role | Integration Method |
|--------|------|--------------------|
| **OTEL** | Source of Candidates | JSON File Parse |
| **AWS ECS** | Live Validation | `boto3` + Credential Portal |
| **OpenShift** | Live Validation | `kubernetes` client + Token |
| **Red Hat** | Compliance Golden Source | REST API (`catalog.redhat.com`) |
| **GitLab** | Remediation Action | REST API (`POST /pipeline`) |
