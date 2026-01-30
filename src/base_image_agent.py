"""Base Image Automation Agent - Main Orchestrator."""

import logging
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.common.config import load_config, AgentConfig
from src.common.models import ServiceRecord
from src.common.utils import setup_logging
from src.discovery.otel_discovery import OTELDiscovery
from src.discovery.aws_discovery import AWSDiscovery
from src.discovery.ose_discovery import OSEDiscovery
from src.compliance.compliance_checker import ComplianceChecker
from src.remediation.gitlab_client import GitLabClient
from src.remediation.pipeline_trigger import PipelineTrigger
from src.reporting.report_generator import ReportGenerator

logger = logging.getLogger(__name__)


class BaseImageAgent:
    
    def __init__(self, config: AgentConfig):
        self.config = config
        
        self.otel_discovery = OTELDiscovery(target_platform="all")
        self.aws_discovery = AWSDiscovery(config.aws)
        self.ose_discovery = OSEDiscovery(config.ose)
        
        self.checker = ComplianceChecker(config.compliance)
        self.gitlab = GitLabClient(config.gitlab, dry_run=config.dry_run)
        self.trigger = PipelineTrigger(self.gitlab)
        self.reporter = ReportGenerator(config.output_dir)
        
        logger.info("Agent initialized")
    
    def validate_deployment(self, service: ServiceRecord) -> bool:
        """Validate service deployment on the appropriate platform."""
        
        if service.platform == "ose":
            logger.info(f"[{service.service_name}] Validating deployment on OSE...")
            
            if not self.ose_discovery.connect_to_apaas():
                logger.warning(f"Could not connect to OSE for {service.service_name}")
                return False
            
            deployment_name = service.deployment_name
            namespace = self.config.ose.namespace
            
            details = self.ose_discovery.get_deployment_by_name(deployment_name, namespace)
            
            if details:
                logger.info(f"[{service.service_name}] Verified: {deployment_name} is active on OSE")
                return True
            else:
                logger.warning(f"[{service.service_name}] Deployment {deployment_name} not found on OSE")
                return False
            
        elif service.platform == "aws":
            logger.info(f"[{service.service_name}] Validating deployment on AWS...")
            
            region = self._map_region_to_aws(service.region)
            
            if not self.aws_discovery.connect(region=region):
                logger.warning(f"Could not connect to AWS for {service.service_name}")
                return False
            
            cluster = service.metadata.get("cluster", "default")
            details = self.aws_discovery.get_service_details(cluster, service.service_name, region)
            
            if details:
                logger.info(f"[{service.service_name}] Verified: {service.service_name} is active on AWS")
                return True
            else:
                logger.warning(f"[{service.service_name}] Service not found on AWS")
                return False
            
        else:
            logger.warning(f"[{service.service_name}] Unknown platform: {service.platform}")
            return False
    
    def _map_region_to_aws(self, region: str) -> str:
        """Map region names to AWS region codes."""
        region_map = {
            "uk": "eu-west-2",
            "us": "us-east-1",
            "eu": "eu-west-1",
            "de": "eu-central-1",
        }
        return region_map.get(region.lower(), "eu-west-2")

    def run(self, otel_file: str, branch: str = "main", trigger: bool = False):
        logger.info("=" * 60)
        logger.info("BASE IMAGE AUTOMATION AGENT - STARTING")
        logger.info("=" * 60)
        
        if trigger:
            self.config.dry_run = False
            self.gitlab.dry_run = False
            logger.info("Mode: LIVE (pipelines will be triggered)")
        else:
            logger.info("Mode: DRY RUN (no pipelines will be triggered)")
        
        otel_data = self.otel_discovery.load_json(otel_file)
        candidates = self.otel_discovery.parse(otel_data)
        
        if not candidates:
            logger.error("No services found in input JSON")
            return None
        
        logger.info(f"Services found in input: {len(candidates)}")
        
        for service in candidates:
            is_valid, errors = self.otel_discovery.validate_required_fields(service)
            if not is_valid:
                logger.error(f"VALIDATION FAILED for {service.service_name}:")
                for error in errors:
                    logger.error(f"  - {error}")
                return None
        
        logger.info("Required fields validated successfully")
        
        validated_services = []
        
        for service in candidates:
            is_deployed = self.validate_deployment(service)
            
            if is_deployed:
                validated_services.append(service)
            else:
                logger.warning(f"Skipped: {service.service_name} not found active on {service.platform}")
        
        if not validated_services:
            logger.warning("No active services verified. Continuing with compliance check anyway.")
            validated_services = candidates
        
        logger.info(f"Validated services: {len(validated_services)}")
        
        logger.info("Checking compliance against Red Hat API...")
        compliance_results = self.checker.check_all(validated_services)
        non_compliant = self.checker.get_non_compliant(compliance_results)
        
        logger.info(f"Compliant: {len(compliance_results) - len(non_compliant)}")
        logger.info(f"Non-compliant: {len(non_compliant)}")
        
        pipeline_results = []
        if non_compliant:
            logger.info(f"Creating pipelines for {len(non_compliant)} non-compliant services...")
            pipeline_results = self.trigger.trigger_for_non_compliant(
                non_compliant,
                branch=branch,
            )
        else:
            logger.info("All services are compliant. No remediation needed.")
        
        report = self.reporter.generate(
            validated_services, compliance_results, pipeline_results, self.config.dry_run
        )
        
        json_path = self.reporter.save_json(report)
        csv_path = self.reporter.save_csv(report)
        self.reporter.print_summary(report)
        
        logger.info("=" * 60)
        logger.info("BASE IMAGE AUTOMATION AGENT - COMPLETED")
        logger.info("=" * 60)
        
        return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Base Image Automation Agent")
    parser.add_argument("--input", "-i", required=True, help="Input OTEL JSON file")
    parser.add_argument("--branch", "-b", default="main", help="Git branch for pipeline")
    parser.add_argument("--trigger", "-t", action="store_true", help="Trigger pipelines (disable dry run)")
    parser.add_argument("--config", "-c", help="Path to .env config file")
    parser.add_argument("--log-level", "-l", default="INFO", help="Log level")
    
    args = parser.parse_args()
    
    setup_logging(args.log_level)
    config = load_config(args.config)
    
    agent = BaseImageAgent(config)
    agent.run(otel_file=args.input, branch=args.branch, trigger=args.trigger)


if __name__ == "__main__":
    main()
