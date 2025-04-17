# MLB Statcast Game Preview Generator

A web application that generates detailed game previews using MLB Statcast data. This tool creates side-by-side comparisons of two teams' lineups with advanced metrics and visual indicators of player performance.

## Features

- Real-time Statcast data for the last 30 days
- Advanced metrics including:
  - BBE (Batted Ball Events)
  - LA° (Launch Angle)
  - EV (Exit Velocity)
  - Hard Hit%
  - xwOBA
  - xBA
  - xSLG
  - K%
- Visual performance indicators with color coding
- Clean, professional table layout
- High-resolution output
- Web interface for easy lineup input
- API endpoint for programmatic access

## Local Development

1. Clone the repository:
```bash
git clone https://github.com/dpk1212/EdgeFinder.git
cd EdgeFinder
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Start the Flask API:
```bash
python api.py
```

5. Open index.html in your browser to use the web interface.

## Deployment

### Deploy to GitHub Pages

1. Go to your repository's Settings
2. Navigate to Pages
3. Select your main branch as the source
4. Save the changes

The static frontend will be available at `https://dpk1212.github.io/EdgeFinder`

### Deploy the API to Heroku

1. Create a new Heroku app:
```bash
heroku create your-app-name
```

2. Push to Heroku:
```bash
git push heroku main
```

3. Update the API URL in index.html to point to your Heroku app.

## API Usage

Generate a preview using the API:

```bash
curl -X POST https://your-app.herokuapp.com/generate \
  -H "Content-Type: application/json" \
  -d '{
    "team1": [
      {"name": "Player Name", "position": "POS"},
      ...
    ],
    "team2": [
      {"name": "Player Name", "position": "POS"},
      ...
    ]
  }'
```

## Data Sources

This tool uses the `pybaseball` package to access MLB Statcast data. All statistics are calculated from the last 30 days of available data.

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 