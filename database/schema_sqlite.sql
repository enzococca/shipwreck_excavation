-- Shipwreck Excavation Database Schema (SQLite version)
-- Standard SQLite database for archaeological excavation management
-- Geometry stored as WKT text

-- Sites table (main shipwreck site)
CREATE TABLE sites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_code TEXT UNIQUE NOT NULL,
    site_name TEXT NOT NULL,
    discovery_date DATE,
    period_from TEXT,
    period_to TEXT,
    vessel_type TEXT,
    estimated_length REAL,
    estimated_width REAL,
    depth_min REAL,
    depth_max REAL,
    description TEXT,
    status TEXT DEFAULT 'active',
    geom TEXT, -- Store geometry as WKT
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sites_code ON sites(site_code);

-- Excavation areas/trenches
CREATE TABLE excavation_areas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL,
    area_code TEXT NOT NULL,
    area_name TEXT,
    excavation_start DATE,
    excavation_end DATE,
    area_type TEXT, -- trench, grid, test pit
    depth REAL,
    notes TEXT,
    geom TEXT, -- Store geometry as WKT
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (site_id) REFERENCES sites(id),
    UNIQUE(site_id, area_code)
);

-- Finds/Materials table
CREATE TABLE finds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL,
    area_id INTEGER,
    find_number TEXT NOT NULL,
    material_type TEXT, -- ceramic, metal, wood, glass, etc.
    object_type TEXT, -- plate, coin, tool, etc.
    description TEXT,
    condition TEXT, -- excellent, good, fair, poor, fragment
    period TEXT,
    dating_info TEXT,
    quantity INTEGER DEFAULT 1,
    weight REAL,
    dimensions TEXT,
    conservation_status TEXT,
    storage_location TEXT,
    finder_name TEXT,
    find_date DATE,
    depth REAL,
    context_description TEXT,
    notes TEXT,
    geom TEXT, -- Store geometry as WKT
    telegram_sync BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (site_id) REFERENCES sites(id),
    FOREIGN KEY (area_id) REFERENCES excavation_areas(id)
);

CREATE INDEX idx_finds_number ON finds(find_number);
CREATE INDEX idx_finds_type ON finds(material_type, object_type);

-- Media files table
CREATE TABLE media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    media_type TEXT NOT NULL, -- photo, video, 3d_model
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    mime_type TEXT,
    description TEXT,
    photographer TEXT,
    capture_date TIMESTAMP,
    telegram_message_id TEXT,
    telegram_sync BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Media relationships (polymorphic)
CREATE TABLE media_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    media_id INTEGER NOT NULL,
    related_type TEXT NOT NULL, -- site, find, dive, etc.
    related_id INTEGER NOT NULL,
    relation_type TEXT DEFAULT 'documentation', -- documentation, before, after, detail
    sort_order INTEGER DEFAULT 0,
    FOREIGN KEY (media_id) REFERENCES media(id) ON DELETE CASCADE
);

CREATE INDEX idx_media_relations ON media_relations(related_type, related_id);

-- Dive logs
CREATE TABLE dive_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL,
    dive_number TEXT NOT NULL,
    dive_date DATE NOT NULL,
    dive_start TIME,
    dive_end TIME,
    max_depth REAL,
    avg_depth REAL,
    water_temp REAL,
    visibility REAL,
    current_strength TEXT,
    weather_conditions TEXT,
    dive_objectives TEXT,
    work_completed TEXT,
    findings_summary TEXT,
    equipment_used TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (site_id) REFERENCES sites(id)
);

-- Dive team members
CREATE TABLE dive_team (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dive_id INTEGER NOT NULL,
    worker_id INTEGER NOT NULL,
    role TEXT, -- dive supervisor, archaeologist, photographer, safety diver
    bottom_time INTEGER, -- minutes
    decompression_time INTEGER,
    air_consumed INTEGER, -- bar
    notes TEXT,
    FOREIGN KEY (dive_id) REFERENCES dive_logs(id),
    FOREIGN KEY (worker_id) REFERENCES workers(id)
);

-- Workers/Staff
CREATE TABLE workers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    worker_code TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT,
    qualification TEXT,
    dive_certification TEXT,
    phone TEXT,
    email TEXT,
    telegram_username TEXT,
    emergency_contact TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Work sessions (for cost tracking)
CREATE TABLE work_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    worker_id INTEGER NOT NULL,
    site_id INTEGER NOT NULL,
    work_date DATE NOT NULL,
    start_time TIME,
    end_time TIME,
    hours_worked REAL,
    work_type TEXT, -- diving, processing, documentation, etc.
    rate_per_hour REAL,
    total_payment REAL,
    payment_status TEXT DEFAULT 'pending',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (worker_id) REFERENCES workers(id),
    FOREIGN KEY (site_id) REFERENCES sites(id)
);

-- Costs/Expenses
CREATE TABLE expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL,
    expense_date DATE NOT NULL,
    category TEXT NOT NULL, -- equipment, boat, fuel, accommodation, etc.
    description TEXT,
    supplier TEXT,
    amount REAL NOT NULL,
    currency TEXT DEFAULT 'IDR',
    payment_method TEXT,
    receipt_number TEXT,
    approved_by TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (site_id) REFERENCES sites(id)
);

-- Telegram sync queue
CREATE TABLE telegram_sync_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_data TEXT NOT NULL, -- JSON
    message_type TEXT NOT NULL, -- find, photo, location, etc.
    user_id TEXT,
    username TEXT,
    chat_id TEXT,
    processed BOOLEAN DEFAULT 0,
    processed_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Settings table
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Views for common queries
CREATE VIEW finds_with_media AS
SELECT 
    f.*,
    COUNT(DISTINCT mr.media_id) as media_count
FROM finds f
LEFT JOIN media_relations mr ON mr.related_type = 'find' AND mr.related_id = f.id
GROUP BY f.id;

CREATE VIEW site_summary AS
SELECT 
    s.*,
    COUNT(DISTINCT f.id) as total_finds,
    COUNT(DISTINCT ea.id) as total_areas,
    COUNT(DISTINCT dl.id) as total_dives
FROM sites s
LEFT JOIN finds f ON f.site_id = s.id
LEFT JOIN excavation_areas ea ON ea.site_id = s.id
LEFT JOIN dive_logs dl ON dl.site_id = s.id
GROUP BY s.id;

-- Default settings
INSERT INTO settings (key, value) VALUES 
    ('language', 'en'),
    ('date_format', 'yyyy-MM-dd'),
    ('coordinate_format', 'decimal'),
    ('default_epsg', '32648');