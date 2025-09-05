# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
This is a QGIS plugin for archaeological excavation management of underwater shipwrecks. It includes finds management, media handling, dive logs, worker management, cost tracking, and Telegram bot integration for field data collection.

## Architecture

### Core Components
- **Database Layer**: Factory pattern supporting both PostgreSQL/Supabase and SQLite backends
  - `database/database_factory.py`: Selects appropriate database manager
  - `database/pg_database_manager.py`: PostgreSQL/Supabase implementation
  - `database/supabase_database_manager.py`: Direct Supabase client implementation
  - `database/database_manager.py`: Legacy SQLite implementation (being phased out)

- **UI Layer**: PyQt5-based dialogs and widgets
  - `ui/main_dialog.py`: Central dialog orchestrating all features
  - Specialized widgets for finds, media, dive logs, costs, workers, sites

- **Sync Layer**: Cloud and field data synchronization
  - `sync/telegram_sync.py`: Telegram bot integration for offline field collection
  - `sync/cloud_sync_manager.py`: Google Drive media synchronization

- **Plugin Integration**: QGIS plugin infrastructure
  - `shipwreck_excavation.py`: Main plugin class
  - `__init__.py`: Plugin factory loader

## Key Development Commands

### Plugin Reload in QGIS
```python
# Execute in QGIS Python Console:
exec(open('/Users/enzo/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/shipwreck_excavation/reload_plugin.py').read())
```

### Dependency Installation
```bash
# Install all dependencies
python3 install_dependencies.py

# Or manually
pip install -r requirements.txt
```

### Testing
```bash
# Test imports and dependencies
python3 test_dependencies.py

# Simple plugin test
python3 simple_test.py

# Full plugin test (requires QGIS environment)
python3 test_plugin.py
```

### Telegram Bots (if configured)
```bash
# Start data collection bot
./start_data_bot_supabase.sh

# Generate signed dive logs
python3 signed_divelog_generator.py
```

## Database Configuration

### Current Setup (PostgreSQL/Supabase)
The plugin is configured for Supabase with these credentials:
- Host: `db.bqlmbmkffhzayinboanu.supabase.co`
- Database: `postgres`
- Port: 5432
- User: `postgres`

Connection settings are managed through:
1. QGIS Plugin UI: Settings ’ Database Settings
2. Environment variables for Telegram bots

### Schema Management
- Main schema: `database/schema.sql`
- SQLite schema (legacy): `database/schema_sqlite.sql`
- Apply migrations in Supabase SQL Editor when updating schema

## Important Migration Notes

### SQLite to PostgreSQL Migration Status
The codebase is transitioning from SQLite to PostgreSQL/Supabase. Be aware:

**Completed**:
- Main CRUD operations
- Media management
- Find/Site/Worker management
- Dive logs and cost tracking

**In Progress**:
- JOIN query replacements (PostgreSQL syntax differences)
- Date function compatibility (strftime() ’ PostgreSQL equivalents)
- Telegram sync with Supabase backend

**Legacy SQLite Code Locations**:
- `sync/telegram_sync.py`: Still uses SQLite for local caching
- `signed_divelog_generator.py`: Direct SQLite connections
- `database/database_manager.py`: Being replaced by pg_database_manager.py

### SQL Compatibility Issues to Watch
- `strftime()` ’ Use PostgreSQL date functions
- `julianday()` ’ Use PostgreSQL interval calculations
- `AUTOINCREMENT` ’ Use `SERIAL` or `IDENTITY`
- `INSERT OR REPLACE` ’ Use `INSERT ... ON CONFLICT`

## Media Storage
Media files are stored on Google Drive and referenced by path in the database. The plugin handles:
- Automatic path resolution
- Thumbnail generation
- Video playback through OpenCV
- 3D model viewing (if VTK installed)

## Internationalization
The plugin supports English and Indonesian languages:
- Translation files: `i18n/` directory
- Manager: `core/i18n_manager.py`
- Language switching through QGIS settings

## Development Workflow

1. Make changes to the plugin code
2. Reload plugin in QGIS using the reload script
3. Test functionality through QGIS interface
4. For database changes, update both PostgreSQL and SQLite schemas
5. Test Telegram bot integration separately if modifying sync features

## Critical Files to Understand

- `ui/main_dialog.py`: Entry point for all UI interactions
- `database/database_factory.py`: Database backend selection logic
- `shipwreck_excavation.py`: QGIS plugin lifecycle management
- `sync/telegram_sync.py`: Field data collection bot implementation

## Environment-Specific Notes

- Plugin directory: `/Users/enzo/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/shipwreck_excavation/`
- Media storage configured for Google Drive integration
- Telegram bots require separate environment configuration