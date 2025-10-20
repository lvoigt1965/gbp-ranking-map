-- GBP Ranking Map Analyzer Database Schema
-- MySQL 5.7+ compatible

-- Main analyses table - tracks each ranking analysis run
CREATE TABLE IF NOT EXISTS analyses (
    id CHAR(36) PRIMARY KEY,  -- UUID format
    center_lat DECIMAL(10, 6) NOT NULL,
    center_lon DECIMAL(10, 6) NOT NULL,
    keyword VARCHAR(255) NOT NULL,
    num_points INT NOT NULL,
    distance_km DECIMAL(5, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    json_url VARCHAR(512) NOT NULL,
    businesses_found INT DEFAULT 0,
    status ENUM('processing', 'completed', 'failed') DEFAULT 'processing',
    error_message TEXT,
    INDEX idx_keyword (keyword),
    INDEX idx_location (center_lat, center_lon),
    INDEX idx_created_at (created_at),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Business rankings table - detailed ranking data for time-series analysis
CREATE TABLE IF NOT EXISTS business_rankings (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    analysis_id CHAR(36) NOT NULL,
    business_id VARCHAR(255) NOT NULL,  -- Google place_id or cid
    business_name VARCHAR(512),
    business_address VARCHAR(1024),
    business_rating DECIMAL(3, 2),
    business_reviews INT,
    grid_point_id INT NOT NULL,
    grid_lat DECIMAL(10, 6) NOT NULL,
    grid_lon DECIMAL(10, 6) NOT NULL,
    ranking_position INT NOT NULL,  -- 1-20 or NULL if not ranked
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (analysis_id) REFERENCES analyses(id) ON DELETE CASCADE,
    INDEX idx_analysis (analysis_id),
    INDEX idx_business (business_id),
    INDEX idx_business_time_series (business_id, created_at),
    INDEX idx_location_keyword (center_lat, center_lon, keyword(100), created_at),
    INDEX idx_ranking_position (ranking_position)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Optional: Create a view for easy time-series queries
CREATE OR REPLACE VIEW business_ranking_history AS
SELECT 
    br.business_id,
    br.business_name,
    a.keyword,
    a.center_lat,
    a.center_lon,
    br.grid_lat,
    br.grid_lon,
    br.ranking_position,
    br.created_at,
    a.id as analysis_id
FROM business_rankings br
JOIN analyses a ON br.analysis_id = a.id
WHERE a.status = 'completed'
ORDER BY br.business_id, br.created_at;

-- Optional: Create a summary view for dashboard
CREATE OR REPLACE VIEW analysis_summary AS
SELECT 
    a.id,
    a.keyword,
    a.center_lat,
    a.center_lon,
    a.num_points,
    a.distance_km,
    a.created_at,
    a.businesses_found,
    a.status,
    COUNT(DISTINCT br.business_id) as unique_businesses,
    AVG(br.ranking_position) as avg_ranking
FROM analyses a
LEFT JOIN business_rankings br ON a.id = br.analysis_id
GROUP BY a.id
ORDER BY a.created_at DESC;