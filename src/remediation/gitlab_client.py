"""GitLab client for pipeline triggering."""

import logging
from typing import Optional, Dict
from datetime import datetime

from src.common.models import PipelineResult, RemediationStatus
from src.common.config import GitLabConfig
from src.common.utils import encode_project_path

logger = logging.getLogger(__name__)

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class GitLabClient:
    
    def __init__(self, config: GitLabConfig, dry_run: bool = True):
        self.base_url = config.base_url
        self.token = config.token
        self.dry_run = dry_run
    
    def _headers(self) -> Dict[str, str]:
        return {"PRIVATE-TOKEN": self.token or "", "Content-Type": "application/json"}
    
    def trigger_pipeline(self, project_path: str, ref: str = "main", 
                        variables: Optional[Dict[str, str]] = None) -> PipelineResult:
        service_name = project_path.split("/")[-1]
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would trigger: {project_path} (ref: {ref})")
            return PipelineResult(
                service_name=service_name,
                project_path=project_path,
                status="dry_run",
                triggered_at=datetime.utcnow().isoformat(),
                remediation_status=RemediationStatus.SKIPPED,
            )
        
        if not HAS_REQUESTS:
            return PipelineResult(
                service_name=service_name,
                project_path=project_path,
                error="requests library not installed",
                remediation_status=RemediationStatus.FAILED,
            )
        
        encoded_path = encode_project_path(project_path)
        url = f"{self.base_url}/projects/{encoded_path}/pipeline"
        
        payload = {"ref": ref}
        if variables:
            payload["variables"] = [{"key": k, "value": v} for k, v in variables.items()]
        
        try:
            response = requests.post(url, headers=self._headers(), json=payload, timeout=30)
            
            if response.status_code == 201:
                data = response.json()
                logger.info(f"Pipeline triggered: {data.get('web_url')}")
                return PipelineResult(
                    service_name=service_name,
                    project_path=project_path,
                    pipeline_id=data.get("id"),
                    pipeline_url=data.get("web_url"),
                    status=data.get("status"),
                    triggered_at=datetime.utcnow().isoformat(),
                    remediation_status=RemediationStatus.TRIGGERED,
                )
            else:
                logger.error(f"Failed: {response.status_code}")
                return PipelineResult(
                    service_name=service_name,
                    project_path=project_path,
                    error=f"HTTP {response.status_code}",
                    remediation_status=RemediationStatus.FAILED,
                )
        except Exception as e:
            logger.exception(f"Error triggering pipeline")
            return PipelineResult(
                service_name=service_name,
                project_path=project_path,
                error=str(e),
                remediation_status=RemediationStatus.FAILED,
            )
    
    def get_pipeline_status(self, project_path: str, pipeline_id: int) -> PipelineResult:
        service_name = project_path.split("/")[-1]
        
        if self.dry_run:
            return PipelineResult(
                service_name=service_name,
                project_path=project_path,
                pipeline_id=pipeline_id,
                status="dry_run",
                remediation_status=RemediationStatus.SKIPPED,
            )
        
        if not HAS_REQUESTS:
            return PipelineResult(
                service_name=service_name,
                project_path=project_path,
                pipeline_id=pipeline_id,
                error="requests not installed",
                remediation_status=RemediationStatus.FAILED,
            )
        
        encoded_path = encode_project_path(project_path)
        url = f"{self.base_url}/projects/{encoded_path}/pipelines/{pipeline_id}"
        
        try:
            response = requests.get(url, headers=self._headers(), timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                
                status_map = {
                    "success": RemediationStatus.COMPLETED,
                    "failed": RemediationStatus.FAILED,
                    "canceled": RemediationStatus.FAILED,
                    "pending": RemediationStatus.IN_PROGRESS,
                    "running": RemediationStatus.IN_PROGRESS,
                }
                
                return PipelineResult(
                    service_name=service_name,
                    project_path=project_path,
                    pipeline_id=pipeline_id,
                    pipeline_url=data.get("web_url"),
                    status=status,
                    remediation_status=status_map.get(status, RemediationStatus.TRIGGERED),
                )
            else:
                return PipelineResult(
                    service_name=service_name,
                    project_path=project_path,
                    pipeline_id=pipeline_id,
                    error=f"HTTP {response.status_code}",
                    remediation_status=RemediationStatus.FAILED,
                )
        except Exception as e:
            return PipelineResult(
                service_name=service_name,
                project_path=project_path,
                pipeline_id=pipeline_id,
                error=str(e),
                remediation_status=RemediationStatus.FAILED,
            )
