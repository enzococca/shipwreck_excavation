# Shipwreck Excavation Plugin - Supabase Installation Guide

## Overview
This version of the Shipwreck Excavation plugin has been migrated from SQLite to Supabase for better cloud synchronization and multi-user support.

## Prerequisites

1. **QGIS 3.16 or higher**
2. **Python 3.7 or higher**
3. **Supabase account and project** (https://supabase.com)

## Installation Steps

### 1. Install Python Dependencies

#### Option A: Automatic Installation
```bash
python3 install_dependencies.py
```

#### Option B: Manual Installation
```bash
pip install -r requirements.txt
```

### 2. Core Dependencies
The following packages MUST be installed:
- `supabase>=2.0.0` - Supabase Python client
- `Pillow>=9.0.0` - Image processing
- `reportlab>=3.6.0` - PDF report generation
- `qrcode>=7.3.0` - QR code generation
- `python-dateutil>=2.8.0` - Date utilities
- `requests>=2.28.0` - HTTP requests

### 3. Optional Dependencies
These enhance functionality but are not required:
- `python-telegram-bot>=20.0` - Telegram bot for field data collection
- `opencv-python>=4.5.0` - Video processing and analysis
- `vtk>=9.0.0` - 3D visualization and rendering
- `pandas>=1.3.0` - Excel export functionality
- Google API packages - Cloud backup features

## Supabase Configuration

### 1. Database Setup
Run the following SQL scripts in your Supabase SQL Editor:

1. **Main schema**: `database/schema.sql`
2. **Migration fixes**: `add_missing_divelog_columns.sql`
3. **Signature table**: `create_signatures_table.sql`

### 2. Configure Connection
In QGIS:
1. Open the plugin
2. Go to Settings > Database
3. Enter your Supabase credentials:
   - URL: `https://YOUR_PROJECT.supabase.co`
   - API Key: Your project's anon key

## Known Issues with SQLite Code

The plugin still contains legacy SQLite code in several files. These are being progressively migrated:

### Files with SQLite dependencies:
- `sync/telegram_sync.py` - Uses SQLite for Telegram sync
- `signed_divelog_generator.py` - Direct SQLite connections
- `database/database_manager.py` - Legacy SQLite manager

### SQL Compatibility Issues:
- **JOIN queries**: Being replaced with separate queries
- **strftime()**: Not supported in PostgreSQL
- **julianday()**: Not supported in PostgreSQL
- **AUTOINCREMENT**: Use SERIAL in PostgreSQL
- **INSERT OR REPLACE**: Use INSERT ... ON CONFLICT

## Telegram Bot Setup (Optional)

If using the Telegram bots for field data collection:

1. **Data Collection Bot**:
   ```bash
   export TELEGRAM_BOT_TOKEN="YOUR_DATA_BOT_TOKEN"
   export BOT_MEDIA_DIR="/path/to/media/folder"
   ```

2. **Signature Bot**:
   ```bash
   export TELEGRAM_BOT_TOKEN_SIGN="YOUR_SIGNATURE_BOT_TOKEN"
   ```

3. Run both bots:
   ```bash
   ./start_data_bot_supabase.sh
   ```

## Troubleshooting

### Import Errors
If you get import errors, ensure all dependencies are installed:
```bash
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

### Database Connection Issues
1. Check your Supabase URL and API key
2. Ensure your Supabase project is active
3. Check Row Level Security (RLS) policies

### Missing Columns Error
Run the migration scripts in Supabase SQL Editor:
```sql
-- Add missing columns
ALTER TABLE dive_logs ADD COLUMN IF NOT EXISTS avg_depth REAL;
-- etc...
```

## Support

For issues or questions:
1. Check the logs in QGIS Python Console
2. Review error messages in the plugin interface
3. Ensure all dependencies are correctly installed

## Migration Status

✅ Completed:
- Main database operations (CRUD)
- Media management
- Find/Site/Worker management
- Dive log operations
- Cost tracking

⚠️ In Progress:
- Full JOIN query replacement
- Date function compatibility
- Telegram sync with Supabase

❌ Not Migrated:
- Direct SQLite file operations
- Some complex report queries
- Legacy sync features