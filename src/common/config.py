"""Configuration module for Base Image Automation Agent."""

import os
import logging
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


# Hardcoded APaaS Configuration (to be made configurable later)
APAAS_V4_ID = "24887"
APAAS_V4_DC_PRIMARY = "https://api.np3-gl.apaas4.barclays.intranet:6443/"
APAAS_V4_DC_SHADOW = "https://api.np3-sl.apaas4.barclays.intranet:6443/"


@dataclass
class GitLabConfig:
    url: str
    api_version: str
    token: Optional[str]
    
    @property
    def base_url(self) -> str:
        return f"{self.url}/api/{self.api_version}"


@dataclass
class AWSConfig:
    proxy_url: str
    portal_url: str


@dataclass
class OSEConfig:
    primary_endpoint: str
    shadow_endpoint: str
    namespace: str


@dataclass
class ComplianceConfig:
    redhat_api_url: str


@dataclass
class AgentConfig:
    gitlab: GitLabConfig
    aws: AWSConfig
    ose: OSEConfig
    compliance: ComplianceConfig
    dry_run: bool
    log_level: str
    output_dir: str


def load_dotenv_file(env_path: Optional[str] = None) -> dict:
    env_vars = {}
    if env_path is None:
        possible_paths = [
            Path(__file__).parent.parent.parent / "config" / ".env",
            Path.cwd() / "config" / ".env",
            Path.cwd() / ".env",
        ]
        for p in possible_paths:
            if p.exists():
                env_path = str(p)
                break
    
    if env_path and os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
                    os.environ[key.strip()] = value.strip()
    return env_vars


def load_config(env_path: Optional[str] = None) -> AgentConfig:
    load_dotenv_file(env_path)
    
    gitlab = GitLabConfig(
        url=os.getenv("GITLAB_URL", "https://app.gitlab.barcapint.com"),
        api_version=os.getenv("GITLAB_API_VERSION", "v4"),
        token=os.getenv("GITLAB_PRIVATE_TOKEN"),
    )
    
    aws = AWSConfig(
        proxy_url=os.getenv("AWS_PROXY_URL", ""),
        portal_url=os.getenv("AWS_PORTAL_URL", ""),
    )
    
    ose = OSEConfig(
        primary_endpoint=os.getenv("OSE_PRIMARY_ENDPOINT", APAAS_V4_DC_PRIMARY),
        shadow_endpoint=os.getenv("OSE_SHADOW_ENDPOINT", APAAS_V4_DC_SHADOW),
        namespace=os.getenv("OSE_NAMESPACE", APAAS_V4_ID),
    )
    
    compliance = ComplianceConfig(
        redhat_api_url=os.getenv("REDHAT_API_URL", "https://catalog.redhat.com/api/containers/v1"),
    )
    
    return AgentConfig(
        gitlab=gitlab,
        aws=aws,
        ose=ose,
        compliance=compliance,
        dry_run=os.getenv("DRY_RUN", "true").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        output_dir=os.getenv("OUTPUT_DIR", "./output"),
    )
