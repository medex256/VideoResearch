# Project Structure Reorganization Plan

## Current Issues

- Multiple Python utility scripts scattered in project root
- Deployment scripts reference scripts by relative paths
- Project structure lacks clear logical grouping
- Maintenance and navigation difficulties

## Proposed Directory Structure

```
NewPortal/
├── app.py                          # Main Flask application entry point
├── config.py                       # Application configuration
├── models.py                       # Database models
├── services.py                     # Business logic services
├── utils.py                        # Common utilities and decorators
├── requirements.txt                # Python dependencies
├── pytest.ini                     # Test configuration
├── docker-compose.yml             # Docker orchestration
├── Dockerfile                     # Docker image definition
├── README.md                      # Project documentation
├── *.xlsx                         # Data files (kept in root for scripts)
├── awsmadi.pem                    # AWS key (should be moved to secure location)
│
├── blueprints/                    # Flask route blueprints
│   ├── __init__.py
│   ├── main.py
│   ├── api.py
│   └── round2.py
│
├── scripts/                       # Data management and deployment scripts
│   ├── deployment/
│   │   ├── init-db.sh            # Database initialization
│   │   └── setup.bash            # Application setup
│   └── data/
│       ├── load_videos.py        # Video data loading
│       ├── translate_categories.py # Category translation
│       ├── update_video.py       # Video updates
│       └── validate_videos.py    # Video validation
│
├── tools/                         # Development and maintenance tools
│   ├── migrate_to_blueprints.py  # Migration utilities
│   └── locustfile.py             # Load testing
│
├── static/                        # Web assets
│   ├── css/
│   ├── js/
│   └── videos/
│
├── templates/                     # HTML templates
│
├── tests/                         # Test suite
│   ├── __init__.py
│   ├── conftest.py
│   └── test_*.py
│
├── instance/                      # Instance-specific files
│   └── *.db
│
├── migrations/                    # Database migrations
│
└── misc/                         # Miscellaneous files and reports
    └── video_reports/
```

## Files to Move

### scripts/data/ (Data Management Scripts)

- `load_videos.py` → `scripts/data/load_videos.py`
- `translate_categories.py` → `scripts/data/translate_categories.py`
- `update_video.py` → `scripts/data/update_video.py`
- `validate_videos.py` → `scripts/data/validate_videos.py`

### scripts/deployment/ (Deployment Scripts)

- `scripts/init-db.sh` → `scripts/deployment/init-db.sh`
- `scripts/setup.bash` → `scripts/deployment/setup.bash`

### tools/ (Development Tools)

- `migrate_to_blueprints.py` → `tools/migrate_to_blueprints.py`
- `locustfile.py` → `tools/locustfile.py`

## Required Script Updates

### 1. scripts/deployment/init-db.sh

Update Python script paths:

```bash
python scripts/data/load_videos.py
python scripts/data/translate_categories.py
python scripts/data/update_video.py
```

### 2. scripts/deployment/setup.bash

Update Python script paths:

```bash
python scripts/data/load_videos.py
python scripts/data/update_video.py
python scripts/data/translate_categories.py
```

### 3. Docker-related files

Update any references to moved scripts in:

- Dockerfile
- docker-compose.yml

## Benefits of This Structure

1. **Clear Separation of Concerns**

   - Core application files in root
   - Data management scripts grouped together
   - Deployment scripts separated from data scripts
   - Development tools in dedicated directory

2. **Improved Maintainability**

   - Easier to locate specific functionality
   - Clear distinction between production and development tools
   - Logical grouping reduces cognitive load

3. **Better Deployment Management**

   - Deployment scripts clearly separated
   - Data scripts grouped for easier batch operations
   - Environment-specific configurations isolated

4. **Enhanced Security**
   - Sensitive files (like awsmadi.pem) identified for relocation
   - Scripts organized by access requirements

## Migration Steps

1. Create new directory structure
2. Move files to new locations
3. Update import paths in moved files
4. Update deployment script references
5. Test deployment process
6. Update documentation

## Deployment Compatibility Notes

- All deployment scripts will continue to work with path updates
- Docker configuration may need minor adjustments
- Excel files remain in root for easy script access
- No changes to core application structure (blueprints, templates, static)
