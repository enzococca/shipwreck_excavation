-- Update Supabase schema to include missing columns for sites table
-- Run this in the Supabase SQL Editor

-- Add missing columns to sites table if they don't exist
ALTER TABLE sites 
ADD COLUMN IF NOT EXISTS period_from TEXT,
ADD COLUMN IF NOT EXISTS period_to TEXT,
ADD COLUMN IF NOT EXISTS vessel_type TEXT,
ADD COLUMN IF NOT EXISTS estimated_length DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS estimated_width DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS depth_min DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS depth_max DECIMAL(10,2);

-- Update media_count to be a computed column (optional - for automatic counting)
-- First drop the existing media_count column if it exists
ALTER TABLE sites DROP COLUMN IF EXISTS media_count;

-- Create a function to count media for sites
CREATE OR REPLACE FUNCTION get_site_media_count(site_id INTEGER)
RETURNS INTEGER AS $$
BEGIN
  RETURN (
    SELECT COUNT(DISTINCT mr.media_id)
    FROM media_relations mr
    WHERE mr.related_id = site_id 
    AND mr.related_type = 'site'
  );
END;
$$ LANGUAGE plpgsql;

-- Add media_count as a generated column (PostgreSQL 12+)
-- Note: If your Supabase instance doesn't support generated columns,
-- you can create a view instead or update the count via triggers
ALTER TABLE sites 
ADD COLUMN media_count INTEGER GENERATED ALWAYS AS (get_site_media_count(id)) STORED;

-- Alternative: Create a trigger to update media_count when media_relations changes
-- This is more compatible with older PostgreSQL versions
CREATE OR REPLACE FUNCTION update_site_media_count()
RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'INSERT' OR TG_OP = 'DELETE' OR TG_OP = 'UPDATE' THEN
    -- Update count for affected site
    UPDATE sites 
    SET media_count = (
      SELECT COUNT(DISTINCT mr.media_id)
      FROM media_relations mr
      WHERE mr.related_id = sites.id 
      AND mr.related_type = 'site'
    )
    WHERE id = COALESCE(NEW.related_id, OLD.related_id)
    AND 'site' = COALESCE(NEW.related_type, OLD.related_type);
  END IF;
  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create trigger if using the trigger approach
DROP TRIGGER IF EXISTS update_site_media_count_trigger ON media_relations;
CREATE TRIGGER update_site_media_count_trigger
AFTER INSERT OR UPDATE OR DELETE ON media_relations
FOR EACH ROW
EXECUTE FUNCTION update_site_media_count();

-- Update existing media counts
UPDATE sites 
SET media_count = (
  SELECT COUNT(DISTINCT mr.media_id)
  FROM media_relations mr
  WHERE mr.related_id = sites.id 
  AND mr.related_type = 'site'
);