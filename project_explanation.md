# Base Image Automation Agent - Project Documentation

## Overview

The **Base Image Automation Agent** is a Python-based tool designed to automate base image compliance and remediation for applications deployed on **AWS ECS** and **OpenShift (APaaS/BCP)**.

It ensures that all active services are running on approved, up-to-date base images by:
1. Parsing OTEL telemetry data to extract service deployment information
2. Validating deployments on the appropriate platform (AWS/OSE)
3. Checking compliance against Red Hat Container Catalog API
4. Triggering GitLab pipelines for remediation when non-compliant

---

## Architecture

```
base-image/
├── config/
│   ├── .env.example          # Configuration template
│   └── sample_otel.json      # Sample OTEL input
├── scripts/
│   └── run_agent.py          # CLI entry point
├── src/
│   ├── base_image_agent.py   # Main orchestrator
│   ├── common/
│   │   ├── config.py         # Configuration loading
│   │   ├── models.py         # Data models
│   │   └── utils.py          # Utility functions
│   ├── discovery/
│   │   ├── otel_discovery.py # OTEL JSON parsing
│   │   ├── aws_discovery.py  # AWS ECS validation
│   │   └── ose_discovery.py  # OpenShift validation
│   ├── compliance/
│   │   ├── compliance_checker.py  # Compliance logic
│   │   └── redhat_client.py       # Red Hat API client
│   ├── remediation/
│   │   ├── gitlab_client.py       # GitLab API client
│   │   └── pipeline_trigger.py    # Pipeline orchestration
│   └── reporting/
│       └── report_generator.py    # Report generation
└── requirements.txt
```

---

## Workflow

### Step 1: Parse OTEL JSON

The agent receives a single-service OTEL JSON containing deployment telemetry:

**Required Fields:**
- `service.name` - Service identifier
- `profile.name` - Deployment name (used for OSE lookup)
- `region.deployed` - Deployment region (e.g., "UK")
- `image.details` - Base image type (e.g., "rhel8.java21")
- `ci_project_path` - GitLab project path
- `base.image.version` - Current base image version
- `target_deployment` - Platform ("bcp" or "aws")

**Filters Applied:**
- Job name must contain "deploy"
- Job status must be "success"

### Step 2: Validate Required Fields

The agent validates that all required fields are present:
- `image.details` - Required for compliance check
- `region.deployed` - Required for logging
- `profile.name` - Required for OSE deployment lookup
- `ci_project_path` - Required for pipeline trigger

If any required field is empty, processing stops with an error.

### Step 3: Platform Validation

Based on `target_deployment`:

**For OSE/BCP:**
- Connects to APaaS cluster (primary endpoint)
- Looks up deployment by `profile.name` in configured namespace
- Verifies deployment exists

**For AWS:**
- Connects to AWS ECS
- Looks up service in specified cluster
- Verifies service exists

### Step 4: Compliance Check

The agent queries Red Hat Container Catalog API:

1. Converts image name: `rhel8.java21` → `rhel8-java21`
2. Queries API for image versions
3. Compares current version with latest version
4. Calculates tag age (N-n)

**Important:** Versions are compared within the same image stream only.

### Step 5: Remediation

For non-compliant services:
- Triggers GitLab pipeline via API
- Passes variables: `BASE_IMAGE_UPGRADE=true`, `TARGET_TAG={latest}`

### Step 6: Reporting

Generates:
- JSON report with full details
- CSV report for compliance results
- Console summary

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GITLAB_URL` | GitLab server URL | `https://app.gitlab.barcapint.com` |
| `GITLAB_PRIVATE_TOKEN` | GitLab API token | (required) |
| `OSE_PRIMARY_ENDPOINT` | APaaS primary cluster | `https://api.np3-gl.apaas4...` |
| `OSE_SHADOW_ENDPOINT` | APaaS shadow cluster | `https://api.np3-sl.apaas4...` |
| `OSE_NAMESPACE` | OpenShift namespace | `24887` |
| `REDHAT_API_URL` | Red Hat Catalog API | `https://catalog.redhat.com/api/containers/v1` |
| `DRY_RUN` | Disable pipeline triggers | `true` |

---

## Usage

### Dry Run (Default)
```bash
python scripts/run_agent.py --input config/sample_otel.json
```

### Live Execution
```bash
python scripts/run_agent.py --input config/sample_otel.json --trigger
```

### With Custom Config
```bash
python scripts/run_agent.py --input data.json --config /path/to/.env --trigger
```

---

## Sample Input

```json
{
    "resourceSpans": [{
        "resource": {
            "attributes": [
                {"key": "service.name", "value": {"stringValue": "fdp-batch-generic"}},
                {"key": "profile.name", "value": {"stringValue": "fdp-batch-debit-rule-audit"}},
                {"key": "region.deployed", "value": {"stringValue": "UK"}},
                {"key": "image.details", "value": {"stringValue": "rhel8.java21"}}
            ]
        },
        "scopeSpans": [{
            "spans": [{
                "attributes": [
                    {"key": "cicd.pipeline.ci_job_name", "value": {"stringValue": "deploy_both_dc"}},
                    {"key": "cicd.pipeline.ci_job_status", "value": {"stringValue": "success"}},
                    {"key": "cicd.pipeline.ci_project_path", "value": {"stringValue": "barclays/fdp-shared-propagation/fdp-batch-generic"}},
                    {"key": "base.image.version", "value": {"stringValue": "1.23-3.1767880120"}},
                    {"key": "target_deployment", "value": {"stringValue": "bcp"}}
                ]
            }]
        }]
    }]
}
```

---

## Sample Output

```
============================================================
BASE IMAGE AGENT REPORT
============================================================
Timestamp: 2026-01-30T14:30:25
Dry Run: False
------------------------------------------------------------
Total Services: 1
Compliant: 0 (0.0%)
Non-compliant: 1
------------------------------------------------------------
Pipelines Triggered: 1
Pipelines Failed: 0
============================================================

NON-COMPLIANT SERVICES:
  - fdp-batch-generic (fdp-batch-debit-rule-audit)
    Current: 1.23-3.1767880120 | Latest: 1.24-1.1789000000 | Age: N-1
```
