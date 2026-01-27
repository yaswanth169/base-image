"""AWS ECS discovery module."""

import logging
import os
import re
from typing import List, Optional

from src.common.models import ServiceRecord
from src.common.config import AWSConfig

logger = logging.getLogger(__name__)

try:
    import boto3
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class AWSCredentialProvider:
    
    def __init__(self, config: AWSConfig):
        self.proxy_url = config.proxy_url
        self.portal_url = config.portal_url
    
    def get_session(self, role_arn: str, region: str = "eu-west-1"):
        if not HAS_BOTO3 or not HAS_REQUESTS:
            logger.error("Required libraries not installed")
            return None
        
        try:
            if self.proxy_url:
                os.environ['HTTP_PROXY'] = self.proxy_url
                os.environ['HTTPS_PROXY'] = self.proxy_url
            
            response = requests.post(
                self.portal_url,
                json={"role_arn": role_arn},
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            
            if response.status_code != 200:
                logger.error(f"Credential provider error: {response.status_code}")
                return None
            
            creds = response.json()
            return boto3.Session(
                aws_access_key_id=creds.get("AccessKeyId"),
                aws_secret_access_key=creds.get("SecretAccessKey"),
                aws_session_token=creds.get("SessionToken"),
                region_name=region,
            )
        except Exception as e:
            logger.exception(f"Error getting AWS credentials: {e}")
            return None
    
    def get_session_from_env(self, region: str = "eu-west-1"):
        if not HAS_BOTO3:
            return None
        try:
            session = boto3.Session(region_name=region)
            session.client('sts').get_caller_identity()
            return session
        except Exception:
            return None


class AWSDiscovery:
    
    def __init__(self, config: AWSConfig):
        self.config = config
        self.credential_provider = AWSCredentialProvider(config)
        self._session = None
    
    def set_session(self, session):
        self._session = session
    
    def connect(self, role_arn: str = None, region: str = "eu-west-1") -> bool:
        if role_arn:
            self._session = self.credential_provider.get_session(role_arn, region)
        else:
            self._session = self.credential_provider.get_session_from_env(region)
        return self._session is not None
    
    def list_services(self, cluster_name: str, region: str) -> List[str]:
        if not self._session:
            return []
        
        try:
            ecs = self._session.client('ecs', region_name=region)
            services = []
            paginator = ecs.get_paginator('list_services')
            
            for page in paginator.paginate(cluster=cluster_name, maxResults=100):
                arns = page.get('serviceArns', [])
                services.extend([arn.split('/')[-1] for arn in arns])
            
            return services
        except Exception as e:
            logger.error(f"Error listing services: {e}")
            return []
    
    def get_service_details(self, cluster: str, service: str, region: str) -> Optional[ServiceRecord]:
        if not self._session:
            return None
        
        try:
            ecs = self._session.client('ecs', region_name=region)
            
            svc_resp = ecs.describe_services(cluster=cluster, services=[service])
            if not svc_resp['services']:
                return None
            
            task_def_arn = svc_resp['services'][0].get('taskDefinition', '')
            task_resp = ecs.describe_task_definition(taskDefinition=task_def_arn)
            task_def = task_resp['taskDefinition']
            
            container = task_def['containerDefinitions'][0]
            image = container.get('image', '')
            labels = container.get('dockerLabels', {})
            env_vars = {e['name']: e['value'] for e in container.get('environment', [])}
            
            base_version = labels.get('BASE_IMAGE_VERSION', 
                          env_vars.get('BASE_IMAGE_VERSION', 
                          self._extract_base_version(image)))
            
            return ServiceRecord(
                service_name=service,
                project_path=env_vars.get('PROJECT_PATH', ''),
                platform='aws',
                region=region,
                image_type=self._extract_image_type(image),
                app_image_version=labels.get('DEVOPS_APP_VERSION', ''),
                base_image_version=base_version,
                environment=env_vars.get('ENV', ''),
                metadata={"cluster": cluster, "image": image},
            )
        except Exception as e:
            logger.error(f"Error getting service details: {e}")
            return None
    
    def _extract_image_type(self, image: str) -> str:
        parts = image.split('/')
        for part in parts:
            if 'rhel' in part.lower() or 'java' in part.lower():
                return part.split(':')[0]
        return ''
    
    def _extract_base_version(self, image: str) -> str:
        if ':' in image:
            tag = image.split(':')[-1]
            match = re.search(r'(\d+\.\d+-\d+)', tag)
            if match:
                return match.group(1)
        return ''
