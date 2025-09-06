
-- Add new fields from Excel structure
ALTER TABLE finds ADD COLUMN IF NOT EXISTS inv_no INTEGER;
ALTER TABLE finds ADD COLUMN IF NOT EXISTS section TEXT;
ALTER TABLE finds ADD COLUMN IF NOT EXISTS su TEXT;
ALTER TABLE finds ADD COLUMN IF NOT EXISTS storage_location TEXT;
ALTER TABLE finds ADD COLUMN IF NOT EXISTS year INTEGER;
ALTER TABLE finds ADD COLUMN IF NOT EXISTS quantity INTEGER;
ALTER TABLE finds ADD COLUMN IF NOT EXISTS dimensions TEXT;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_finds_inv_no ON finds(inv_no);
CREATE INDEX IF NOT EXISTS idx_finds_section ON finds(section);
CREATE INDEX IF NOT EXISTS idx_finds_year ON finds(year);
CREATE INDEX IF NOT EXISTS idx_finds_storage ON finds(storage_location);
