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
        self.target_image_type = config.target_image_type
        # Initialize real Red Hat client
        self.rh_client = RedHatClient(config.redhat_api_url)
        self.latest_tag_cache = None
        
    def _get_latest_tag(self) -> str:
        """Get latest tag from API, fallback to config if fails."""
        if self.latest_tag_cache:
            return self.latest_tag_cache
            
        # Try fetching from API
        # Extract 'rhel8' from 'rhel8.java8' for search
        search_name = self.target_image_type.split('.')[0]
        
        rh_tag = self.rh_client.get_latest_tag(search_name)
        if rh_tag:
            logger.info(f"Retrieved latest tag from Red Hat API: {rh_tag.tag}")
            self.latest_tag_cache = rh_tag.tag
            return rh_tag.tag
            
        logger.warning(f"Failed to get tag from API, using fallback: {self.config.latest_base_image_tag}")
        return self.config.latest_base_image_tag
    
    def check_all(self, services: List[ServiceRecord]) -> List[ComplianceResult]:
        # Refresh latest tag at start of check
        self.latest_tag_cache = None
        latest_tag = self._get_latest_tag()
        
        results = [self.check_service(s, latest_tag) for s in services]
        compliant = sum(1 for r in results if r.is_compliant)
        logger.info(f"Compliance: {compliant}/{len(results)} compliant (Target: {latest_tag})")
        return results
    
    def check_service(self, service: ServiceRecord, latest_tag: str) -> ComplianceResult:
        current_tag = service.base_image_version
        
        # Use simple comparison first
        is_within_threshold, tag_age = compare_versions(current_tag, latest_tag)
        
        # If simple comparison fails, try using API for accurate age (N-n)
        if not is_within_threshold and tag_age == 1:
             # Extract searchable name
             search_name = self.target_image_type.split('.')[0]
             real_age = self.rh_client.get_tag_age(search_name, current_tag)
             if real_age is not None:
                 tag_age = real_age
        
        is_compliant = is_within_threshold
        remediation_required = not is_within_threshold
        status = ComplianceStatus.COMPLIANT if is_compliant else ComplianceStatus.NON_COMPLIANT
        
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
