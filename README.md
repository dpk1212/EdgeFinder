# MLB Statcast Game Preview Generator

A Python tool that generates detailed game previews using MLB Statcast data. This tool creates side-by-side comparisons of two teams' lineups with advanced metrics and visual indicators of player performance.

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

## Installation

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

## Usage

1. Edit the lineups in `statcast_preview.py`:
```python
team1 = [
    {'name': 'Player Name', 'position': 'POS'},
    # Add more players...
]

team2 = [
    {'name': 'Player Name', 'position': 'POS'},
    # Add more players...
]
```

2. Run the script:
```bash
python statcast_preview.py
```

3. The script will generate a `game_preview.png` file with the visualization.

## Example Output

The generated preview includes:
- Team names and lineups
- Advanced Statcast metrics for each player
- Color-coded performance indicators:
  - Red: Above average performance
  - White: Average performance
  - Blue: Below average performance

## Data Sources

This tool uses the `pybaseball` package to access MLB Statcast data. All statistics are calculated from the last 30 days of available data.

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 