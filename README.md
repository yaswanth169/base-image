# Base Image Automation Agent

Automates base image compliance checking and pipeline remediation for services deployed on AWS ECS and OpenShift.

## Project Structure

```
base-image/
├── src/
│   ├── __init__.py
│   ├── base_image_agent.py          # Main orchestrator
│   ├── common/
│   │   ├── config.py                # Static config from .env
│   │   ├── models.py                # Data models
│   │   └── utils.py                 # Utilities
│   ├── discovery/
│   │   ├── otel_discovery.py        # Dynamic OTEL parsing
│   │   ├── aws_discovery.py         # AWS ECS discovery
│   │   └── ose_discovery.py         # OpenShift discovery
│   ├── compliance/
│   │   ├── compliance_checker.py    # Step 2a & 2b
│   │   └── redhat_client.py         # Red Hat API client
│   ├── remediation/
│   │   ├── gitlab_client.py         # GitLab API
│   │   └── pipeline_trigger.py      # Pipeline orchestration
│   └── reporting/
│       └── report_generator.py      # JSON/CSV reports
├── config/
│   ├── .env.example                 # Static infrastructure config
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

**config/.env** - Static infrastructure config only:
- `GITLAB_URL`, `GITLAB_PRIVATE_TOKEN` - GitLab API
- `AWS_PROXY_URL`, `AWS_PORTAL_URL` - AWS access
- `OSE_PRIMARY_ENDPOINT` - OpenShift access
- `LATEST_BASE_IMAGE_TAG` - Target compliance tag
- `DRY_RUN` - Set to `false` to trigger pipelines

## Workflow

1. **Step 1**: Parse OTEL JSON → Flat table (dynamic field extraction)
2. **Step 2a**: Platform validation
3. **Step 2b**: Tag age check (N/N-n)
4. **Step 3**: Trigger pipelines for non-compliant services
5. Generate JSON/CSV reports
