# How to Run the Base Image Automation Agent

## Prerequisites

1. **Python 3.8+** installed
2. **Git** (to clone the repository)
3. **GitLab Private Token** (for pipeline triggering)
4. **OpenShift Token** (optional - for OSE deployment validation)

---

## Installation

```bash
# 1. Navigate to project directory
cd c:\Users\yaswa\OneDrive\Documents\barclays\base-image

# 2. Create virtual environment (recommended)
python -m venv venv

# 3. Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt
```

---

## Configuration

### Step 1: Create .env file

```bash
cp config/.env.example config/.env
```

### Step 2: Edit .env file

Open `config/.env` and set the required values:

```env
# =============================================================================
# REQUIRED VARIABLES
# =============================================================================

# GitLab token for triggering pipelines
GITLAB_PRIVATE_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx

# =============================================================================
# OPTIONAL VARIABLES (have defaults)
# =============================================================================

# GitLab Configuration
GITLAB_URL=https://app.gitlab.barcapint.com
GITLAB_API_VERSION=v4

# OpenShift/APaaS Configuration
OSE_PRIMARY_ENDPOINT=https://api.np3-gl.apaas4.barclays.intranet:6443/
OSE_SHADOW_ENDPOINT=https://api.np3-sl.apaas4.barclays.intranet:6443/
OSE_NAMESPACE=24887

# AWS Configuration (if validating AWS deployments)
AWS_PROXY_URL=http://primary-proxy.gslb.intranet.barcapint.com:8080
AWS_PORTAL_URL=https://awsportal.barcapint.com/v1/creds-provider/provide-credentials/

# Red Hat API Configuration
REDHAT_API_URL=https://catalog.redhat.com/api/containers/v1
LATEST_BASE_IMAGE_TAG=1.24-1.1789000000

# Agent Settings
DRY_RUN=true
LOG_LEVEL=INFO
OUTPUT_DIR=./output
```

---

## Environment Variables Summary

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `GITLAB_PRIVATE_TOKEN` | **YES** | GitLab API token for pipeline triggers | - |
| `GITLAB_URL` | No | GitLab server URL | `https://app.gitlab.barcapint.com` |
| `OSE_PRIMARY_ENDPOINT` | No | APaaS primary cluster URL | Hardcoded |
| `OSE_NAMESPACE` | No | OpenShift namespace/project ID | `24887` |
| `REDHAT_API_URL` | No | Red Hat Container Catalog API | `https://catalog.redhat.com/api/containers/v1` |
| `DRY_RUN` | No | If `true`, pipelines won't be triggered | `true` |
| `LOG_LEVEL` | No | Logging level | `INFO` |
| `OUTPUT_DIR` | No | Directory for reports | `./output` |

---

## Running the Agent

### Dry Run Mode (Default - Safe)

No pipelines will be triggered. Use this to test:

```bash
python scripts/run_agent.py --input config/sample_otel.json
```

### Live Mode (Triggers Pipelines)

```bash
python scripts/run_agent.py --input config/sample_otel.json --trigger
```

### With Custom Config File

```bash
python scripts/run_agent.py --input config/sample_otel.json --config /path/to/.env
```

### With Custom Branch

```bash
python scripts/run_agent.py --input config/sample_otel.json --branch develop --trigger
```

### With Debug Logging

```bash
python scripts/run_agent.py --input config/sample_otel.json --log-level DEBUG
```

---

## Command Line Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--input` | `-i` | Input OTEL JSON file | **Required** |
| `--trigger` | `-t` | Enable live mode (trigger pipelines) | `false` |
| `--branch` | `-b` | Git branch for pipeline | `main` |
| `--config` | `-c` | Path to .env config file | Auto-detected |
| `--log-level` | `-l` | Log level (DEBUG, INFO, WARNING, ERROR) | `INFO` |

---

## Input JSON Requirements

Your input OTEL JSON must contain these fields:

| Field | Location | Required | Example |
|-------|----------|----------|---------|
| `service.name` | resource.attributes | Yes | `fdp-batch-generic` |
| `profile.name` | resource.attributes | Yes | `fdp-batch-debit-rule-audit` |
| `region.deployed` | resource.attributes | Yes | `UK` |
| `image.details` | resource.attributes | Yes | `rhel8.java21` |
| `ci_project_path` | span.attributes | Yes | `barclays/fdp-shared-propagation/fdp-batch-generic` |
| `base.image.version` | span.attributes | Yes | `1.23-3.1767880120` |
| `target_deployment` | span.attributes | Yes | `bcp` or `aws` |
| `ci_job_name` | span.attributes | Yes | Must contain "deploy" |
| `ci_job_status` | span.attributes | Yes | Must be "success" |

---

## Sample Input JSON

```json
{
    "resourceSpans": [
        {
            "resource": {
                "attributes": [
                    {"key": "service.name", "value": {"stringValue": "fdp-batch-generic"}},
                    {"key": "profile.name", "value": {"stringValue": "fdp-batch-debit-rule-audit"}},
                    {"key": "region.deployed", "value": {"stringValue": "UK"}},
                    {"key": "image.details", "value": {"stringValue": "rhel8.java21"}}
                ]
            },
            "scopeSpans": [
                {
                    "spans": [
                        {
                            "attributes": [
                                {"key": "cicd.pipeline.ci_job_name", "value": {"stringValue": "deploy_both_dc"}},
                                {"key": "cicd.pipeline.ci_job_status", "value": {"stringValue": "success"}},
                                {"key": "cicd.pipeline.ci_project_path", "value": {"stringValue": "barclays/fdp-shared-propagation/fdp-batch-generic"}},
                                {"key": "base.image.version", "value": {"stringValue": "1.23-3.1767880120"}},
                                {"key": "target_deployment", "value": {"stringValue": "bcp"}}
                            ]
                        }
                    ]
                }
            ]
        }
    ]
}
```

---

## Output

After running, the agent generates:

1. **Console Output** - Summary of compliance status
2. **JSON Report** - `./output/report_YYYYMMDD_HHMMSS.json`
3. **CSV Report** - `./output/compliance_YYYYMMDD_HHMMSS.csv`

---

## Example Run

```bash
$ python scripts/run_agent.py --input config/sample_otel.json

2026-01-30 14:30:25 - INFO - ============================================================
2026-01-30 14:30:25 - INFO - BASE IMAGE AUTOMATION AGENT - STARTING
2026-01-30 14:30:25 - INFO - ============================================================
2026-01-30 14:30:25 - INFO - Mode: DRY RUN (no pipelines will be triggered)
2026-01-30 14:30:25 - INFO - Loading OTEL data from: config/sample_otel.json
2026-01-30 14:30:25 - INFO - Found: fdp-batch-generic | ose | profile=fdp-batch-debit-rule-audit | image=rhel8.java21 | base=1.23-3.1767880120
2026-01-30 14:30:25 - INFO - Services extracted: 1
2026-01-30 14:30:25 - INFO - Required fields validated successfully
2026-01-30 14:30:25 - INFO - [fdp-batch-generic] Validating deployment on OSE...
2026-01-30 14:30:26 - INFO - Checking compliance against Red Hat API...
2026-01-30 14:30:26 - INFO - [fdp-batch-generic] Querying Red Hat API for: rhel8-java21
2026-01-30 14:30:27 - INFO - [fdp-batch-generic] Current: 1.23-3.1767880120 | Latest: 1.24-1.1789000000 | Compliant: NO
2026-01-30 14:30:27 - INFO - Compliant: 0
2026-01-30 14:30:27 - INFO - Non-compliant: 1
2026-01-30 14:30:27 - INFO - [DRY RUN] Would trigger: barclays/fdp-shared-propagation/fdp-batch-generic
2026-01-30 14:30:27 - INFO - JSON report saved: ./output/report_20260130_143027.json
2026-01-30 14:30:27 - INFO - CSV report saved: ./output/compliance_20260130_143027.csv

============================================================
BASE IMAGE AGENT REPORT
============================================================
Timestamp: 2026-01-30T14:30:27
Dry Run: True
------------------------------------------------------------
Total Services: 1
Compliant: 0 (0.0%)
Non-compliant: 1
------------------------------------------------------------
Pipelines Triggered: 0
Pipelines Failed: 0
============================================================

NON-COMPLIANT SERVICES:
  - fdp-batch-generic (fdp-batch-debit-rule-audit)
    Current: 1.23-3.1767880120 | Latest: 1.24-1.1789000000 | Age: N-1

2026-01-30 14:30:27 - INFO - ============================================================
2026-01-30 14:30:27 - INFO - BASE IMAGE AUTOMATION AGENT - COMPLETED
2026-01-30 14:30:27 - INFO - ============================================================
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `image.details is required but empty` | Ensure your input JSON has `image.details` field populated |
| `region.deployed is required but empty` | Ensure your input JSON has `region.deployed` field populated |
| `profile.name is required but empty` | Ensure your input JSON has `profile.name` field populated |
| `Could not connect to OSE` | Check `OSE_PRIMARY_ENDPOINT` and network access |
| `Pipeline trigger failed` | Verify `GITLAB_PRIVATE_TOKEN` is valid |
| `Module not found` | Run `pip install -r requirements.txt` |
| `No services found in input JSON` | Ensure `ci_job_name` contains "deploy" and `ci_job_status` is "success" |

---

## Workflow Overview

```
Input OTEL JSON
       │
       ▼
┌──────────────────┐
│ 1. Parse JSON    │
│    Extract fields│
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 2. Validate      │
│    Required fields│
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 3. Platform      │
│    Validation    │
│    (OSE/AWS)     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 4. Compliance    │
│    Check         │
│    (Red Hat API) │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 5. Remediation   │
│    (GitLab       │
│    Pipeline)     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 6. Generate      │
│    Reports       │
└──────────────────┘
```
