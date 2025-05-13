# CKAN Migration Tool (2.8.2 → 2.11.2)

A Python tool for migrating data between CKAN instances, specifically designed to handle the migration from CKAN 2.8.2 to CKAN 2.11.2 with proper handling of API differences and conflict resolution.

## Overview

This script facilitates the migration of organizations, datasets, and resources from a source CKAN instance (version 2.8.2) to a target CKAN instance (version 2.11.2). 

## Example usage
```
# Migrate everything (organizations, datasets, and resources)
python ckan_migrator.py config.json

# Migrate only specific organizations with their datasets and resources
python ckan_migrator.py config.json --orgs org1 org2

# Migrate only specific datasets with their resources
python ckan_migrator.py config.json --skip-orgs --datasets dataset1 dataset2

# Migrate only dataset metadata, not resources
python ckan_migrator.py config.json --skip-resources

# Skip confirmation prompt
python ckan_migrator.py config.json --yes

# Migrate only organizations (skip datasets and resources)
python ckan_migrator.py config.json --skip-datasets
```
