# Base Image Automation Agent

Automates base image compliance checking and pipeline remediation for services deployed on AWS ECS and OpenShift (APaaS/BCP).

## Project Structure

```
base-image/
├── src/
│   ├── __init__.py
│   ├── base_image_agent.py          # Main orchestrator
│   ├── common/
│   │   ├── config.py                # Configuration loading
│   │   ├── models.py                # Data models
│   │   └── utils.py                 # Utilities
│   ├── discovery/
│   │   ├── otel_discovery.py        # OTEL JSON parsing
│   │   ├── aws_discovery.py         # AWS ECS discovery
│   │   └── ose_discovery.py         # OpenShift discovery
│   ├── compliance/
│   │   ├── compliance_checker.py    # Compliance logic
│   │   └── redhat_client.py         # Red Hat API client
│   ├── remediation/
│   │   ├── gitlab_client.py         # GitLab API
│   │   └── pipeline_trigger.py      # Pipeline orchestration
│   └── reporting/
│       └── report_generator.py      # JSON/CSV reports
├── config/
│   ├── .env.example                 # Configuration template
│   └── sample_otel.json             # Sample input data
├── scripts/
│   └── run_agent.py                 # CLI entry point
├── tests/
└── requirements.txt
```

## Quick Start

```bash
# 1. Setup config
cp config/.env.example config/.env
# Edit config/.env with your GitLab token

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run agent (dry run)
python scripts/run_agent.py --input config/sample_otel.json

# 4. Run with actual pipeline triggering
python scripts/run_agent.py --input config/sample_otel.json --trigger
```

## Configuration

**config/.env** - Configuration options:
- `GITLAB_URL`, `GITLAB_PRIVATE_TOKEN` - GitLab API access
- `OSE_PRIMARY_ENDPOINT`, `OSE_NAMESPACE` - OpenShift access
- `AWS_PROXY_URL`, `AWS_PORTAL_URL` - AWS access
- `REDHAT_API_URL` - Red Hat Container Catalog
- `DRY_RUN` - Set to `false` to trigger pipelines

## Workflow

1. **Parse**: Load OTEL JSON, extract service details
2. **Validate Fields**: Ensure required fields (image.details, region.deployed) are present
3. **Validate Platform**: Check service exists on OSE or AWS
4. **Compliance Check**: Query Red Hat API, compare versions
5. **Remediation**: Trigger GitLab pipelines for non-compliant services
6. **Report**: Generate JSON/CSV reports

## Required JSON Fields

| Field | Description | Example |
|-------|-------------|---------|
| `service.name` | Service identifier | `fdp-batch-generic` |
| `profile.name` | Deployment name (OSE) | `fdp-batch-debit-rule-audit` |
| `region.deployed` | Deployment region | `UK` |
| `image.details` | Base image type | `rhel8.java21` |
| `ci_project_path` | GitLab project path | `barclays/fdp-shared-propagation/fdp-batch-generic` |
| `base.image.version` | Current base image version | `1.23-3.1767880120` |
| `target_deployment` | Platform | `bcp` or `aws` |

## Command Line Options

```
python scripts/run_agent.py --help

Options:
  --input, -i     Input OTEL JSON file (required)
  --branch, -b    Git branch for pipeline (default: main)
  --trigger, -t   Trigger pipelines (disable dry run)
  --config, -c    Path to .env config file
  --log-level, -l Log level (default: INFO)
```
