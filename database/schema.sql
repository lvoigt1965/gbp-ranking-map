-- GBP Ranking Map Analyzer - MySQL Database Schema

-- Create database (optional - you may already have one)
-- CREATE DATABASE IF NOT EXISTS gbp_rankings CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- USE gbp_rankings;

-- Table to track each analysis run
CREATE TABLE IF NOT EXISTS analyses (
    id CHAR(36) PRIMARY KEY,  -- UUID
    center_lat DECIMAL(10, 6) NOT NULL,
    center_lon DECIMAL(10, 6) NOT NULL,
    keyword VARCHAR(255) NOT NULL,
    num_points INT NOT NULL,
    distance_km DECIMAL(5, 2) NOT NULL,
    grid_rows INT NOT NULL,
    grid_cols INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    json_url TEXT,
    json_filename VARCHAR(255),
    businesses_found INT DEFAULT 0,
    status ENUM('processing', 'completed', 'failed') DEFAULT 'processing',
    error_message TEXT NULL,
    api_calls_made INT DEFAULT 0,
    INDEX idx_location (center_lat, center_lon),
    INDEX idx_keyword (keyword),
    INDEX idx_created_at (created_at),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table to track individual business rankings at each grid point
CREATE TABLE IF NOT EXISTS business_rankings (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    analysis_id CHAR(36) NOT NULL,
    business_id VARCHAR(255) NOT NULL,  -- place_id from Google
    business_name VARCHAR(500),
    business_address TEXT,
    business_rating DECIMAL(2, 1),
    business_reviews INT,
    grid_point_id INT NOT NULL,
    grid_lat DECIMAL(10, 6) NOT NULL,
    grid_lon DECIMAL(10, 6) NOT NULL,
    ranking_position INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (analysis_id) REFERENCES analyses(id) ON DELETE CASCADE,
    INDEX idx_analysis (analysis_id),
    INDEX idx_business (business_id),
    INDEX idx_grid_point (analysis_id, grid_point_id),
    INDEX idx_ranking (ranking_position),
    INDEX idx_time_series (business_id, center_lat, center_lon, keyword, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- View for easy querying of business performance over time
CREATE OR REPLACE VIEW business_performance AS
SELECT 
    br.business_id,
    br.business_name,
    a.keyword,
    a.center_lat,
    a.center_lon,
    a.created_at,
    COUNT(DISTINCT br.grid_point_id) as locations_ranked,
    AVG(br.ranking_position) as avg_ranking,
    MIN(br.ranking_position) as best_ranking,
    MAX(br.ranking_position) as worst_ranking,
    a.id as analysis_id
FROM business_rankings br
JOIN analyses a ON br.analysis_id = a.id
WHERE a.status = 'completed'
GROUP BY br.business_id, br.business_name, a.keyword, a.center_lat, a.center_lon, a.created_at, a.id;

-- View for analysis summary
CREATE OR REPLACE VIEW analysis_summary AS
SELECT 
    a.id,
    a.center_lat,
    a.center_lon,
    a.keyword,
    a.num_points,
    a.distance_km,
    a.created_at,
    a.status,
    a.businesses_found,
    a.json_url,
    COUNT(DISTINCT br.business_id) as unique_businesses,
    AVG(br.ranking_position) as avg_ranking_position
FROM analyses a
LEFT JOIN business_rankings br ON a.id = br.analysis_id
GROUP BY a.id, a.center_lat, a.center_lon, a.keyword, a.num_points, 
         a.distance_km, a.created_at, a.status, a.businesses_found, a.json_url;

-- Optional: Table for tracking clients/customers (for future use)
CREATE TABLE IF NOT EXISTS clients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    company VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE KEY unique_email (email),
    INDEX idx_name (name),
    INDEX idx_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Optional: Link analyses to clients
CREATE TABLE IF NOT EXISTS client_analyses (
    client_id INT NOT NULL,
    analysis_id CHAR(36) NOT NULL,
    shared_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    PRIMARY KEY (client_id, analysis_id),
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
    FOREIGN KEY (analysis_id) REFERENCES analyses(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;