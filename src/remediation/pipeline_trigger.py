"""Pipeline trigger orchestration."""

import logging
from typing import List, Optional, Dict

from src.common.models import ComplianceResult, PipelineResult, RemediationStatus
from src.remediation.gitlab_client import GitLabClient

logger = logging.getLogger(__name__)


class PipelineTrigger:
    
    def __init__(self, gitlab_client: GitLabClient):
        self.gitlab = gitlab_client
    
    def trigger_for_non_compliant(self, non_compliant: List[ComplianceResult], 
                                   branch: str = "main",
                                   variables: Optional[Dict[str, str]] = None) -> List[PipelineResult]:
        results = []
        
        for result in non_compliant:
            service = result.service
            
            if not service.project_path:
                results.append(PipelineResult(
                    service_name=service.service_name,
                    project_path="",
                    error="No project path",
                    remediation_status=RemediationStatus.SKIPPED,
                ))
                continue
            
            trigger_vars = {
                "BASE_IMAGE_UPGRADE": "true",
                "TARGET_TAG": result.latest_tag,
                **(variables or {}),
            }
            
            pipeline_result = self.gitlab.trigger_pipeline(
                project_path=service.project_path,
                ref=branch,
                variables=trigger_vars,
            )
            results.append(pipeline_result)
        
        triggered = sum(1 for r in results if r.remediation_status == RemediationStatus.TRIGGERED)
        skipped = sum(1 for r in results if r.remediation_status == RemediationStatus.SKIPPED)
        failed = sum(1 for r in results if r.remediation_status == RemediationStatus.FAILED)
        
        logger.info(f"Pipelines: triggered={triggered}, skipped={skipped}, failed={failed}")
        return results
