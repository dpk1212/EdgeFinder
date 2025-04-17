from flask import Flask, render_template, request, jsonify
import pybaseball
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
from datetime import datetime, date
import traceback  # For detailed error logging
import math # For checking NaN

# Enable pybaseball caching (store data locally to speed up repeated requests)
# Consider configuring cache location/strategy later if needed
pybaseball.cache.enable()

app = Flask(__name__)

# Configure Matplotlib for non-interactive backend
plt.switch_backend('Agg')

# --- Helper Functions ---
def get_current_season():
    return datetime.now().year

def create_plot_base64(fig):
    """Converts a Matplotlib figure to a base64 encoded PNG image."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    buf.close()
    plt.close(fig) # Close the figure to free memory
    return f"data:image/png;base64,{img_base64}"

# Function to safely convert numpy types to standard Python types for JSON
def safe_jsonify(data):
    if isinstance(data, dict):
        return {k: safe_jsonify(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [safe_jsonify(i) for i in data]
    elif isinstance(data, (pd.Timestamp, pd.Timedelta)):
        return str(data)
    # Check for float NaN specifically before general pd.isna
    elif isinstance(data, float) and math.isnan(data):
        return None
    elif pd.isna(data):
        return None
    elif hasattr(data, 'item'): # Handle numpy types
        # Convert numpy types to standard Python types
        # Check for numpy bool_ explicitly
        if isinstance(data, (pd.BooleanDtype.type, bool)):
            return bool(data) 
        try:
            item = data.item()
            # Check for float NaN again after item() call
            if isinstance(item, float) and math.isnan(item):
                return None
            return item
        except: # Fallback if item() fails or type is complex
             return str(data)
    # Fallback for other types
    try:
        jsonify({ 'data': data }) # Test serialization
        return data
    except TypeError:
        return str(data)

# --- Routes ---
@app.route('/')
def today_page():
    # Serve the main page displaying today's games
    return render_template('today.html')

@app.route('/api/today_schedule')
def get_today_schedule():
    """Fetches today's MLB schedule using MLB Stats API."""
    try:
        today_str = date.today().strftime("%Y-%m-%d")
        import requests
        # Using the official MLB Stats API endpoint
        schedule_url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today_str}&hydrate=probablePitcher,team"
        print(f"Fetching schedule from: {schedule_url}") # Log URL
        response = requests.get(schedule_url, timeout=10) # Add timeout
        response.raise_for_status()
        schedule_data = response.json()
        games = []
        if schedule_data.get('totalGames', 0) > 0:
            for day_schedule in schedule_data.get('dates', []):
                 for game_info in day_schedule.get('games', []):
                    # Extract detailed probable starter info if available
                    home_starter_id = game_info.get('teams', {}).get('home', {}).get('probablePitcher', {}).get('id')
                    away_starter_id = game_info.get('teams', {}).get('away', {}).get('probablePitcher', {}).get('id')
                    home_starter_name = game_info.get('teams', {}).get('home', {}).get('probablePitcher', {}).get('fullName')
                    away_starter_name = game_info.get('teams', {}).get('away', {}).get('probablePitcher', {}).get('fullName')

                    games.append({
                        "game_pk": game_info.get('gamePk'),
                        "away_team": game_info.get('teams', {}).get('away', {}).get('team', {}).get('name'),
                        "home_team": game_info.get('teams', {}).get('home', {}).get('team', {}).get('name'),
                        "away_score": game_info.get('teams', {}).get('away', {}).get('score'),
                        "home_score": game_info.get('teams', {}).get('home', {}).get('score'),
                        "status": game_info.get('status', {}).get('detailedState'),
                        "time": game_info.get('gameDate'),
                        "venue": game_info.get('venue', {}).get('name'),
                        "away_probable_pitcher": away_starter_name,
                        "home_probable_pitcher": home_starter_name,
                        "away_probable_pitcher_id": away_starter_id,
                        "home_probable_pitcher_id": home_starter_id, # Corrected: Home ID for home pitcher
                    })
        return jsonify(safe_jsonify({"games": games}))
    except requests.exceptions.RequestException as req_e:
         print(f"HTTP Error fetching schedule: {req_e}")
         traceback.print_exc()
         return jsonify({"error": f"Failed to fetch schedule from MLB API: {req_e}"}), 503 # Service Unavailable
    except Exception as e:
        print(f"Error processing schedule data: {e}")
        traceback.print_exc()
        return jsonify({"error": "Failed to process schedule data."}), 500

@app.route('/api/search_player', methods=['GET'])
def search_player():
    player_name = request.args.get('name', '')
    if not player_name:
        return jsonify({"error": "Player name is required"}), 400

    try:
        lookup = pybaseball.playerid_lookup(last=player_name.split(' ')[-1] if ' ' in player_name else player_name,
                                            first=player_name.split(' ')[0] if ' ' in player_name else None,
                                            fuzzy=True)

        if lookup.empty:
            return jsonify({"error": f"Player '{player_name}' not found"}), 404

        # Handle multiple results - return a list for user to choose? For now, just first.
        player_data = lookup.iloc[0]
        result = {
            "name_first": player_data['name_first'],
            "name_last": player_data['name_last'],
            "mlbam_id": int(player_data['key_mlbam']) # Ensure standard int
        }
        # If multiple matches, maybe return top 3?
        # results = []
        # for _, row in lookup.head(5).iterrows():
        #     results.append({
        #         "name_first": row['name_first'],
        #         "name_last": row['name_last'],
        #         "mlbam_id": int(row['key_mlbam'])
        #     })

        return jsonify(safe_jsonify(result)) # Use safe_jsonify

    except Exception as e:
        print(f"Error during player lookup for '{player_name}': {e}")
        traceback.print_exc()
        return jsonify({"error": "Failed to lookup player."}), 500

@app.route('/api/player_stats', methods=['GET'])
def get_player_stats():
    """Fetches curated summary stats (trad & percentile) and optionally detailed Statcast data."""
    mlbam_id = request.args.get('mlbam_id')
    full_stats_requested = request.args.get('full_stats', 'false').lower() == 'true'
    try:
        season = int(request.args.get('season', get_current_season()))
    except ValueError:
        return jsonify({"error": "Invalid season format"}), 400

    if not mlbam_id:
        return jsonify({"error": "MLBAM ID is required"}), 400

    try:
        mlbam_id = int(mlbam_id)
    except ValueError:
        return jsonify({"error": "Invalid MLBAM ID format"}), 400

    try:
        print(f"Fetching stats for ID: {mlbam_id}, Season: {season}, Full: {full_stats_requested}")

        # --- Get Player Name --- (Same as before)
        player_name = "Player"
        try:
            player_lookup = pybaseball.playerid_lookup(mlbam_id=mlbam_id)
            if not player_lookup.empty:
                player_name = f"{player_lookup.iloc[0]['name_first']} {player_lookup.iloc[0]['name_last']}"
        except Exception as name_e:
            print(f"Could not lookup player name for {mlbam_id}: {name_e}")

        player_info = {"name": player_name, "id": mlbam_id, "season": season}
        summary_stats = {} # Curated stats for comparison view
        detailed_statcast = {} # Raw data for full charts view
        position_type = "Unknown"
        min_ip_leaderboard = 10 # Minimum IP for leaderboard inclusion (adjust as needed)
        min_pa_leaderboard = 20 # Minimum PA for leaderboard inclusion

        # --- Fetch Traditional Pitching Stats & Leaderboard Percentiles ---
        try:
            pitching_trad = pybaseball.pitching_stats(season, season, playerid=mlbam_id, qual=1)
            if not pitching_trad.empty:
                position_type = "Pitcher"
                p_data = pitching_trad.iloc[0]
                summary_stats['pitching'] = {
                    'IP': p_data.get('IP'), 'ERA': p_data.get('ERA'), 'FIP': p_data.get('FIP'),
                    'WHIP': p_data.get('WHIP'), 'K/9': p_data.get('SO9'), 'BB/9': p_data.get('BB9'),
                    'HR/9': p_data.get('HR9'), 'ERA+': p_data.get('ERA+')
                }
                # Fetch Leaderboard Percentiles (only if enough IP)
                if p_data.get('IP', 0) >= min_ip_leaderboard:
                    try:
                        lb = pybaseball.statcast_leaderboards.pitcher_leaderboard(start_season=season, end_season=season, player_id=mlbam_id, min_ip=min_ip_leaderboard)
                        if not lb.empty:
                            lb_data = lb.iloc[0]
                            summary_stats['pitching_percentiles'] = {
                                'xERA': lb_data.get('xera'), # Value, not percentile directly from this board?
                                'K%': lb_data.get('k_percent_percentile'),
                                'BB%': lb_data.get('bb_percent_percentile'),
                                'Whiff%': lb_data.get('whiff_percent_percentile'),
                                'Barrel%': lb_data.get('barrel_percent_percentile'),
                                'HardHit%': lb_data.get('hard_hit_percent_percentile'),
                                'Avg EV': lb_data.get('avg_exit_velocity_percentile'),
                                'Fastball Velo': lb_data.get('fastball_velocity_percentile')
                            }
                            # Add actual xERA value if available
                            if 'xera' in lb_data:
                                summary_stats['pitching']['xERA'] = lb_data['xera']
                        else:
                             print(f"Player {mlbam_id} not found on {season} pitcher leaderboard (min IP: {min_ip_leaderboard})")
                    except Exception as lb_e:
                         print(f"Failed to fetch pitcher leaderboard data for {mlbam_id}: {lb_e}")

        except Exception as e:
            print(f"Could not fetch traditional pitching stats for {mlbam_id}, season {season}: {e}")
            if "IndexError" not in str(e):
                 traceback.print_exc()

        # --- Fetch Traditional Batting Stats & Leaderboard Percentiles ---
        # (Keep basic fetch, can add batter leaderboards later if needed)
        try:
            batting_trad = pybaseball.batting_stats(season, season, playerid=mlbam_id, qual=1)
            if not batting_trad.empty:
                b_data = batting_trad.iloc[0]
                summary_stats['batting'] = {
                     'PA': b_data.get('PA'), 'AVG': b_data.get('BA'), 'OBP': b_data.get('OBP'),
                     'SLG': b_data.get('SLG'), 'OPS': b_data.get('OPS'), 'HR': b_data.get('HR'),
                     'RBI': b_data.get('RBI'), 'wRC+': b_data.get('wRC+') # Use OPS+ if wRC+ not present?
                 }
                 if position_type == "Pitcher":
                     position_type = "Two-Way"
                 else:
                     position_type = "Hitter"
                 # Placeholder: Add batter leaderboard fetch here if needed later

        except Exception as e:
            print(f"Could not fetch traditional batting stats for {mlbam_id}, season {season}: {e}")
            if "IndexError" not in str(e):
                 traceback.print_exc()

        player_info["position_type"] = position_type

        # --- Fetch DETAILED Statcast Data (Only if Requested) ---
        if full_stats_requested:
            print(f"Fetching FULL Statcast data for {mlbam_id}")
            start_date = f"{season}-03-01"
            end_date = f"{season}-11-01"

            # Fetch Detailed Statcast Pitching
            if position_type in ["Pitcher", "Two-Way"]:
                try:
                    sc_pitching = pybaseball.statcast_pitcher(start_dt=start_date, end_dt=end_date, player_id=mlbam_id)
                    if not sc_pitching.empty:
                        sc_cols = ['pitch_type', 'release_speed', 'release_spin_rate', 'pfx_x', 'pfx_z', 'plate_x', 'plate_z', 'description', 'events']
                        # Filter necessary columns and drop rows where essential info is missing
                        sc_pitching_filtered = sc_pitching[sc_cols].dropna(subset=['pitch_type', 'release_speed', 'plate_x', 'plate_z'])
                        if not sc_pitching_filtered.empty:
                            detailed_statcast['pitching_raw'] = sc_pitching_filtered.to_dict(orient='list')
                        else: 
                            print("No usable detailed pitching Statcast rows after filtering NA.") 
                    else:
                        print(f"No detailed Statcast pitching data found for {mlbam_id} in {season}")
                except Exception as e:
                    print(f"Error fetching detailed Statcast pitching data: {e}")
                    traceback.print_exc()

            # Fetch Detailed Statcast Batting
            if position_type in ["Hitter", "Two-Way"]:
                try:
                    sc_batting = pybaseball.statcast_batter(start_dt=start_date, end_dt=end_date, player_id=mlbam_id)
                    # Check essential columns exist and have data
                    if not sc_batting.empty and 'launch_speed' in sc_batting.columns and 'launch_angle' in sc_batting.columns and sc_batting['launch_speed'].notna().any():
                        sc_cols = ['launch_speed', 'launch_angle', 'estimated_woba_using_speedangle', 'bb_type', 'events', 'hc_x', 'hc_y']
                        valid_cols = [col for col in sc_cols if col in sc_batting.columns]
                        # Filter necessary columns and drop rows where essential info is missing
                        sc_batting_filtered = sc_batting[valid_cols].dropna(subset=['launch_speed', 'launch_angle', 'hc_x', 'hc_y'])
                        if not sc_batting_filtered.empty:
                            detailed_statcast['batting_raw'] = sc_batting_filtered.to_dict(orient='list')
                        else:
                             print("No usable detailed batting Statcast rows after filtering NA.") 
                    else:
                        print(f"No detailed Statcast hitting data (or launch speed/angle) found for {mlbam_id} in {season}")
                except Exception as e:
                    print(f"Error fetching detailed Statcast hitting data: {e}")
                    traceback.print_exc()

        # --- Combine and Return --- #
        result_data = {
            "player_info": player_info,
            "summary_stats": summary_stats
        }
        # Only include detailed stats if requested and available
        if full_stats_requested and detailed_statcast:
            result_data["detailed_statcast"] = detailed_statcast
        elif full_stats_requested:
             print(f"Full stats requested but no detailed data found/fetched for {mlbam_id}")

        return jsonify(safe_jsonify(result_data))

    except Exception as e:
        print(f"Generic error during player stats fetch for {mlbam_id}, season {season}: {e}")
        traceback.print_exc()
        return jsonify({"error": "An unexpected error occurred while fetching player stats."}), 500

if __name__ == '__main__':
    # Ensure host='0.0.0.0' if running in a container or VM and need external access
    # Port 5001 used previously, keeping it consistent
    app.run(debug=True, port=5001) # Keep debug=True for development 