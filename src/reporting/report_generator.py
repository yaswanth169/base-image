"""Report generator module."""

import json
import csv
import os
import logging
from typing import List
from datetime import datetime

from src.common.models import ServiceRecord, ComplianceResult, PipelineResult, AgentReport

logger = logging.getLogger(__name__)


class ReportGenerator:
    
    def __init__(self, output_dir: str = "./output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate(self, services: List[ServiceRecord], compliance_results: List[ComplianceResult],
                 pipeline_results: List[PipelineResult], dry_run: bool = True) -> AgentReport:
        compliant = sum(1 for r in compliance_results if r.is_compliant)
        triggered = sum(1 for p in pipeline_results if p.remediation_status.value == "triggered")
        failed = sum(1 for p in pipeline_results if p.remediation_status.value == "failed")
        
        return AgentReport(
            run_timestamp=datetime.utcnow().isoformat(),
            total_services=len(services),
            compliant_count=compliant,
            non_compliant_count=len(compliance_results) - compliant,
            pipelines_triggered=triggered,
            pipelines_failed=failed,
            dry_run=dry_run,
            services=[s.to_dict() for s in services],
            compliance_results=[r.to_dict() for r in compliance_results],
            pipeline_results=[p.to_dict() for p in pipeline_results],
        )
    
    def save_json(self, report: AgentReport, filename: str = None) -> str:
        if not filename:
            filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(report.to_dict(), f, indent=2, default=str)
        
        logger.info(f"JSON report: {filepath}")
        return filepath
    
    def save_csv(self, report: AgentReport, filename: str = None) -> str:
        if not filename:
            filename = f"compliance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        filepath = os.path.join(self.output_dir, filename)
        
        if report.compliance_results:
            headers = list(report.compliance_results[0].keys())
            with open(filepath, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(report.compliance_results)
        
        logger.info(f"CSV report: {filepath}")
        return filepath
    
    def print_summary(self, report: AgentReport):
        summary = report.to_dict()["summary"]
        
        print("\n" + "=" * 50)
        print("BASE IMAGE AGENT REPORT")
        print("=" * 50)
        print(f"Timestamp: {report.run_timestamp}")
        print(f"Dry Run: {summary['dry_run']}")
        print("-" * 50)
        print(f"Total: {summary['total_services']}")
        print(f"Compliant: {summary['compliant_count']} ({summary['compliance_rate']})")
        print(f"Non-compliant: {summary['non_compliant_count']}")
        print("-" * 50)
        print(f"Pipelines Triggered: {summary['pipelines_triggered']}")
        print(f"Pipelines Failed: {summary['pipelines_failed']}")
        print("=" * 50)
        
        if summary['non_compliant_count'] > 0:
            print("\nNON-COMPLIANT:")
            for r in report.compliance_results:
                if not r.get("is_compliant"):
                    print(f"  - {r['service_name']}: {r['current_tag']} -> {r['latest_tag']}")
