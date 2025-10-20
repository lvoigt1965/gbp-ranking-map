#!/usr/bin/env python3
"""
GBP Ranking Map Analyzer - Data Generator
Generates ranking data and stores it for public viewing
"""

import os
import json
import uuid
import base64
import requests
import mysql.connector
from datetime import datetime
from typing import Dict, List, Tuple
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class GBPAnalysisGenerator:
    def __init__(self):
        # DataForSEO credentials
        self.dfs_login = os.getenv('DATAFORSEO_LOGIN')
        self.dfs_password = os.getenv('DATAFORSEO_PASSWORD')
        
        # GitHub credentials
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.github_repo = os.getenv('GITHUB_REPO', 'lvoigt1965/gbp-ranking-map')
        
        # MySQL credentials
        self.db_config = {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'user': os.getenv('MYSQL_USER'),
            'password': os.getenv('MYSQL_PASSWORD'),
            'database': os.getenv('MYSQL_DATABASE', 'gbp_rankings')
        }
        
        # Base URL for viewing
        self.base_url = os.getenv('BASE_URL', 'https://lvoigt1965.github.io/gbp-ranking-map/')
        
    def calculate_grid_dimensions(self, num_points: int) -> Tuple[int, int]:
        """Calculate optimal rectangular grid dimensions"""
        import math
        sqrt = math.sqrt(num_points)
        rows = math.floor(sqrt)
        cols = math.ceil(num_points / rows)
        return rows, cols
    
    def calculate_offset(self, distance_km: float) -> float:
        """Calculate lat/lon offset for distance in km"""
        return distance_km / 111  # Approximate: 1 degree latitude = 111km
    
    def generate_grid_points(self, center_lat: float, center_lon: float, 
                            num_points: int, distance_km: float) -> List[Dict]:
        """Generate grid points for analysis"""
        import math
        rows, cols = self.calculate_grid_dimensions(num_points)
        offset = self.calculate_offset(distance_km)
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
                lon = center_lon + (start_col + j) * offset / math.cos(center_lat * math.pi / 180)
                
                points.append({
                    'id': point_count,
                    'lat': round(lat, 6),
                    'lon': round(lon, 6)
                })
                point_count += 1
        
        return points
    
    def call_dataforseo_api(self, lat: float, lon: float, keyword: str) -> Dict:
        """Call DataForSEO Business Data API"""
        url = 'https://api.dataforseo.com/v3/business_data/google/my_business_info/live'
        
        auth = base64.b64encode(f"{self.dfs_login}:{self.dfs_password}".encode()).decode()
        headers = {
            'Authorization': f'Basic {auth}',
            'Content-Type': 'application/json'
        }
        
        payload = [{
            'language_code': 'en',
            'location_coordinate': f'{lat},{lon}',
            'keyword': keyword,
            'depth': 20
        }]
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        return response.json()
    
    def process_api_response(self, data: Dict, point_id: int) -> List[Dict]:
        """Extract business rankings from API response"""
        businesses = []
        
        if data.get('tasks') and data['tasks'][0].get('result'):
            items = data['tasks'][0]['result'][0].get('items', [])
            
            for index, item in enumerate(items):
                biz_id = item.get('place_id') or item.get('cid')
                if not biz_id:
                    continue
                
                businesses.append({
                    'business_id': biz_id,
                    'business_name': item.get('title'),
                    'business_address': item.get('address'),
                    'business_rating': item.get('rating', {}).get('value'),
                    'business_reviews': item.get('rating', {}).get('votes_count'),
                    'grid_point_id': point_id,
                    'ranking_position': index + 1
                })
        
        return businesses
    
    def run_analysis(self, center_lat: float, center_lon: float, keyword: str,
                    num_points: int, distance_km: float) -> str:
        """Run complete analysis and return UUID"""
        
        analysis_id = str(uuid.uuid4())
        print(f"Starting analysis: {analysis_id}")
        print(f"Location: ({center_lat}, {center_lon})")
        print(f"Keyword: {keyword}")
        print(f"Grid: {num_points} points, {distance_km}km spacing")
        
        # Generate grid
        grid_points = self.generate_grid_points(center_lat, center_lon, num_points, distance_km)
        rows, cols = self.calculate_grid_dimensions(num_points)
        
        # Initialize database record
        conn = mysql.connector.connect(**self.db_config)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO analyses (id, center_lat, center_lon, keyword, num_points, 
                                distance_km, grid_rows, grid_cols, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (analysis_id, center_lat, center_lon, keyword, num_points, 
              distance_km, rows, cols, 'processing'))
        conn.commit()
        
        # Collect all data
        all_businesses = {}
        all_rankings = []
        api_calls = 0
        
        try:
            for point in grid_points:
                print(f"Querying point {point['id'] + 1}/{len(grid_points)}...", end=' ')
                
                # Call API
                response = self.call_dataforseo_api(point['lat'], point['lon'], keyword)
                api_calls += 1
                
                # Process results
                businesses = self.process_api_response(response, point['id'])
                
                for biz in businesses:
                    biz_id = biz['business_id']
                    
                    # Track unique businesses
                    if biz_id not in all_businesses:
                        all_businesses[biz_id] = {
                            'id': biz_id,
                            'title': biz['business_name'],
                            'address': biz['business_address'],
                            'rating': biz['business_rating'],
                            'reviews': biz['business_reviews']
                        }
                    
                    # Store ranking data
                    all_rankings.append({
                        'analysis_id': analysis_id,
                        'business_id': biz_id,
                        'business_name': biz['business_name'],
                        'business_address': biz['business_address'],
                        'business_rating': biz['business_rating'],
                        'business_reviews': biz['business_reviews'],
                        'grid_point_id': point['id'],
                        'grid_lat': point['lat'],
                        'grid_lon': point['lon'],
                        'ranking_position': biz['ranking_position']
                    })
                
                print(f"Found {len(businesses)} businesses")
            
            # Create JSON output
            output_data = {
                'analysis_id': analysis_id,
                'metadata': {
                    'center_lat': center_lat,
                    'center_lon': center_lon,
                    'keyword': keyword,
                    'num_points': num_points,
                    'distance_km': distance_km,
                    'grid_rows': rows,
                    'grid_cols': cols,
                    'created_at': datetime.utcnow().isoformat(),
                    'api_calls_made': api_calls
                },
                'grid_points': grid_points,
                'businesses': list(all_businesses.values()),
                'rankings': {}
            }
            
            # Organize rankings by business
            for ranking in all_rankings:
                biz_id = ranking['business_id']
                if biz_id not in output_data['rankings']:
                    output_data['rankings'][biz_id] = {}
                output_data['rankings'][biz_id][ranking['grid_point_id']] = ranking['ranking_position']
            
            # Save to GitHub
            json_filename = f"{analysis_id}.json"
            json_url = self.push_to_github(json_filename, output_data)
            
            # Insert rankings into database
            if all_rankings:
                cursor.executemany("""
                    INSERT INTO business_rankings 
                    (analysis_id, business_id, business_name, business_address,
                     business_rating, business_reviews, grid_point_id, 
                     grid_lat, grid_lon, ranking_position)
                    VALUES (%(analysis_id)s, %(business_id)s, %(business_name)s, 
                            %(business_address)s, %(business_rating)s, %(business_reviews)s,
                            %(grid_point_id)s, %(grid_lat)s, %(grid_lon)s, %(ranking_position)s)
                """, all_rankings)
            
            # Update analysis record
            cursor.execute("""
                UPDATE analyses 
                SET status = 'completed', 
                    json_url = %s,
                    json_filename = %s,
                    businesses_found = %s,
                    api_calls_made = %s
                WHERE id = %s
            """, (json_url, json_filename, len(all_businesses), api_calls, analysis_id))
            
            conn.commit()
            
            print(f"\n✓ Analysis complete!")
            print(f"  UUID: {analysis_id}")
            print(f"  Businesses found: {len(all_businesses)}")
            print(f"  Total rankings: {len(all_rankings)}")
            print(f"  API calls: {api_calls}")
            
            return analysis_id
            
        except Exception as e:
            # Update status to failed
            cursor.execute("""
                UPDATE analyses 
                SET status = 'failed', 
                    error_message = %s,
                    api_calls_made = %s
                WHERE id = %s
            """, (str(e), api_calls, analysis_id))
            conn.commit()
            raise
        
        finally:
            cursor.close()
            conn.close()
    
    def push_to_github(self, filename: str, data: Dict) -> str:
        """Push JSON file to GitHub repository"""
        
        path = f"data/{filename}"
        content = json.dumps(data, indent=2)
        
        # GitHub API endpoint
        url = f"https://api.github.com/repos/{self.github_repo}/contents/{path}"
        
        headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # Check if file exists
        response = requests.get(url, headers=headers)
        
        payload = {
            'message': f'Add analysis data: {filename}',
            'content': base64.b64encode(content.encode()).decode()
        }
        
        # If file exists, include sha for update
        if response.status_code == 200:
            payload['sha'] = response.json()['sha']
        
        # Create or update file
        response = requests.put(url, headers=headers, json=payload)
        response.raise_for_status()
        
        # Return raw GitHub URL
        return f"https://raw.githubusercontent.com/{self.github_repo}/main/{path}"
    
    def get_viewer_url(self, analysis_id: str) -> str:
        """Generate shareable viewer URL"""
        return f"{self.base_url}?data={analysis_id}"


def main():
    parser = argparse.ArgumentParser(description='Generate GBP ranking analysis')
    parser.add_argument('--lat', type=float, required=True, help='Center latitude')
    parser.add_argument('--lon', type=float, required=True, help='Center longitude')
    parser.add_argument('--keyword', type=str, required=True, help='Search keyword')
    parser.add_argument('--points', type=int, default=9, help='Number of grid points (default: 9)')
    parser.add_argument('--distance', type=float, default=1.0, help='Distance between points in km (default: 1.0)')
    
    args = parser.parse_args()
    
    # Create generator
    generator = GBPAnalysisGenerator()
    
    # Run analysis
    try:
        analysis_id = generator.run_analysis(
            center_lat=args.lat,
            center_lon=args.lon,
            keyword=args.keyword,
            num_points=args.points,
            distance_km=args.distance
        )
        
        # Output shareable URL
        viewer_url = generator.get_viewer_url(analysis_id)
        print(f"\n🔗 Shareable URL:")
        print(f"   {viewer_url}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == '__main__':
    main()