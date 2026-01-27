"""Base Image Automation Agent - Main Orchestrator."""

import logging
import sys
from pathlib import Path

# Add project root to path
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
        
        # Initialize modules
        self.otel_discovery = OTELDiscovery(
            target_image_type=config.compliance.target_image_type,
            target_platform="all"
        )
        
        # Real-time platform validation clients
        self.aws_discovery = AWSDiscovery(config.aws)
        self.ose_discovery = OSEDiscovery(config.ose)
        
        self.checker = ComplianceChecker(config.compliance)
        self.gitlab = GitLabClient(config.gitlab, dry_run=config.dry_run)
        self.trigger = PipelineTrigger(self.gitlab)
        self.reporter = ReportGenerator(config.output_dir)
        
        logger.info(f"Agent initialized. Target={config.compliance.target_image_type}")
    
    def validate_deployment(self, service: ServiceRecord) -> bool:
        """
        Verify if the service is actually deployed in real-time.
        Connects to AWS or OpenShift based on platform type.
        """
        if service.platform == "aws":
            # Connect to AWS using role/region from service metadata if available
            # defaulting to eu-west-1 for POC
            if not self.aws_discovery.connect(region=service.region or "eu-west-1"):
                logger.warning(f"Could not connect to AWS for {service.service_name}")
                return False
                
            # Check if service exists in cluster
            # This requires cluster name in metadata or we search
            cluster = service.metadata.get("cluster", "default")
            details = self.aws_discovery.get_service_details(cluster, service.service_name, service.region)
            return details is not None
            
        elif service.platform == "ose":
            # Connect to OpenShift using token
            if not self.ose_discovery.connect():
                logger.warning(f"Could not connect to OpenShift for {service.service_name}")
                return False
            
            # Check if deployment exists
            namespace = service.metadata.get("namespace", "default")
            details = self.ose_discovery.get_deployment_details(service.service_name, namespace)
            return details is not None
            
        return False

    def run(self, otel_file: str, branch: str = "main", trigger: bool = False):
        logger.info("STARTING AGENT - REAL-TIME VALIDATION MODE")
        
        if trigger:
            self.config.dry_run = False
            self.gitlab.dry_run = False
        
        # Step 1: Parse OTEL Data (Candidates)
        otel_data = self.otel_discovery.load_json(otel_file)
        candidates = self.otel_discovery.parse(otel_data)
        
        if not candidates:
            logger.warning("No candidate services found in OTEL data")
            return None
        
        logger.info(f"OTEL candidates found: {len(candidates)}")
        
        # Step 2a: Real-Time Platform Validation (Mandatory)
        validated_services = []
        for service in candidates:
            logger.info(f"Validating deployment for {service.service_name} ({service.platform})...")
            is_deployed = self.validate_deployment(service)
            
            if is_deployed:
                logger.info(f"✅ Verified: {service.service_name} is active on {service.platform}")
                validated_services.append(service)
            else:
                logger.warning(f"❌ Skipped: {service.service_name} not found on {service.platform}")
        
        logger.info(f"Active services verified: {len(validated_services)}")
        
        if not validated_services:
            logger.warning("No active services found. Exiting.")
            return None

        # Step 2b: Compliance Check (Real-Time Red Hat API)
        logger.info("Checking compliance against Red Hat API...")
        compliance_results = self.checker.check_all(validated_services)
        non_compliant = self.checker.get_non_compliant(compliance_results)
        
        # Step 3: Remediation (Create Pipeline)
        pipeline_results = []
        if non_compliant:
            logger.info(f"Creating pipelines for {len(non_compliant)} services...")
            pipeline_results = self.trigger.trigger_for_non_compliant(
                non_compliant,
                branch=branch,
            )
        else:
            logger.info("All active services are compliant")
        
        # Generate Reports
        report = self.reporter.generate(
            validated_services, compliance_results, pipeline_results, self.config.dry_run
        )
        
        json_path = self.reporter.save_json(report)
        csv_path = self.reporter.save_csv(report)
        self.reporter.print_summary(report)
        
        return report


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Base Image Automation Agent")
    parser.add_argument("--input", "-i", required=True, help="OTEL JSON file")
    parser.add_argument("--branch", "-b", default="main", help="Git branch")
    parser.add_argument("--trigger", "-t", action="store_true", help="Trigger pipelines")
    parser.add_argument("--config", "-c", help="Path to .env")
    parser.add_argument("--log-level", "-l", default="INFO", help="Log level")
    
    args = parser.parse_args()
    
    setup_logging(args.log_level)
    config = load_config(args.config)
    
    agent = BaseImageAgent(config)
    agent.run(otel_file=args.input, branch=args.branch, trigger=args.trigger)


if __name__ == "__main__":
    main()
