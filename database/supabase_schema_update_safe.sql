-- Safe Update for Supabase schema - adds missing columns for sites table
-- This version uses a simpler approach without generated columns

-- Step 1: Add missing columns to sites table if they don't exist
ALTER TABLE sites 
ADD COLUMN IF NOT EXISTS period_from TEXT,
ADD COLUMN IF NOT EXISTS period_to TEXT,
ADD COLUMN IF NOT EXISTS vessel_type TEXT,
ADD COLUMN IF NOT EXISTS estimated_length DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS estimated_width DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS depth_min DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS depth_max DECIMAL(10,2);

-- Step 2: Ensure media_count column exists (as a regular column, not generated)
ALTER TABLE sites 
ADD COLUMN IF NOT EXISTS media_count INTEGER DEFAULT 0;

-- Step 3: Create function to update media count for a specific site
CREATE OR REPLACE FUNCTION update_site_media_count_for_id(site_id_param INTEGER)
RETURNS VOID AS $$
BEGIN
  UPDATE sites 
  SET media_count = (
    SELECT COUNT(DISTINCT mr.media_id)
    FROM media_relations mr
    WHERE mr.related_id = site_id_param 
    AND mr.related_type = 'site'
  )
  WHERE id = site_id_param;
END;
$$ LANGUAGE plpgsql;

-- Step 4: Create trigger function to update media count when media_relations changes
CREATE OR REPLACE FUNCTION trigger_update_site_media_count()
RETURNS TRIGGER AS $$
BEGIN
  -- Handle INSERT
  IF TG_OP = 'INSERT' THEN
    IF NEW.related_type = 'site' THEN
      PERFORM update_site_media_count_for_id(NEW.related_id);
    END IF;
    RETURN NEW;
  -- Handle DELETE
  ELSIF TG_OP = 'DELETE' THEN
    IF OLD.related_type = 'site' THEN
      PERFORM update_site_media_count_for_id(OLD.related_id);
    END IF;
    RETURN OLD;
  -- Handle UPDATE
  ELSIF TG_OP = 'UPDATE' THEN
    -- If the site changed, update both old and new
    IF OLD.related_type = 'site' THEN
      PERFORM update_site_media_count_for_id(OLD.related_id);
    END IF;
    IF NEW.related_type = 'site' AND NEW.related_id != OLD.related_id THEN
      PERFORM update_site_media_count_for_id(NEW.related_id);
    END IF;
    RETURN NEW;
  END IF;
END;
$$ LANGUAGE plpgsql;

-- Step 5: Create trigger (drop first if exists to avoid conflicts)
DROP TRIGGER IF EXISTS update_site_media_count_trigger ON media_relations;

CREATE TRIGGER update_site_media_count_trigger
AFTER INSERT OR UPDATE OR DELETE ON media_relations
FOR EACH ROW
EXECUTE FUNCTION trigger_update_site_media_count();

-- Step 6: Update all existing site media counts
UPDATE sites 
SET media_count = (
  SELECT COUNT(DISTINCT mr.media_id)
  FROM media_relations mr
  WHERE mr.related_id = sites.id 
  AND mr.related_type = 'site'
);

-- Step 7: Verify the update (optional - you can comment this out)
SELECT id, site_code, site_name, media_count 
FROM sites 
ORDER BY id;