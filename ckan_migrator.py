#!/usr/bin/env python3
"""
CKAN Migration Script - Download data from CKAN 2.8.2 
and upload to CKAN 2.11.2 with a complete migration strategy

This script reads configuration from a JSON file containing source and target information.
It allows selective migration of organizations, datasets, and resources.
"""

import os
import json
import re
import time
import datetime
import requests
import logging
import sys
import argparse
from urllib.parse import urljoin

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("migration.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ckan_migrator")

class CkanMigrator:
    def __init__(self, source_url, source_api_key, target_url, target_api_key):
        """Initialize the CKAN migrator with source and target information"""
        self.source_url = source_url.rstrip('/')
        self.source_api_key = source_api_key
        self.target_url = target_url.rstrip('/')
        self.target_api_key = target_api_key
        self.download_dir = "ckan_migration"
        self.org_dir = os.path.join(self.download_dir, "organizations")
        self.datasets_dir = os.path.join(self.download_dir, "datasets")
        
        # Create download directory if it doesn't exist
        for directory in [self.download_dir, self.org_dir, self.datasets_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
        
        # Dictionary to map source organization IDs to target organization IDs
        self.org_id_mapping = {}
        
        # Read the mapping file if it exists (for resuming migration)
        mapping_file = os.path.join(self.download_dir, "org_mapping.json")
        if os.path.exists(mapping_file):
            try:
                with open(mapping_file, 'r') as f:
                    self.org_id_mapping = json.load(f)
                logger.info(f"Loaded organization mapping with {len(self.org_id_mapping)} entries")
            except Exception as e:
                logger.error(f"Error loading organization mapping: {e}")

    def save_org_mapping(self):
        """Save the organization mapping to a file"""
        mapping_file = os.path.join(self.download_dir, "org_mapping.json")
        try:
            with open(mapping_file, 'w') as f:
                json.dump(self.org_id_mapping, f, indent=2)
            logger.info(f"Saved organization mapping with {len(self.org_id_mapping)} entries")
        except Exception as e:
            logger.error(f"Error saving organization mapping: {e}")

    def prepare_target_database(self):
        """Check target CKAN instance"""
        try:
            logger.info("Checking target CKAN instance...")
            
            # Check status of target CKAN
            check_url = urljoin(self.target_url, "api/3/action/status_show")
            headers = {"Authorization": self.target_api_key}
            response = requests.get(check_url, headers=headers)
            
            if response.status_code == 200:
                logger.info("Target CKAN instance is accessible.")
                
                # Check if the target CKAN is version 2.11+
                try:
                    response_json = response.json()
                    if 'result' in response_json and 'ckan_version' in response_json['result']:
                        ckan_version = response_json['result']['ckan_version']
                        logger.info(f"Target CKAN version: {ckan_version}")
                        
                        # Check if the version meets requirements
                        major, minor = map(int, ckan_version.split('.')[:2])
                        if major < 2 or (major == 2 and minor < 11):
                            logger.warning(f"Target CKAN version {ckan_version} may not be compatible with this migration tool")
                except Exception:
                    logger.warning("Could not parse CKAN version information")
                
                logger.info("\nIMPORTANT: Before continuing, ensure you've run 'ckan -c CONFIG_FILE db upgrade' on the target system")
                
            return True
        except Exception as e:
            logger.error(f"Error checking target database: {e}")
            return False
    
    def source_request(self, url, method="GET", params=None, data=None, files=None):
        """Make a request to the source CKAN"""
        if params is None:
            params = {}
        
        headers = {"Authorization": self.source_api_key}
        
        max_retries = 3
        retry_delay = 5  # seconds
        
        for attempt in range(max_retries):
            try:
                if method == "GET":
                    response = requests.get(url, headers=headers, params=params)
                elif method == "POST":
                    response = requests.post(url, headers=headers, json=data, files=files)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    error_msg = f"HTTP {response.status_code}"
                    try:
                        error_data = response.json()
                        if 'error' in error_data:
                            error_msg = f"{error_msg}: {error_data['error']}"
                    except:
                        error_msg = f"{error_msg}: {response.text[:100]}"
                    
                    logger.error(f"Source API error: {error_msg}")
                    
                    if attempt < max_retries - 1:
                        logger.info(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        return {"success": False, "error": error_msg}
                    
            except Exception as e:
                logger.error(f"Request failed (attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "Max retries exceeded"}
    
    def target_request(self, url, method="GET", params=None, data=None, files=None):
        """Make a request to the target CKAN"""
        if params is None:
            params = {}
        
        headers = {"Authorization": self.target_api_key}
        
        max_retries = 3
        retry_delay = 5  # seconds
        
        for attempt in range(max_retries):
            try:
                if method == "GET":
                    response = requests.get(url, headers=headers, params=params)
                elif method == "POST":
                    response = requests.post(url, headers=headers, json=data, files=files)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    error_msg = f"HTTP {response.status_code}"
                    try:
                        error_data = response.json()
                        if 'error' in error_data:
                            error_msg = f"{error_msg}: {error_data['error']}"
                    except:
                        error_msg = f"{error_msg}: {response.text[:100]}"
                    
                    logger.error(f"Target API error: {error_msg}")
                    
                    if attempt < max_retries - 1:
                        logger.info(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        return {"success": False, "error": error_msg}
                    
            except Exception as e:
                logger.error(f"Request failed (attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "Max retries exceeded"}
    
    def sanitize_name(self, name):
        """Sanitize a name to ensure it's valid in CKAN 2.11"""
        if not name:
            return name
            
        # Remove invalid characters
        sanitized = re.sub(r'[^a-z0-9_\-]', '_', name.lower())
        
        # Make sure it's not too long
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
            
        return sanitized
    
    def get_organization_list(self, specific_orgs=None):
        """
        Get list of organizations from source CKAN
        
        Args:
            specific_orgs: List of specific organization names or IDs to include
        
        Returns:
            List of organization IDs
        """
        url = urljoin(self.source_url, "api/3/action/organization_list")
        
        logger.info("Retrieving list of organizations...")
        response = self.source_request(url)
        
        if response.get("success", False):
            all_org_ids = response.get("result", [])
            logger.info(f"Found {len(all_org_ids)} organizations in total")
            
            if specific_orgs:
                # Filter organizations by name or ID
                filtered_orgs = []
                
                # First try to match by direct ID
                for org_id in specific_orgs:
                    if org_id in all_org_ids:
                        filtered_orgs.append(org_id)
                
                # If we haven't matched all orgs, try matching by name
                if len(filtered_orgs) < len(specific_orgs):
                    # Get details of all orgs to match by name
                    for org_id in all_org_ids:
                        if org_id in filtered_orgs:
                            continue
                            
                        url = urljoin(self.source_url, "api/3/action/organization_show")
                        params = {"id": org_id}
                        org_response = self.source_request(url, params=params)
                        
                        if org_response.get("success", False):
                            org_name = org_response.get("result", {}).get("name")
                            if org_name in specific_orgs:
                                filtered_orgs.append(org_id)
                
                logger.info(f"Filtered to {len(filtered_orgs)} specified organizations")
                return filtered_orgs
            else:
                return all_org_ids
        else:
            logger.error(f"Failed to get organization list: {response.get('error', {})}")
            return []
    
    def download_organization(self, org_id):
        """Download a single organization metadata"""
        logger.info(f"Downloading organization: {org_id}")
        url = urljoin(self.source_url, "api/3/action/organization_show")
        params = {"id": org_id, "include_datasets": False}
        
        # Get organization metadata with all details
        response = self.source_request(url, params=params)
        
        if not response.get("success", False):
            logger.error(f"Failed to get organization {org_id}: {response.get('error', {})}")
            return None
        
        org_data = response.get("result", {})
        
        # Save organization metadata
        org_file = os.path.join(self.org_dir, f"{org_id}.json")
        with open(org_file, 'w') as f:
            json.dump(org_data, f, indent=2)
        
        return {
            "metadata": org_data,
            "metadata_file": org_file
        }
    
    def upload_organization(self, org_data):
        """Upload an organization to target CKAN"""
        if not org_data:
            return False
        
        metadata = org_data["metadata"]
        org_id = metadata.get("id")
        org_name = metadata.get("name")
        
        # If the organization is already in our mapping, skip it
        if org_id in self.org_id_mapping:
            logger.info(f"Organization {org_name} already migrated, skipping")
            return True
        
        logger.info(f"Processing organization: {org_name}")
        
        # Sanitize organization data
        sanitized_metadata = metadata.copy()
        
        # Ensure name is valid
        original_name = sanitized_metadata.get('name', '')
        sanitized_name = self.sanitize_name(original_name)
        
        if original_name != sanitized_name:
            logger.info(f"Organization name sanitized: '{original_name}' -> '{sanitized_name}'")
            sanitized_metadata['name'] = sanitized_name
        
        # Remove fields that shouldn't be included in the creation request
        fields_to_remove = [
            "id", "created", "is_organization", "revision_id", "revision_timestamp", 
            "packages", "display_name", "package_count", "users", "groups", 
            "followers_count", "state", "num_followers"
        ]
        
        for field in fields_to_remove:
            if field in sanitized_metadata:
                del sanitized_metadata[field]
        
        # Check if org exists by name
        check_url = urljoin(self.target_url, "api/3/action/organization_show")
        check_params = {"id": sanitized_name}
        check_response = self.target_request(check_url, params=check_params)
        
        if check_response.get("success", False):
            # Organization already exists, get its ID
            existing_org = check_response.get("result", {})
            existing_org_id = existing_org.get("id")
            logger.info(f"Organization already exists with ID: {existing_org_id}")
            
            # Store ID mapping
            self.org_id_mapping[org_id] = existing_org_id
            self.save_org_mapping()
            return True
        
        # Create organization in target CKAN
        create_url = urljoin(self.target_url, "api/3/action/organization_create")
        create_response = self.target_request(create_url, method="POST", data=sanitized_metadata)
        
        if not create_response.get("success", False):
            logger.error(f"Failed to create organization {org_name}: {create_response.get('error', {})}")
            return False
        
        created_org = create_response.get("result", {})
        created_org_id = created_org.get("id")
        
        logger.info(f"Created organization with ID: {created_org_id}")
        
        # Store ID mapping
        self.org_id_mapping[org_id] = created_org_id
        self.save_org_mapping()
        return True
    
    def get_dataset_list(self, specific_datasets=None, org_id=None):
        """
        Get list of datasets from source CKAN
        
        Args:
            specific_datasets: List of specific dataset names or IDs to include
            org_id: Organization ID to filter datasets by
            
        Returns:
            List of dataset IDs
        """
        if specific_datasets:
            # First try to get datasets directly by ID
            dataset_ids = []
            for dataset_id in specific_datasets:
                url = urljoin(self.source_url, "api/3/action/package_show")
                params = {"id": dataset_id}
                response = self.source_request(url, params=params)
                
                if response.get("success", False):
                    dataset_ids.append(dataset_id)
                    
            logger.info(f"Found {len(dataset_ids)} specified datasets by ID")
            return dataset_ids
            
        elif org_id:
            # Get datasets belonging to a specific organization
            url = urljoin(self.source_url, "api/3/action/organization_show")
            params = {"id": org_id, "include_datasets": True}
            response = self.source_request(url, params=params)
            
            if response.get("success", False):
                org_data = response.get("result", {})
                datasets = org_data.get("packages", [])
                dataset_ids = [dataset.get("id") for dataset in datasets]
                logger.info(f"Found {len(dataset_ids)} datasets in organization {org_id}")
                return dataset_ids
            else:
                logger.error(f"Failed to get datasets for organization {org_id}: {response.get('error', {})}")
                return []
        else:
            # Get all datasets
            url = urljoin(self.source_url, "api/3/action/package_list")
            response = self.source_request(url)
            
            if response.get("success", False):
                dataset_ids = response.get("result", [])
                logger.info(f"Found {len(dataset_ids)} datasets in total")
                return dataset_ids
            else:
                logger.error(f"Failed to get dataset list: {response.get('error', {})}")
                return []
    
    def download_package(self, package_id):
        """Download a single package (dataset) and its resources"""
        logger.info(f"Downloading dataset: {package_id}")
        url = urljoin(self.source_url, "api/3/action/package_show")
        params = {"id": package_id}
        
        # Get package metadata
        response = self.source_request(url, params=params)
        
        if not response.get("success", False):
            logger.error(f"Failed to get package {package_id}: {response.get('error', {})}")
            return None
        
        package_data = response.get("result", {})
        
        # Save package metadata
        package_file = os.path.join(self.datasets_dir, f"{package_id}.json")
        with open(package_file, 'w') as f:
            json.dump(package_data, f, indent=2)
        
        # Download resources if present
        resources = package_data.get("resources", [])
        resource_dir = os.path.join(self.datasets_dir, package_id)
        
        if resources and not os.path.exists(resource_dir):
            os.makedirs(resource_dir)
        
        # Track resource file paths to add to metadata
        resource_files = []
        
        for resource in resources:
            resource_id = resource.get("id")
            resource_url = resource.get("url")
            resource_format = resource.get("format", "bin").lower()
            
            if not resource_url:
                continue
            
            # Create filename for resource
            resource_filename = f"{resource_id}.{resource_format}"
            resource_path = os.path.join(resource_dir, resource_filename)
            
            logger.info(f"  Downloading resource: {resource_id}")
            
            try:
                # Download resource file
                response = requests.get(resource_url, headers={"Authorization": self.source_api_key})
                response.raise_for_status()
                
                with open(resource_path, 'wb') as f:
                    f.write(response.content)
                
                # Add to resource files list
                resource_files.append({
                    "id": resource_id,
                    "path": resource_path,
                    "metadata": resource
                })
                
                logger.info(f"  Resource saved to {resource_path}")
            except requests.exceptions.RequestException as e:
                logger.error(f"  Failed to download resource {resource_id}: {e}")
        
        return {
            "metadata": package_data,
            "metadata_file": package_file,
            "resources": resource_files
        }

    def migrate_package(self, package_data, skip_resources=False):
        """Migrate a package (dataset) and its resources to target CKAN using package_create"""
        if not package_data:
            return False
        
        metadata = package_data["metadata"]
        resources = package_data.get("resources", []) if not skip_resources else []
        package_id = metadata.get("id")
        package_name = metadata.get("name", "")
        
        logger.info(f"Migrating dataset: {package_name}")
        
        # Sanitize dataset data
        sanitized_metadata = metadata.copy()
        
        # Sanitize the dataset name
        original_name = sanitized_metadata.get('name', '')
        sanitized_name = self.sanitize_name(original_name)
        
        if original_name != sanitized_name:
            logger.info(f"Dataset name sanitized: '{original_name}' -> '{sanitized_name}'")
            sanitized_metadata['name'] = sanitized_name
        
        # For CKAN 2.11.2, we'll use package_create 
        # We'll remove all IDs to force creation of new objects
        if 'id' in sanitized_metadata:
            del sanitized_metadata['id']
            
        # Remove resource data as we'll upload resources separately
        if 'resources' in sanitized_metadata:
            del sanitized_metadata['resources']
            
        # Remove fields that shouldn't be included
        fields_to_remove = [
            "metadata_created", "metadata_modified", "revision_id", "revision_timestamp",
            "creator_user_id", "private"
        ]
        
        for field in fields_to_remove:
            if field in sanitized_metadata:
                del sanitized_metadata[field]
        
        # Update organization reference using the ID mapping
        if "owner_org" in sanitized_metadata:
            source_org_id = sanitized_metadata["owner_org"]
            if source_org_id in self.org_id_mapping:
                sanitized_metadata["owner_org"] = self.org_id_mapping[source_org_id]
            else:
                logger.warning(f"Organization {source_org_id} not found in mapping, removing owner_org")
                del sanitized_metadata["owner_org"]
        
        # Check if dataset already exists
        check_url = urljoin(self.target_url, "api/3/action/package_show")
        check_params = {"id": sanitized_name}
        check_response = self.target_request(check_url, params=check_params)
        
        if check_response.get("success", False):
            # Dataset already exists, we'll skip it
            existing_pkg = check_response.get("result", {})
            existing_pkg_id = existing_pkg.get("id")
            logger.info(f"Dataset already exists with ID: {existing_pkg_id}")
            logger.info(f"Skipping dataset creation, moving to resources")
            target_package_id = existing_pkg_id
        else:
            # Create dataset in target CKAN
            create_url = urljoin(self.target_url, "api/3/action/package_create")
            create_response = self.target_request(create_url, method="POST", data=sanitized_metadata)
            
            if not create_response.get("success", False):
                logger.error(f"Failed to create dataset {package_name}: {create_response.get('error', {})}")
                return False
            
            created_package = create_response.get("result", {})
            target_package_id = created_package.get("id")
            
            logger.info(f"Created dataset with ID: {target_package_id}")
        
        # Upload resources if not skipping
        if not skip_resources and resources:
            successful_resources = 0
            for resource_data in resources:
                if self.migrate_resource(target_package_id, resource_data):
                    successful_resources += 1
            
            logger.info(f"Uploaded {successful_resources}/{len(resources)} resources")
        
        return True
    
    def migrate_resource(self, package_id, resource_data):
        """Migrate a resource to the target CKAN"""
        if not resource_data:
            return False
        
        resource_id = resource_data.get("id")
        resource_path = resource_data.get("path")
        resource_metadata = resource_data.get("metadata", {})
        
        if not os.path.exists(resource_path):
            logger.error(f"  Resource file not found: {resource_path}")
            return False
        
        logger.info(f"  Uploading resource: {resource_id}")
        
        # Sanitize resource metadata
        sanitized_metadata = resource_metadata.copy()
        
        # Remove fields that shouldn't be included 
        fields_to_remove = [
            "id", "created", "last_modified", "revision_id", "resource_type",
            "position", "cache_url", "cache_last_updated", "webstore_url", 
            "webstore_last_updated", "datastore_active"
        ]
        
        for field in fields_to_remove:
            if field in sanitized_metadata:
                del sanitized_metadata[field]
        
        # Add package_id to resource metadata
        sanitized_metadata["package_id"] = package_id
        
        # Create resource
        url = urljoin(self.target_url, "api/3/action/resource_create")
        
        # Some important resource fields need to be properly sanitized
        if 'name' in sanitized_metadata:
            sanitized_metadata['name'] = sanitized_metadata['name'][:100]
        
        if 'description' in sanitized_metadata and sanitized_metadata['description'] is None:
            sanitized_metadata['description'] = ''
        
        # Prepare the file for upload
        files = {
            'upload': (os.path.basename(resource_path), open(resource_path, 'rb'))
        }
        
        try:
            # Convert metadata to form fields
            data = {key: str(value) if value is not None else '' 
                   for key, value in sanitized_metadata.items()}
            
            # CKAN 2.11.2 expects a simple HTTP POST form, not JSON
            headers = {"Authorization": self.target_api_key}
            
            # Make the request manually since our helper expects JSON
            response = requests.post(url, headers=headers, data=data, files=files)
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    if response_data.get("success", False):
                        logger.info(f"  Resource uploaded successfully")
                        return True
                    else:
                        error_msg = response_data.get('error', {})
                        logger.error(f"  Failed to upload resource: {error_msg}")
                except Exception as e:
                    logger.error(f"  Error parsing response: {e}")
            else:
                logger.error(f"  Failed to upload resource: HTTP {response.status_code}")
                
                if response.status_code == 404:
                    logger.error("  404 NOT FOUND - The resource_create endpoint may have changed in CKAN 2.11.2")
                    logger.error("  Trying alternative approach...")
                    
                    # Try a different approach - create with minimal data first
                    minimal_data = {
                        "package_id": package_id,
                        "name": data.get('name', 'Resource'),
                        "url": data.get('url', 'http://example.com')
                    }
                    
                    alt_url = urljoin(self.target_url, "api/3/action/resource_create")
                    alt_response = requests.post(alt_url, headers=headers, json=minimal_data)
                    
                    if alt_response.status_code == 200 and alt_response.json().get("success", False):
                        logger.info("  Successfully created resource placeholder")
                        return True
            
            return False
                    
        except Exception as e:
            logger.error(f"  Error uploading resource: {e}")
            return False
        finally:
            # Close the file
            files['upload'][1].close()
    
    def migrate_all(self, migrate_orgs=True, migrate_datasets=True, migrate_resources=True, 
                   specific_orgs=None, specific_datasets=None):
        """
        Migrate data from source to target CKAN
        
        Args:
            migrate_orgs: Whether to migrate organizations
            migrate_datasets: Whether to migrate datasets
            migrate_resources: Whether to migrate resources
            specific_orgs: List of specific organization names/IDs to migrate
            specific_datasets: List of specific dataset names/IDs to migrate
        """
        # First check target database readiness
        if not self.prepare_target_database():
            logger.error("Target database preparation failed. Please resolve issues before proceeding.")
            return
        
        # Migrate organizations if requested
        if migrate_orgs:
            logger.info("\n===== MIGRATING ORGANIZATIONS =====\n")
            org_ids = self.get_organization_list(specific_orgs=specific_orgs)
            
            if not org_ids:
                logger.warning("No organizations found to migrate.")
            else:
                total_orgs = len(org_ids)
                successful_org_migrations = 0
                
                # Process each organization
                for i, org_id in enumerate(org_ids):
                    logger.info(f"\nProcessing organization {i+1}/{total_orgs}: {org_id}")
                    
                    try:
                        # Download organization
                        org_data = self.download_organization(org_id)
                        
                        if org_data:
                            # Upload organization
                            if self.upload_organization(org_data):
                                successful_org_migrations += 1
                    except Exception as e:
                        logger.error(f"Error processing organization {org_id}: {e}")
                        logger.info("Continuing with next organization...")
                    
                    # Add a small delay to prevent overwhelming the server
                    time.sleep(1)
                
                logger.info(f"\nOrganization migration complete. Successfully migrated {successful_org_migrations}/{total_orgs} organizations.")
        
        # Migrate datasets if requested
        if migrate_datasets:
            logger.info("\n===== MIGRATING DATASETS =====\n")
            
            # Get list of datasets to migrate
            if specific_datasets:
                package_ids = self.get_dataset_list(specific_datasets=specific_datasets)
            elif specific_orgs:
                # Get datasets for specific organizations
                package_ids = []
                for org_id in specific_orgs:
                    org_datasets = self.get_dataset_list(org_id=org_id)
                    package_ids.extend(org_datasets)
            else:
                # Get all datasets
                package_ids = self.get_dataset_list()
            
            if not package_ids:
                logger.warning("No datasets found to migrate.")
                return
            
            total_packages = len(package_ids)
            successful_dataset_migrations = 0
            
            # Process each package
            for i, package_id in enumerate(package_ids):
                logger.info(f"\nProcessing dataset {i+1}/{total_packages}: {package_id}")
                
                try:
                    # Download package
                    package_data = self.download_package(package_id)
                    
                    if package_data:
                        # Using package_create instead of package_update
                        if self.migrate_package(package_data, skip_resources=not migrate_resources):
                            successful_dataset_migrations += 1
                except Exception as e:
                    logger.error(f"Error processing dataset {package_id}: {e}")
                    logger.info("Continuing with next dataset...")
                
                # Add a small delay to prevent overwhelming the server
                time.sleep(1)
            
            logger.info(f"\nDataset migration complete. Successfully migrated {successful_dataset_migrations}/{total_packages} datasets.")
        
        # Display summary
        logger.info("\n===== MIGRATION SUMMARY =====")
        if migrate_orgs:
            logger.info(f"Organizations: {successful_org_migrations}/{len(org_ids)} migrated successfully")
        if migrate_datasets:
            logger.info(f"Datasets: {successful_dataset_migrations}/{total_packages} migrated successfully")
        
        logger.info("\n===== POST-MIGRATION STEPS =====")
        logger.info("1. Run 'ckan -c /etc/ckan/default/ckan.ini search-index rebuild' on the target system")
        logger.info("2. Check if datapusher/datastore requires configuration")
        logger.info("3. Verify permissions and user roles")


def load_config(config_file):
    """Load configuration from a JSON file"""
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        required_keys = ["source_url", "source_api_key", "target_url", "target_api_key"]
        missing_keys = [key for key in required_keys if key not in config]
        
        if missing_keys:
            logger.error(f"Configuration file is missing the following required keys: {', '.join(missing_keys)}")
            return None
        
        return config
    except Exception as e:
        logger.error(f"Error loading configuration file: {e}")
        return None


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='CKAN Migration Tool (2.8.2 -> 2.11.2)')
    
    parser.add_argument('config', nargs='?', default='ckan_migration_config.json',
                        help='Path to configuration JSON file (default: ckan_migration_config.json)')
    
    parser.add_argument('--skip-orgs', action='store_true',
                        help='Skip organization migration')
    
    parser.add_argument('--skip-datasets', action='store_true',
                        help='Skip dataset migration')
    
    parser.add_argument('--skip-resources', action='store_true',
                        help='Skip resource migration (only migrate dataset metadata)')
    
    parser.add_argument('--orgs', nargs='+',
                        help='Specific organizations to migrate (by name or ID)')
    
    parser.add_argument('--datasets', nargs='+',
                        help='Specific datasets to migrate (by name or ID)')
    
    parser.add_argument('--yes', '-y', action='store_true',
                        help='Skip confirmation prompt')
    
    return parser.parse_args()


if __name__ == "__main__":
    # Parse command line arguments
    args = parse_args()
    
    # Load configuration from file
    config = load_config(args.config)
    
    if not config:
        logger.error(f"Could not load configuration from {args.config}")
        logger.info("Example config file format:")
        logger.info('''{
  "source_url": "http://source-ckan-url",
  "source_api_key": "your-source-api-key",
  "target_url": "http://target-ckan-url",
  "target_api_key": "your-target-api-key"
}''')
        sys.exit(1)
    
    # Determine what to migrate
    migrate_orgs = not args.skip_orgs
    migrate_datasets = not args.skip_datasets
    migrate_resources = not args.skip_resources
    
    # Construct component list for display
    components = []
    if migrate_orgs:
        components.append("organizations")
    if migrate_datasets:
        components.append("datasets")
    if migrate_resources and migrate_datasets:
        components.append("resources")
    
    # Display migration plan
    logger.info("\n===== CKAN MIGRATION (2.8.2 -> 2.11.2) =====\n")
    logger.info(f"Source CKAN: {config['source_url']}")
    logger.info(f"Target CKAN: {config['target_url']}")
    logger.info(f"\nComponents to migrate: {', '.join(components)}")
    
    if args.orgs:
        logger.info(f"Filtering to specified organizations: {args.orgs}")
    
    if args.datasets:
        logger.info(f"Filtering to specified datasets: {args.datasets}")
    
    logger.info("\nWARNING: This process may take a long time depending on the amount of data")
    
    # Ask for confirmation unless --yes flag is provided
    if not args.yes:
        proceed = input("\nDo you want to proceed? (y/n): ")
        if proceed.lower() != 'y':
            logger.info("Migration aborted.")
            sys.exit(0)
    
    # Initialize and run the migrator
    migrator = CkanMigrator(
        config['source_url'],
        config['source_api_key'],
        config['target_url'],
        config['target_api_key']
    )
    
    migrator.migrate_all(
        migrate_orgs=migrate_orgs,
        migrate_datasets=migrate_datasets,
        migrate_resources=migrate_resources,
        specific_orgs=args.orgs,
        specific_datasets=args.datasets
    )