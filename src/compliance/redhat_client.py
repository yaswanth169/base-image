"""Red Hat API client for real-time image version checking."""

import logging
import requests
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TagInfo:
    tag: str
    release_date: Optional[datetime] = None
    is_latest: bool = False
    image_age: Optional[str] = None


class RedHatClient:
    """
    Client for Red Hat Container Catalog API.
    Used to fetch the latest available base image versions in real-time.
    """
    
    def __init__(self, api_url: str):
        self.api_url = api_url.rstrip('/')
        self._image_cache: Dict[str, List[TagInfo]] = {}
        self.rhel_image_names: dict = {
            "rhel8-java21": "apaas/barclays-rhel8-rh-java-openjdk21-runtime",
            "rhel8-java17": "apaas/barclays-rhel8-rh-java-openjdk17-runtime",
            "rhel8-java8": "barclays/ubi8"
        }
    
    def get_latest_tag(self, image_name: str) -> Optional[TagInfo]:
        """
        Get the latest tag for a given image name (e.g., 'rhel8').
        
        Flow:
        1. GET /images?name={name} -> Get image_id
        2. GET /images/{image_id}/versions -> Get all versions
        3. Sort by date and return latest
        """
        versions = self._get_image_versions(image_name)
        if versions:
            return versions[0]
        return None
    
    def get_tag_age(self, image_name: str, current_tag: str) -> Optional[int]:
        """
        Calculate how many versions behind the current tag is (N-n).
        
        Returns:
            0 = latest (N)
            1 = one behind (N-1)
            etc.
        """
        versions = self._get_image_versions(image_name)
        if not versions:
            return None
        
        # specific logic to match tag format
        # API returns 'redHatTag', we compare with that
        for i, v in enumerate(versions):
            if v.tag == current_tag:
                return i
        
        # Tag not found in recent history - assume very old
        return len(versions)
    
    def _get_image_versions(self, image_name: str) -> List[TagInfo]:
        """Fetch and cache image versions from API."""
        if image_name in self._image_cache:
            return self._image_cache[image_name]
        
        try:
            # Step 1: Get Image ID
            base_image_name = self.rhel_image_names[image_name]
            image_id = self._get_image_id(base_image_name)
            if not image_id:
                logger.warning(f"Image not found: {base_image_name}")
                return []
            
            # Step 2: Get Versions
            url = f"{self.api_url}/images/{image_id}/versions"
            logger.info(f"Fetching versions for {base_image_name} (ID: {image_id}) from {url}")
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Parse and sort versions
            tags = []
            for item in data:
                tag = item.get("redHatTag") or item.get("tag")
                date_str = item.get("madeLiveDate")
                
                dt = None
                if date_str:
                    try:
                        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    except ValueError:
                        pass
                
                if tag:
                    tags.append(TagInfo(
                        tag=tag, 
                        release_date=dt,
                        image_age=item.get("imageAge")
                    ))
            
            # Sort by release date descending (newest first)
            tags.sort(key=lambda x: x.release_date or datetime.min, reverse=True)
            
            # Mark latest
            if tags:
                tags[0].is_latest = True
                
            self._image_cache[image_name] = tags
            return tags
            
        except Exception as e:
            logger.error(f"Error fetching versions for {image_name}: {e}")
            return []

    def _get_image_id(self, image_name: str) -> Optional[str]:
        """Get internal ID for an image name."""
        try:
            url = f"{self.api_url}/images"
            params = {"name": image_name}
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data and isinstance(data, list):
                # Return ID of first match
                return str(data[0].get("id"))
            
            return None
            
        except Exception as e:
            logger.error(f"Error searching for image {image_name}: {e}")
            return None
