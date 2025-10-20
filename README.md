# GBP Ranking Map Analyzer

Interactive web application for visualizing Google Business Profile (GBP) rankings across multiple geographic locations using the DataForSEO API.

## Features

- **Flexible Grid System**: Specify the number of grid points and distance between them (in kilometers)
- **Automatic Grid Calculation**: Generates rectangular grids optimized for your specified number of points
- **Interactive Map**: Visualize rankings with color-coded markers
  - 🟢 Green: Rank 1-3
  - 🟡 Yellow: Rank 4-10
  - 🟠 Orange: Rank 11-20
  - ⚪ Gray: Not ranked
- **Business Selector**: Switch between different businesses to see their ranking distribution
- **URL Sharing**: Generate shareable URLs with your exact configuration
- **Three Configuration Methods**:
  1. Default values in code
  2. URL parameters
  3. UI form inputs

## Quick Start

### Option 1: Use GitHub Pages (Recommended)

1. Enable GitHub Pages for this repository:
   - Go to Settings → Pages
   - Under "Source", select "Deploy from a branch"
   - Select "main" branch and "/ (root)"
   - Click Save

2. Access your app at:
   ```
   https://lvoigt1965.github.io/gbp-ranking-map/
   ```

### Option 2: Run Locally

1. Clone this repository:
   ```bash
   git clone https://github.com/lvoigt1965/gbp-ranking-map.git
   ```

2. Open `index.html` in your web browser

## Configuration

### Default Values

Edit the `DEFAULT_CONFIG` object in `index.html` (around line 126):

```javascript
const DEFAULT_CONFIG = {
    centerLat: 40.7128,        // Center latitude
    centerLon: -74.0060,       // Center longitude
    keyword: 'restaurant',     // Search keyword
    numPoints: 9,              // Number of grid points
    distanceKm: 1,             // Distance between points in km
    apiLogin: '',              // DataForSEO API login
    apiPassword: ''            // DataForSEO API password
};
```

### URL Parameters

Share configurations via URL:

```
https://lvoigt1965.github.io/gbp-ranking-map/?lat=34.0522&lon=-118.2437&keyword=coffee&num_points=16&distance_km=2
```

Supported parameters:
- `lat` - Center latitude
- `lon` - Center longitude
- `keyword` - Search keyword
- `num_points` - Number of grid points
- `distance_km` - Distance between points in km

### UI Form

All values can be modified directly in the web interface before running analysis.

## Usage

1. **Configure Location**: Enter center latitude and longitude
2. **Set Search Parameters**:
   - Enter a keyword (e.g., "restaurant", "dentist", "coffee shop")
   - Specify number of grid points (e.g., 9, 16, 25)
   - Set distance between points in kilometers
3. **Add API Credentials**: Enter your DataForSEO API login and password
4. **Preview Grid**: The map shows blue markers for your grid layout
5. **Run Analysis**: Click "Run Analysis" to fetch data
6. **View Results**: Select different businesses to see their ranking distribution

## Grid Calculation

The app automatically calculates optimal rectangular grids:

- 9 points → 3×3 grid
- 12 points → 3×4 grid
- 16 points → 4×4 grid
- 20 points → 4×5 grid
- 25 points → 5×5 grid

## API Requirements

This application requires a [DataForSEO](https://dataforseo.com/) account with access to the Business Data API.

**Endpoint Used**: `/v3/business_data/google/my_business_info/live`

**Cost**: Check DataForSEO pricing - each grid point = one API call

## Security Notes

⚠️ **Important**: Never commit API credentials to version control

- API credentials are entered via the UI only
- They are not stored in the code or URL
- They are not persisted between sessions

## Browser Compatibility

- Chrome/Edge: ✅ Full support
- Firefox: ✅ Full support
- Safari: ✅ Full support
- Mobile browsers: ✅ Responsive design

## Technologies Used

- **Leaflet.js**: Interactive mapping
- **Tailwind CSS**: Styling (via CDN)
- **DataForSEO API**: GBP ranking data
- **Vanilla JavaScript**: No build process required

## Troubleshooting

### Map not displaying
- Check browser console for errors
- Ensure you have an internet connection (map tiles require online access)

### API calls failing
- Verify your DataForSEO credentials
- Check your API quota/balance
- Ensure the coordinates are valid

### No businesses found
- Try a different keyword
- Adjust the center location
- Increase the distance between points

## License

MIT License - feel free to modify and use as needed.

## Contributing

Contributions welcome! Please open an issue or submit a pull request.

## Author

Created for analyzing Google Business Profile ranking distributions across geographic areas.