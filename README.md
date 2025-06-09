# CKAN Migration Tool (2.8.2 → 2.11.2)

A Python tool for migrating data between CKAN instances, specifically designed to handle the migration from CKAN 2.8.2 to CKAN 2.11.2 with proper handling of API differences and conflict resolution.

## Overview

This script facilitates the migration of organizations, datasets, and resources from a source CKAN instance (version 2.8.2) to a target CKAN instance (version 2.11.2). It addresses compatibility issues between these versions and provides robust error handling for common migration challenges.

## Features

- **Selective Migration**: Choose to migrate organizations, datasets, resources, or any combination
- **Persistent Sessions**: Uses HTTP session pooling for better performance and reliability
- **SSL Flexibility**: Disables SSL verification for compatibility with self-signed certificates
- **Conflict Resolution**: Handles 409 CONFLICT and 404 NOT FOUND errors gracefully
- **Resume Capability**: Can resume interrupted migrations using saved organization mappings
- **Detailed Logging**: Comprehensive logging to both console and file
- **Flexible Filtering**: Migrate specific organizations or datasets by name/ID
- **Version Compatibility**: Designed specifically for CKAN 2.8.2 → 2.11.2 migration

## Requirements

- Python 3.6 or higher
- `requests` library
- Access to both source (2.8.2) and target (2.11.2) CKAN instances
- Valid API keys for both CKAN instances with appropriate permissions

## Installation

1. **Clone or download the script**:
   ```bash
   wget https://raw.githubusercontent.com/your-repo/ckan_migrator.py
   ```

2. **Install dependencies**:
   ```bash
   pip install requests
   ```

3. **Make the script executable**:
   ```bash
   chmod +x ckan_migrator.py
   ```

## Configuration

Create a JSON configuration file with your CKAN connection details:

```json
{
  "source_url": "https://source-ckan.example.com",
  "source_api_key": "your-source-api-key-here",
  "target_url": "https://target-ckan.example.com",
  "target_api_key": "your-target-api-key-here"
}
```

### Getting API Keys

1. Log into your CKAN instance
2. Go to your user profile
3. Find the "API Key" or "API Tokens" section
4. Copy the key/token for use in the configuration file

**Note**: Ensure your API keys have sufficient permissions to create organizations, datasets, and resources on the target system.

## Usage

### Basic Usage

```bash
# Migrate everything using default config file
python3 ckan_migrator.py

# Use a specific config file
python3 ckan_migrator.py my_config.json

# Skip confirmation prompt
python3 ckan_migrator.py --yes
```

### Selective Migration

```bash
# Migrate only organizations
python3 ckan_migrator.py --skip-datasets

# Migrate only datasets (without resources)
python3 ckan_migrator.py --skip-orgs --skip-resources

# Migrate specific organizations and their datasets
python3 ckan_migrator.py --orgs org1 org2 org3

# Migrate specific datasets by name/ID
python3 ckan_migrator.py --datasets dataset1 dataset2

# Migrate datasets without their file resources (metadata only)
python3 ckan_migrator.py --skip-resources
```

### Command-Line Options

| Option | Description |
|--------|-------------|
| `--skip-orgs` | Skip organization migration |
| `--skip-datasets` | Skip dataset migration |
| `--skip-resources` | Skip resource file migration (metadata only) |
| `--orgs ORG1 ORG2` | Migrate specific organizations by name or ID |
| `--datasets DS1 DS2` | Migrate specific datasets by name or ID |
| `--yes` or `-y` | Skip confirmation prompt |

## Migration Process

The tool follows this sequence:

1. **Validation**: Checks connectivity to both source and target CKAN instances
2. **Organizations**: Downloads and creates organizations in the target system
3. **Organization Mapping**: Maintains a mapping file to handle ID changes
4. **Datasets**: Downloads dataset metadata and creates datasets in target system
5. **Resources**: Downloads resource files and uploads them to target system
6. **Logging**: Records all operations and errors to `migration.log`

## Directory Structure

The script creates the following directory structure:

```
ckan_migration/
├── organizations/           # Downloaded organization metadata
│   ├── org1.json
│   └── org2.json
├── datasets/               # Downloaded dataset metadata and resources
│   ├── dataset1.json
│   ├── dataset1/          # Resource files for dataset1
│   │   ├── resource1.csv
│   │   └── resource2.pdf
│   └── dataset2.json
└── org_mapping.json       # Organization ID mapping (for resume capability)
```

## Error Handling

The script handles common migration errors:

- **409 CONFLICT**: When datasets/organizations already exist
- **404 NOT FOUND**: When API endpoints have changed between versions
- **Network timeouts**: Automatic retry with exponential backoff
- **SSL certificate issues**: SSL verification disabled by default
- **Large file uploads**: Chunked upload handling

## Logging

All operations are logged to:
- **Console**: Real-time progress updates
- **migration.log**: Detailed log file with timestamps and error details

Log levels include INFO, WARNING, and ERROR messages for comprehensive troubleshooting.

## Resume Capability

If migration is interrupted:
1. The script saves organization ID mappings to `org_mapping.json`
2. On restart, it loads existing mappings to avoid duplicates
3. Existing organizations and datasets are skipped automatically

## Post-Migration Steps

After successful migration, perform these steps on the target CKAN system:

```bash
# Rebuild search index
ckan -c /etc/ckan/default/ckan.ini search-index rebuild

# Update datastore if using DataPusher
ckan -c /etc/ckan/default/ckan.ini datastore set-permissions

# Verify configuration
ckan -c /etc/ckan/default/ckan.ini config-tool
```

## Troubleshooting

### Common Issues

**SSL Certificate Errors**:
- SSL verification is disabled by default
- If needed, certificates can be added to the system trust store

**Permission Errors**:
- Ensure API keys have admin privileges on target system
- Check that organizations exist before migrating datasets

**Large Resource Files**:
- Monitor disk space in the `ckan_migration` directory
- Consider using `--skip-resources` for initial metadata migration

**Network Timeouts**:
- The script includes automatic retry logic
- Adjust network timeout if needed for large files

### Debugging

Enable verbose logging by checking the `migration.log` file:

```bash
tail -f migration.log
```

## Limitations

- Designed specifically for CKAN 2.8.2 → 2.11.2 migration
- Does not migrate user accounts or permissions
- Custom extensions may require additional handling
- Very large files (>1GB) may require manual transfer

## Security Considerations

- Store configuration files securely (contains API keys)
- Use HTTPS URLs when possible
- Rotate API keys after migration
- Review permissions on migrated content

## Performance Tips

- Run migration during low-traffic periods
- Use `--skip-resources` for initial metadata migration
- Monitor target system resources during migration
- Consider migrating organizations first, then datasets in batches

## Examples

### Complete Migration
```bash
# Full migration with custom config
python3 ckan_migrator.py production_config.json --yes
```

### Organization-Specific Migration
```bash
# Migrate specific organizations and all their datasets
python3 ckan_migrator.py --orgs "health-department" "education-ministry"
```

### Metadata-Only Migration
```bash
# Migrate all metadata without resource files
python3 ckan_migrator.py --skip-resources
```

### Testing Migration
```bash
# Test with a single dataset
python3 ckan_migrator.py --skip-orgs --datasets "test-dataset-123"
```

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

This tool is provided as-is for CKAN migration purposes. Use at your own risk and always backup your data before migration.

## Support

For issues and questions:
1. Check the `migration.log` file for detailed error information
2. Review the troubleshooting section above
3. Open an issue with relevant log excerpts and configuration details (redacted)

---

**⚠️ Important**: Always test the migration on a staging environment before running on production systems. Backup both source and target systems before beginning migration.
