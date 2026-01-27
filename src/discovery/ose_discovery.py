"""OpenShift/OSE discovery module."""

import logging
import os
from typing import List, Optional, Dict, Any

from src.common.models import ServiceRecord
from src.common.config import OSEConfig

logger = logging.getLogger(__name__)

try:
    from kubernetes import client as k8s_client
    from kubernetes.client import Configuration
    from openshift.dynamic import DynamicClient
    HAS_OPENSHIFT = True
except ImportError:
    HAS_OPENSHIFT = False


class OSECredentialProvider:
    
    def __init__(self, config: OSEConfig):
        self.primary_endpoint = config.primary_endpoint
        self.shadow_endpoint = config.shadow_endpoint
    
    def get_client(self, endpoint: str, token: str = None, location: str = "primary"):
        if not HAS_OPENSHIFT:
            logger.error("openshift library not installed")
            return None
        
        try:
            config = Configuration()
            config.host = endpoint
            config.verify_ssl = True
            
            if token:
                config.api_key = {"authorization": f"Bearer {token}"}
            else:
                token = self._get_token_from_env()
                if token:
                    config.api_key = {"authorization": f"Bearer {token}"}
            
            api_client = k8s_client.ApiClient(config)
            return DynamicClient(api_client)
        except Exception as e:
            logger.exception(f"Error creating OSE client: {e}")
            return None
    
    def get_primary_client(self, token: str = None):
        return self.get_client(self.primary_endpoint, token, "primary")
    
    def get_shadow_client(self, token: str = None):
        return self.get_client(self.shadow_endpoint, token, "shadow")
    
    def _get_token_from_env(self) -> Optional[str]:
        token = os.getenv("OSE_TOKEN") or os.getenv("OPENSHIFT_TOKEN")
        if token:
            return token
        
        token_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
        if os.path.exists(token_path):
            with open(token_path, 'r') as f:
                return f.read().strip()
        return None


class OSEDiscovery:
    
    def __init__(self, config: OSEConfig):
        self.config = config
        self.credential_provider = OSECredentialProvider(config)
        self._clients: Dict[str, Any] = {}
    
    def set_client(self, location: str, client):
        self._clients[location] = client
    
    def connect(self, token: str = None) -> bool:
        primary = self.credential_provider.get_primary_client(token)
        if primary:
            self._clients["primary"] = primary
        
        shadow = self.credential_provider.get_shadow_client(token)
        if shadow:
            self._clients["shadow"] = shadow
        
        return len(self._clients) > 0
    
    def list_deployments(self, namespace: str, location: str = "primary") -> List[str]:
        client = self._clients.get(location)
        if not client:
            return []
        
        try:
            deployments = []
            
            try:
                resource = client.resources.get(api_version='apps/v1', kind='Deployment')
                result = resource.get(namespace=namespace)
                deployments.extend([d.metadata.name for d in result.items])
            except Exception:
                pass
            
            try:
                resource = client.resources.get(api_version='apps.openshift.io/v1', kind='DeploymentConfig')
                result = resource.get(namespace=namespace)
                deployments.extend([d.metadata.name for d in result.items])
            except Exception:
                pass
            
            return list(set(deployments))
        except Exception as e:
            logger.error(f"Error listing deployments: {e}")
            return []
    
    def get_deployment_details(self, name: str, namespace: str, location: str = "primary") -> Optional[ServiceRecord]:
        client = self._clients.get(location)
        if not client:
            return None
        
        try:
            deployment = None
            kind = "Deployment"
            
            try:
                resource = client.resources.get(api_version='apps/v1', kind='Deployment')
                deployment = resource.get(name=name, namespace=namespace)
            except Exception:
                try:
                    resource = client.resources.get(api_version='apps.openshift.io/v1', kind='DeploymentConfig')
                    deployment = resource.get(name=name, namespace=namespace)
                    kind = "DeploymentConfig"
                except Exception:
                    return None
            
            if not deployment:
                return None
            
            containers = deployment.spec.template.spec.containers
            if not containers:
                return None
            
            container = containers[0]
            image = container.image if hasattr(container, 'image') else ''
            
            labels = dict(deployment.metadata.labels) if deployment.metadata.labels else {}
            
            env_vars = {}
            if hasattr(container, 'env') and container.env:
                for env in container.env:
                    if hasattr(env, 'value') and env.value:
                        env_vars[env.name] = env.value
            
            return ServiceRecord(
                service_name=name,
                project_path=labels.get('GITLAB_PROJECT_PATH', env_vars.get('PROJECT_PATH', '')),
                platform='ose',
                region=location,
                image_type=self._extract_image_type(image),
                app_image_version=labels.get('DEVOPS_APP_VERSION', ''),
                base_image_version=labels.get('BASE_IMAGE_VERSION', ''),
                environment=labels.get('ENVIRONMENT', env_vars.get('ENV', '')),
                metadata={"namespace": namespace, "kind": kind},
            )
        except Exception as e:
            logger.error(f"Error getting deployment details: {e}")
            return None
    
    def _extract_image_type(self, image: str) -> str:
        parts = image.split('/')
        for part in parts:
            if 'rhel' in part.lower() or 'java' in part.lower():
                return part.split(':')[0]
        return ''
