from flask import Flask, request, jsonify, send_file, send_from_directory, render_template
from flask_cors import CORS
import pybaseball
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import os
import base64
from pybaseball import statcast_pitcher, statcast_batter, playerid_lookup, pitching_stats, batting_stats
import requests
import json

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

def get_team_roster(team_name):
    # Convert team name to abbreviation if needed
    team_abbrev = {
        'Arizona Diamondbacks': 'ARI',
        'Atlanta Braves': 'ATL',
        'Baltimore Orioles': 'BAL',
        'Boston Red Sox': 'BOS',
        'Chicago Cubs': 'CHC',
        'Chicago White Sox': 'CWS',
        'Cincinnati Reds': 'CIN',
        'Cleveland Guardians': 'CLE',
        'Colorado Rockies': 'COL',
        'Detroit Tigers': 'DET',
        'Houston Astros': 'HOU',
        'Kansas City Royals': 'KC',
        'Los Angeles Angels': 'LAA',
        'Los Angeles Dodgers': 'LAD',
        'Miami Marlins': 'MIA',
        'Milwaukee Brewers': 'MIL',
        'Minnesota Twins': 'MIN',
        'New York Mets': 'NYM',
        'New York Yankees': 'NYY',
        'Oakland Athletics': 'OAK',
        'Philadelphia Phillies': 'PHI',
        'Pittsburgh Pirates': 'PIT',
        'San Diego Padres': 'SD',
        'San Francisco Giants': 'SF',
        'Seattle Mariners': 'SEA',
        'St. Louis Cardinals': 'STL',
        'Tampa Bay Rays': 'TB',
        'Texas Rangers': 'TEX',
        'Toronto Blue Jays': 'TOR',
        'Washington Nationals': 'WSH'
    }.get(team_name)
    
    if not team_abbrev:
        return []
    
    try:
        # Get team roster
        roster = pybaseball.team_roster(team_abbrev)
        return roster.to_dict('records')
    except Exception as e:
        print(f"Error getting roster for {team_name}: {str(e)}")
        return []

def get_player_stats(player_name, days_back=7):
    try:
        # Get Statcast data for the player
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Format dates for pybaseball
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        # Get recent Statcast data
        recent_stats = pybaseball.statcast_batter(start_str, end_str, player_name)
        
        # Get season stats
        season_stats = pybaseball.statcast_batter(str(end_date.year) + '-03-01', end_str, player_name)
        
        if recent_stats.empty or season_stats.empty:
            return None
            
        # Calculate advanced metrics
        recent_metrics = calculate_advanced_metrics(recent_stats)
        season_metrics = calculate_advanced_metrics(season_stats)
        
        return {
            'last7': recent_metrics,
            'season': season_metrics,
            'advanced': {
                'xwoba': float(season_stats['estimated_woba_using_speedangle'].mean()),
                'barrelPct': calculate_barrel_percentage(season_stats),
                'hardHitPct': calculate_hard_hit_percentage(season_stats)
            }
        }
    except Exception as e:
        print(f"Error getting stats for {player_name}: {str(e)}")
        return None

def calculate_advanced_metrics(stats_df):
    if stats_df.empty:
        return {'avg': 0, 'obp': 0, 'slg': 0}
    
    # Calculate basic stats
    hits = len(stats_df[stats_df['events'].isin(['single', 'double', 'triple', 'home_run'])])
    at_bats = len(stats_df[stats_df['events'].notna()])
    bases = (
        len(stats_df[stats_df['events'] == 'single']) * 1 +
        len(stats_df[stats_df['events'] == 'double']) * 2 +
        len(stats_df[stats_df['events'] == 'triple']) * 3 +
        len(stats_df[stats_df['events'] == 'home_run']) * 4
    )
    
    walks = len(stats_df[stats_df['events'] == 'walk'])
    hbp = len(stats_df[stats_df['events'] == 'hit_by_pitch'])
    
    avg = hits / at_bats if at_bats > 0 else 0
    obp = (hits + walks + hbp) / (at_bats + walks + hbp) if (at_bats + walks + hbp) > 0 else 0
    slg = bases / at_bats if at_bats > 0 else 0
    
    return {
        'avg': round(avg, 3),
        'obp': round(obp, 3),
        'slg': round(slg, 3)
    }

def calculate_barrel_percentage(stats_df):
    if stats_df.empty:
        return 0
    
    barrels = len(stats_df[
        (stats_df['launch_angle'].between(8, 50)) &
        (stats_df['launch_speed'] >= 95)
    ])
    
    total_batted_balls = len(stats_df[stats_df['launch_speed'].notna()])
    return round(barrels / total_batted_balls * 100 if total_batted_balls > 0 else 0, 1)

def calculate_hard_hit_percentage(stats_df):
    if stats_df.empty:
        return 0
    
    hard_hits = len(stats_df[stats_df['launch_speed'] >= 95])
    total_batted_balls = len(stats_df[stats_df['launch_speed'].notna()])
    return round(hard_hits / total_batted_balls * 100 if total_batted_balls > 0 else 0, 1)

@app.route('/player_stats', methods=['POST'])
def get_game_stats():
    data = request.json
    away_team = data.get('awayTeam')
    home_team = data.get('homeTeam')
    
    # Get rosters
    away_roster = get_team_roster(away_team)
    home_roster = get_team_roster(home_team)
    
    # Get stats for each player
    away_players = []
    for player in away_roster:
        stats = get_player_stats(player['Name'])
        if stats:
            away_players.append({
                'name': player['Name'],
                'position': player['Position'],
                'stats': stats
            })
    
    home_players = []
    for player in home_roster:
        stats = get_player_stats(player['Name'])
        if stats:
            home_players.append({
                'name': player['Name'],
                'position': player['Position'],
                'stats': stats
            })
    
    return jsonify({
        'awayTeam': away_players,
        'homeTeam': home_players
    })

@app.route('/generate', methods=['POST'])
def generate_preview():
    try:
        data = request.json
        team1 = data.get('team1', [])
        team2 = data.get('team2', [])

        # Create a figure with player stats visualization
        plt.figure(figsize=(12, 8))
        
        # Add your visualization logic here
        # This is a placeholder - you'll want to customize this based on your needs
        plt.title('Game Preview')
        
        # Save the plot to a bytes buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return send_file(buf, mimetype='image/png')
    except Exception as e:
        print(f"Error generating preview: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/game.html')
def serve_game():
    return send_from_directory('.', 'game.html')

@app.route('/get_team_rosters', methods=['GET'])
def get_team_rosters():
    try:
        away_team = request.args.get('away_team')
        home_team = request.args.get('home_team')
        
        # Get current year
        current_year = datetime.now().year
        
        # Get pitching and batting stats for the current year
        pitchers = pitching_stats(current_year)
        batters = batting_stats(current_year)
        
        # Function to get team players
        def get_team_players(team_name, pitchers_df, batters_df):
            # Filter pitchers for the team
            team_pitchers = pitchers_df[pitchers_df['Team'] == team_name][['Name', 'W', 'L', 'ERA', 'SO', 'WHIP']].to_dict('records')
            
            # Filter batters for the team
            team_batters = batters_df[batters_df['Team'] == team_name][['Name', 'AVG', 'HR', 'RBI', 'OPS', 'Position']].to_dict('records')
            
            return {
                'pitchers': team_pitchers,
                'batters': team_batters
            }
        
        # Get rosters for both teams
        away_roster = get_team_players(away_team, pitchers, batters)
        home_roster = get_team_players(home_team, pitchers, batters)
        
        return jsonify({
            'away_team': {
                'name': away_team,
                'roster': away_roster
            },
            'home_team': {
                'name': home_team,
                'roster': home_roster
            }
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 