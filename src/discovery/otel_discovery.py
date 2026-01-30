"""OTEL JSON parser for service discovery."""

import json
import logging
from typing import List, Dict, Any, Optional, Tuple

from src.common.models import ServiceRecord

logger = logging.getLogger(__name__)


class OTELDiscovery:
    
    def __init__(self, target_platform: str = "all"):
        self.target_platform = target_platform.lower()
    
    def load_json(self, file_path: str) -> Dict[str, Any]:
        logger.info(f"Loading OTEL data from: {file_path}")
        with open(file_path, 'r') as f:
            return json.load(f)
    
    def parse(self, otel_data: Dict[str, Any]) -> List[ServiceRecord]:
        services = []
        resource_spans = otel_data.get("resourceSpans", [])
        
        for resource_span in resource_spans:
            resource_attrs = self._extract_attributes(
                resource_span.get("resource", {}).get("attributes", [])
            )
            
            scope_spans = resource_span.get("scopeSpans", [])
            for scope_span in scope_spans:
                for span in scope_span.get("spans", []):
                    record = self._process_span(span, resource_attrs)
                    if record:
                        services.append(record)
        
        logger.info(f"Services extracted: {len(services)}")
        return services
    
    def _process_span(self, span: Dict, resource_attrs: Dict) -> Optional[ServiceRecord]:
        span_attrs = self._extract_attributes(span.get("attributes", []))
        all_attrs = {**resource_attrs, **span_attrs}
        
        job_name = self._find_value(all_attrs, ["ci_job_name", "job_name"], "")
        job_status = self._find_value(all_attrs, ["ci_job_status", "job_status"], "")
        
        if "deploy" not in job_name.lower() or job_status != "success":
            return None
        
        platform = self._find_platform(all_attrs)
        if self.target_platform != "all" and platform != self.target_platform:
            return None
        
        service_name = self._find_value(all_attrs, ["service.name", "service_name"], "unknown")
        profile_name = self._find_value(all_attrs, ["profile.name", "profile_name"], "")
        project_path = self._find_value(all_attrs, ["ci_project_path", "project_path"], "")
        region = self._find_value(all_attrs, ["region.deployed", "region"], "")
        image_type = self._find_value(all_attrs, ["image.details", "image_details"], "")
        app_version = self._find_value(all_attrs, ["app.image.version", "app_image_version"], "")
        base_version = self._find_value(all_attrs, ["base.image.version", "base_image_version"], "")
        environment = self._find_value(all_attrs, ["app.image.environment", "environment"], "")
        
        core_keys = {
            "service.name", "profile.name", "ci_project_path", "region.deployed",
            "app.image.version", "base.image.version", "app.image.environment", "image.details"
        }
        metadata = {k: v for k, v in all_attrs.items() if k not in core_keys}
        
        logger.info(f"Found: {service_name} | {platform} | profile={profile_name} | image={image_type} | base={base_version}")
        
        return ServiceRecord(
            service_name=service_name,
            profile_name=profile_name,
            project_path=project_path,
            platform=platform,
            region=region,
            image_type=image_type,
            app_image_version=app_version,
            base_image_version=base_version,
            environment=environment,
            metadata=metadata,
            deploy_timestamp=span.get("endTimeUnixNano"),
        )
    
    def validate_required_fields(self, service: ServiceRecord) -> Tuple[bool, List[str]]:
        """
        Validate that required fields are present.
        Returns (is_valid, list_of_errors)
        """
        errors = []
        
        if not service.image_type:
            errors.append("image.details is required but empty")
        
        if not service.region:
            errors.append("region.deployed is required but empty")
        
        if not service.profile_name:
            errors.append("profile.name is required but empty")
        
        if not service.project_path:
            errors.append("ci_project_path is required but empty")
        
        if not service.service_name or service.service_name == "unknown":
            errors.append("service.name is required but empty")
        
        return (len(errors) == 0, errors)
    
    def _extract_attributes(self, attributes: List[Dict]) -> Dict[str, str]:
        result = {}
        for attr in attributes:
            key = attr.get("key", "")
            value_obj = attr.get("value", {})
            
            if "stringValue" in value_obj:
                result[key] = value_obj["stringValue"]
            elif "intValue" in value_obj:
                result[key] = str(value_obj["intValue"])
            elif "boolValue" in value_obj:
                result[key] = str(value_obj["boolValue"])
            elif "doubleValue" in value_obj:
                result[key] = str(value_obj["doubleValue"])
        
        return result
    
    def _find_value(self, attrs: Dict, possible_keys: List[str], default: str) -> str:
        for key in possible_keys:
            if key in attrs:
                return attrs[key]
            for attr_key in attrs:
                if key in attr_key:
                    return attrs[attr_key]
        return default
    
    def _find_platform(self, attrs: Dict) -> str:
        target = self._find_value(attrs, ["target_deployment", "platform"], "")
        if target:
            target = target.lower()
            if target in ("bcp", "apaas", "openshift"):
                return "ose"
            return target
        
        region = self._find_value(attrs, ["region.deployed", "region"], "")
        if "aws" in region.lower():
            return "aws"
        if "bcp" in region.lower() or "ose" in region.lower():
            return "ose"
        
        return "unknown"
    
    def to_flat_table(self, services: List[ServiceRecord]) -> List[Dict]:
        return [s.to_dict() for s in services]
