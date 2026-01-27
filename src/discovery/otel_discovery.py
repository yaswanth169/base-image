"""OTEL JSON parser for service discovery."""

import json
import logging
from typing import List, Dict, Any, Optional

from src.common.models import ServiceRecord

logger = logging.getLogger(__name__)


class OTELDiscovery:
    
    def __init__(self, target_image_type: str = "rhel8.java8", target_platform: str = "aws"):
        self.target_image_type = target_image_type
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
            
            image_details = self._find_image_type(resource_attrs)
            if self.target_image_type and self.target_image_type not in image_details:
                continue
            
            scope_spans = resource_span.get("scopeSpans", [])
            for scope_span in scope_spans:
                for span in scope_span.get("spans", []):
                    record = self._process_span(span, resource_attrs, image_details)
                    if record:
                        services.append(record)
        
        logger.info(f"Discovered {len(services)} services")
        return services
    
    def _process_span(self, span: Dict, resource_attrs: Dict, image_details: str) -> Optional[ServiceRecord]:
        span_attrs = self._extract_attributes(span.get("attributes", []))
        all_attrs = {**resource_attrs, **span_attrs}
        
        job_name = self._find_value(all_attrs, ["job_name", "ci_job_name"], "")
        job_status = self._find_value(all_attrs, ["job_status", "ci_job_status"], "")
        
        if job_name != "deploy" or job_status != "success":
            return None
        
        platform = self._find_platform(all_attrs)
        if self.target_platform != "all" and platform != self.target_platform:
            return None
        
        service_name = self._find_value(all_attrs, ["service.name", "service_name"], "unknown")
        project_path = self._find_value(all_attrs, ["project_path", "ci_project_path"], "")
        region = self._find_value(all_attrs, ["region.deployed", "region"], "")
        app_version = self._find_value(all_attrs, ["app.image.version", "app_image_version"], "")
        base_version = self._find_value(all_attrs, ["base.image.version", "base_image_version"], "")
        environment = self._find_value(all_attrs, ["app.image.environment", "environment"], "")
        
        core_keys = {"service.name", "project_path", "region.deployed", "app.image.version", 
                     "base.image.version", "app.image.environment", "image.details"}
        metadata = {k: v for k, v in all_attrs.items() if k not in core_keys}
        
        logger.info(f"Found: {service_name} | {platform} | base={base_version}")
        
        return ServiceRecord(
            service_name=service_name,
            project_path=project_path,
            platform=platform,
            region=region,
            image_type=image_details,
            app_image_version=app_version,
            base_image_version=base_version,
            environment=environment,
            metadata=metadata,
            deploy_timestamp=span.get("endTimeUnixNano"),
        )
    
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
    
    def _find_image_type(self, attrs: Dict) -> str:
        return self._find_value(attrs, ["image.details", "image_details", "base_image"], "")
    
    def _find_platform(self, attrs: Dict) -> str:
        target = self._find_value(attrs, ["target_deployment", "platform"], "")
        if target:
            return target.lower()
        
        region = self._find_value(attrs, ["region.deployed", "region"], "")
        if "aws" in region.lower():
            return "aws"
        if "bcp" in region.lower() or "ose" in region.lower():
            return "ose"
        
        return "unknown"
    
    def to_flat_table(self, services: List[ServiceRecord]) -> List[Dict]:
        return [s.to_dict() for s in services]
