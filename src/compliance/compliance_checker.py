"""Compliance checker module."""

import logging
from typing import List

from src.common.models import ServiceRecord, ComplianceResult, ComplianceStatus
from src.common.config import ComplianceConfig
from src.common.utils import compare_versions
from src.compliance.redhat_client import RedHatClient

logger = logging.getLogger(__name__)


class ComplianceChecker:
    
    def __init__(self, config: ComplianceConfig):
        self.config = config
        self.rh_client = RedHatClient(config.redhat_api_url)
        
    def check_all(self, services: List[ServiceRecord]) -> List[ComplianceResult]:
        return [self.check_service(s) for s in services]
    
    def check_service(self, service: ServiceRecord) -> ComplianceResult:
        """
        Check compliance dynamically based on the service's own image type.
        Uses the full image name (e.g., rhel8-java21) for API query.
        """
        current_tag = service.base_image_version
        image_type = service.image_type
        
        if not image_type:
            logger.warning(f"Service {service.service_name} has no image type defined. Skipping API check.")
            return ComplianceResult(
                service=service,
                is_compliant=False,
                current_tag=current_tag,
                latest_tag="unknown",
                status=ComplianceStatus.UNKNOWN,
                remediation_required=False
            )

        search_name = image_type.replace('.', '-') if '.' in image_type else image_type
        
        logger.info(f"[{service.service_name}] Querying Red Hat API for: {search_name}")
        
        latest_tag_info = self.rh_client.get_latest_tag(search_name)
        
        if latest_tag_info:
            latest_tag = latest_tag_info.tag
            logger.info(f"[{service.service_name}] Latest tag for {search_name}: {latest_tag}")
        else:
            logger.error(f"[{service.service_name}] FAILED to fetch latest tag for {search_name} from Red Hat API. Skipping compliance check.")
            return ComplianceResult(
                service=service,
                is_compliant=False,
                current_tag=current_tag,
                latest_tag="API_FETCH_FAILED",
                status=ComplianceStatus.UNKNOWN,
                remediation_required=False
            )

        is_within_threshold, tag_age = compare_versions(current_tag, latest_tag)
        
        if not is_within_threshold and tag_age == 1:
            real_age = self.rh_client.get_tag_age(search_name, current_tag)
            if real_age is not None:
                tag_age = real_age
        
        is_compliant = is_within_threshold
        remediation_required = not is_within_threshold
        status = ComplianceStatus.COMPLIANT if is_compliant else ComplianceStatus.NON_COMPLIANT
        
        logger.info(f"[{service.service_name}] Current: {current_tag} | Latest: {latest_tag} | Compliant: {'YES' if is_compliant else 'NO'}")
        
        return ComplianceResult(
            service=service,
            is_compliant=is_compliant,
            current_tag=current_tag,
            latest_tag=latest_tag,
            tag_age=tag_age,
            status=status,
            remediation_required=remediation_required,
        )
    
    def get_non_compliant(self, results: List[ComplianceResult]) -> List[ComplianceResult]:
        return [r for r in results if r.remediation_required]
    
    def get_compliant(self, results: List[ComplianceResult]) -> List[ComplianceResult]:
        return [r for r in results if r.is_compliant]
