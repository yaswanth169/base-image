"""Data models for Base Image Automation Agent."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum


class Platform(str, Enum):
    AWS = "aws"
    OSE = "ose"
    BCP = "bcp"
    UNKNOWN = "unknown"


class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    UNKNOWN = "unknown"


class RemediationStatus(str, Enum):
    PENDING = "pending"
    TRIGGERED = "triggered"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ServiceRecord:
    service_name: str
    profile_name: str
    project_path: str
    platform: str
    region: str
    image_type: str
    app_image_version: str
    base_image_version: str
    environment: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    deploy_timestamp: Optional[str] = None
    
    @property
    def deployment_name(self) -> str:
        """Returns the deployment name for platform validation."""
        return self.profile_name if self.profile_name else self.service_name
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_name": self.service_name,
            "profile_name": self.profile_name,
            "project_path": self.project_path,
            "platform": self.platform,
            "region": self.region,
            "image_type": self.image_type,
            "app_image_version": self.app_image_version,
            "base_image_version": self.base_image_version,
            "environment": self.environment,
            "deploy_timestamp": self.deploy_timestamp,
            **self.metadata,
        }


@dataclass
class ComplianceResult:
    service: ServiceRecord
    is_compliant: bool
    current_tag: str
    latest_tag: str
    tag_age: Optional[int] = None
    status: ComplianceStatus = ComplianceStatus.UNKNOWN
    remediation_required: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_name": self.service.service_name,
            "profile_name": self.service.profile_name,
            "project_path": self.service.project_path,
            "platform": self.service.platform,
            "environment": self.service.environment,
            "image_type": self.service.image_type,
            "is_compliant": self.is_compliant,
            "current_tag": self.current_tag,
            "latest_tag": self.latest_tag,
            "tag_age": f"N-{self.tag_age}" if self.tag_age else "N",
            "status": self.status.value,
            "remediation_required": self.remediation_required,
        }


@dataclass
class PipelineResult:
    service_name: str
    project_path: str
    pipeline_id: Optional[int] = None
    pipeline_url: Optional[str] = None
    status: Optional[str] = None
    triggered_at: Optional[str] = None
    error: Optional[str] = None
    remediation_status: RemediationStatus = RemediationStatus.PENDING
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_name": self.service_name,
            "project_path": self.project_path,
            "pipeline_id": self.pipeline_id,
            "pipeline_url": self.pipeline_url,
            "status": self.status,
            "triggered_at": self.triggered_at,
            "error": self.error,
            "remediation_status": self.remediation_status.value,
        }


@dataclass
class AgentReport:
    run_timestamp: str
    total_services: int
    compliant_count: int
    non_compliant_count: int
    pipelines_triggered: int
    pipelines_failed: int
    dry_run: bool
    services: List[Dict[str, Any]]
    compliance_results: List[Dict[str, Any]]
    pipeline_results: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        rate = f"{(self.compliant_count / self.total_services * 100):.1f}%" if self.total_services > 0 else "N/A"
        return {
            "run_timestamp": self.run_timestamp,
            "summary": {
                "total_services": self.total_services,
                "compliant_count": self.compliant_count,
                "non_compliant_count": self.non_compliant_count,
                "compliance_rate": rate,
                "pipelines_triggered": self.pipelines_triggered,
                "pipelines_failed": self.pipelines_failed,
                "dry_run": self.dry_run,
            },
            "services": self.services,
            "compliance_results": self.compliance_results,
            "pipeline_results": self.pipeline_results,
        }
