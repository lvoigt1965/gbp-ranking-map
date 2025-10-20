#!/usr/bin/env python3
"""
GBP Ranking Analysis Generator

This script:
1. Calls DataForSEO API to fetch GBP rankings across a grid
2. Generates a JSON file with the results
3. Pushes the JSON to GitHub
4. Stores metadata in MySQL database

Usage:
    python generate_analysis.py --lat 40.7128 --lon -74.0060 --keyword "restaurant" --points 9 --distance 1
"""

import os
import json
import uuid
import argparse
import base64
from datetime import datetime
from typing import Dict, List, Optional
import requests
import mysql.connector
from mysql.connector import Error

# Configuration - set these as environment variables or in a config file
DATAFORSEO_LOGIN = os.getenv('DATAFORSEO_LOGIN')
DATAFORSEO_PASSWORD = os.getenv('DATAFORSEO_PASSWORD')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_REPO = os.getenv('GITHUB_REPO', 'lvoigt1965/gbp-ranking-map')
MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3306'))
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'gbp_rankings')
GITHUB_PAGES_URL = f"https://{GITHUB_REPO.split('/')[0]}.github.io/{GITHUB_REPO.split('/')[1]}"


def calculate_grid_dimensions(num_points: int) -> tuple:
    """Calculate optimal rectangular grid dimensions."""
    import math
    rows = int(math.floor(math.sqrt(num_points)))
    cols = int(math.ceil(num_points / rows))
    return rows, cols


def generate_grid_points(center_lat: float, center_lon: float, num_points: int, distance_km: float) -> List[Dict]:
    """Generate grid of lat/lon points."""
    import math
    
    rows, cols = calculate_grid_dimensions(num_points)
    offset = distance_km / 111  # Approximate: 1 degree latitude = 111km
    points = []
    
    start_row = -(rows - 1) / 2
    start_col = -(cols - 1) / 2
    
    point_count = 0
    for i in range(rows):
        if point_count >= num_points:
            break
        for j in range(cols):
            if point_count >= num_points:
                break
            
            lat = center_lat + (start_row + i) * offset
            lon = center_lon + (start_col + j) * offset / math.cos(math.radians(center_lat))
            
            points.append({
                'id': point_count,
                'lat': round(lat, 6),
                'lon': round(lon, 6)
            })
            point_count += 1
    
    return points


def call_dataforseo_api(lat: float, lon: float, keyword: str) -> Optional[List[Dict]]:
    """Call DataForSEO API for a single location."""
    url = 'https://api.dataforseo.com/v3/business_data/google/my_business_info/live'
    
    headers = {
        'Authorization': 'Basic ' + base64.b64encode(
            f"{DATAFORSEO_LOGIN}:{DATAFORSEO_PASSWORD}".encode()
        ).decode(),
        'Content-Type': 'application/json'
    }
    
    payload = [{
        'language_code': 'en',
        'location_coordinate': f'{lat},{lon}',
        'keyword': keyword,
        'depth': 20
    }]
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if data.get('tasks') and data['tasks'][0].get('result'):
            return data['tasks'][0]['result'][0].get('items', [])
        return []
    except Exception as e:
        print(f"Error calling DataForSEO API: {e}")
        return None


def generate_analysis(center_lat: float, center_lon: float, keyword: str, num_points: int, distance_km: float) -> Dict:
    """Generate complete ranking analysis."""
    analysis_id = str(uuid.uuid4())
    print(f"Generating analysis: {analysis_id}")
    
    # Generate grid points
    grid_points = generate_grid_points(center_lat, center_lon, num_points, distance_km)
    print(f"Generated {len(grid_points)} grid points")
    
    # Collect all businesses and rankings
    all_businesses = {}
    ranking_data = {}
    
    for i, point in enumerate(grid_points):
        print(f"Fetching data for point {i+1}/{len(grid_points)}...")
        items = call_dataforseo_api(point['lat'], point['lon'], keyword)
        
        if items is None:
            continue
        
        for index, item in enumerate(items):
            biz_id = item.get('place_id') or item.get('cid')
            if not biz_id:
                continue
            
            # Store business info
            if biz_id not in all_businesses:
                all_businesses[biz_id] = {
                    'id': biz_id,
                    'title': item.get('title'),
                    'address': item.get('address'),
                    'rating': item.get('rating', {}).get('value'),
                    'reviews': item.get('rating', {}).get('votes_count')
                }
            
            # Store ranking for this grid point
            if biz_id not in ranking_data:
                ranking_data[biz_id] = {}
            ranking_data[biz_id][point['id']] = index + 1
    
    # Build result
    result = {
        'analysis_id': analysis_id,
        'metadata': {
            'center_lat': center_lat,
            'center_lon': center_lon,
            'keyword': keyword,
            'num_points': num_points,
            'distance_km': distance_km,
            'created_at': datetime.utcnow().isoformat() + 'Z'
        },
        'grid_points': grid_points,
        'businesses': list(all_businesses.values()),
        'rankings': ranking_data
    }
    
    return result


def push_to_github(analysis_id: str, data: Dict) -> str:
    """Push JSON file to GitHub."""
    print(f"Pushing to GitHub...")
    
    filename = f'data/{analysis_id}.json'
    json_content = json.dumps(data, indent=2)
    
    url = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{filename}'
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    payload = {
        'message': f'Add analysis {analysis_id}',
        'content': base64.b64encode(json_content.encode()).decode(),
        'branch': 'main'
    }
    
    response = requests.put(url, json=payload, headers=headers)
    response.raise_for_status()
    
    # Return raw GitHub URL
    raw_url = f'https://raw.githubusercontent.com/{GITHUB_REPO}/main/{filename}'
    print(f"Pushed to: {raw_url}")
    return raw_url


def save_to_mysql(data: Dict, json_url: str) -> None:
    """Save analysis metadata and rankings to MySQL."""
    print(f"Saving to MySQL...")
    
    connection = None
    try:
        connection = mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        
        cursor = connection.cursor()
        
        # Insert analysis metadata
        analysis_query = """
            INSERT INTO analyses 
            (id, center_lat, center_lon, keyword, num_points, distance_km, json_url, businesses_found, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(analysis_query, (
            data['analysis_id'],
            data['metadata']['center_lat'],
            data['metadata']['center_lon'],
            data['metadata']['keyword'],
            data['metadata']['num_points'],
            data['metadata']['distance_km'],
            json_url,
            len(data['businesses']),
            'completed'
        ))
        
        # Insert business rankings
        ranking_query = """
            INSERT INTO business_rankings 
            (analysis_id, business_id, business_name, business_address, business_rating, 
             business_reviews, grid_point_id, grid_lat, grid_lon, ranking_position)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        for business in data['businesses']:
            biz_id = business['id']
            rankings = data['rankings'].get(biz_id, {})
            
            for grid_point in data['grid_points']:
                position = rankings.get(grid_point['id'])
                if position:
                    cursor.execute(ranking_query, (
                        data['analysis_id'],
                        biz_id,
                        business['title'],
                        business['address'],
                        business['rating'],
                        business['reviews'],
                        grid_point['id'],
                        grid_point['lat'],
                        grid_point['lon'],
                        position
                    ))
        
        connection.commit()
        print(f"Saved {cursor.rowcount} ranking records to MySQL")
        
    except Error as e:
        print(f"MySQL Error: {e}")
        if connection:
            connection.rollback()
        raise
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


def main():
    parser = argparse.ArgumentParser(description='Generate GBP ranking analysis')
    parser.add_argument('--lat', type=float, required=True, help='Center latitude')
    parser.add_argument('--lon', type=float, required=True, help='Center longitude')
    parser.add_argument('--keyword', type=str, required=True, help='Search keyword')
    parser.add_argument('--points', type=int, default=9, help='Number of grid points (default: 9)')
    parser.add_argument('--distance', type=float, default=1.0, help='Distance between points in km (default: 1.0)')
    
    args = parser.parse_args()
    
    # Validate environment variables
    required_env = {
        'DATAFORSEO_LOGIN': DATAFORSEO_LOGIN,
        'DATAFORSEO_PASSWORD': DATAFORSEO_PASSWORD,
        'GITHUB_TOKEN': GITHUB_TOKEN,
        'MYSQL_USER': MYSQL_USER,
        'MYSQL_PASSWORD': MYSQL_PASSWORD
    }
    
    missing = [k for k, v in required_env.items() if not v]
    if missing:
        print(f"Error: Missing required environment variables: {', '.join(missing)}")
        return
    
    try:
        # Generate analysis
        print("\n=== Starting Analysis ===")
        data = generate_analysis(
            args.lat, 
            args.lon, 
            args.keyword, 
            args.points, 
            args.distance
        )
        
        print(f"\nFound {len(data['businesses'])} unique businesses")
        
        # Push to GitHub
        json_url = push_to_github(data['analysis_id'], data)
        
        # Save to MySQL
        save_to_mysql(data, json_url)
        
        # Generate shareable URL
        viewer_url = f"{GITHUB_PAGES_URL}/?data={data['analysis_id']}"
        
        print("\n=== Analysis Complete ===")
        print(f"Analysis ID: {data['analysis_id']}")
        print(f"JSON URL: {json_url}")
        print(f"Viewer URL: {viewer_url}")
        print(f"\nShare this URL with your client:")
        print(f"  {viewer_url}")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()