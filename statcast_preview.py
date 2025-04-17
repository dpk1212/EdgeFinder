import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pybaseball import statcast_batter, playerid_lookup
from datetime import datetime, timedelta
import numpy as np

def get_color_for_percentile(value, metric):
    """Return color based on metric value and type"""
    # Define color ranges (red is good for most stats, blue is good for K%)
    if metric == 'K%':
        if value <= 20: return '#E6F3FF'  # light blue (good)
        elif value <= 25: return 'white'   # neutral
        else: return '#FFE6E6'            # light red (bad)
    else:
        if metric in ['xwOBA', 'xBA', 'xSLG']:
            if value >= 0.350: return '#FFE6E6'     # light red (good)
            elif value >= 0.300: return 'white'     # neutral
            else: return '#E6F3FF'                  # light blue (bad)
        elif metric in ['EV', 'Hard Hit%']:
            if value >= 90: return '#FFE6E6'        # light red (good)
            elif value >= 85: return 'white'        # neutral
            else: return '#E6F3FF'                  # light blue (bad)
    return 'white'  # default

def get_player_stats(first_name, last_name, days_back=30):
    try:
        # Get player ID
        player = playerid_lookup(last_name, first_name)
        if player.empty:
            return None
        
        # Get Statcast data for last 30 days
        end_date = datetime.today()
        start_date = end_date - timedelta(days=days_back)
        
        stats = statcast_batter(start_date.strftime('%Y-%m-%d'), 
                               end_date.strftime('%Y-%m-%d'), 
                               player.iloc[0].key_mlbam)
        
        if stats is None or stats.empty:
            return None

        # Calculate metrics
        metrics = {
            'BBE': len(stats[stats['launch_speed'].notna()]),
            'LA°': round(stats['launch_angle'].mean(), 1),
            'EV': round(stats['launch_speed'].mean(), 1),
            'Hard_Hit%': round((stats['launch_speed'] >= 95).mean() * 100, 1),
            'xwOBA': round(stats['estimated_woba_using_speedangle'].mean(), 3),
            'xBA': round(stats['estimated_ba_using_speedangle'].mean(), 3),
            'xSLG': round(stats['estimated_slg_using_speedangle'].mean(), 3),
            'K%': round((stats['events'] == 'strikeout').mean() * 100, 1)
        }
        
        return metrics
    except Exception as e:
        print(f"Error getting stats for {first_name} {last_name}: {str(e)}")
        return None

def create_stat_table(ax, team_data, is_home_team=False):
    columns = ['Pos.', 'BBE', 'LA°', 'EV', 'Hard Hit%', 'xwOBA', 'xBA', 'xSLG', 'K%']
    
    # Create table
    cell_text = []
    cell_colors = []
    
    for _, row in team_data.iterrows():
        stats = row.get('stats', {})
        if stats is None:
            stats = {}
        
        row_data = [
            row['Pos'],
            str(stats.get('BBE', 0)),
            f"{stats.get('LA°', 0):.1f}",
            f"{stats.get('EV', 0):.1f}",
            f"{stats.get('Hard_Hit%', 0):.1f}",
            f"{stats.get('xwOBA', 0):.3f}",
            f"{stats.get('xBA', 0):.3f}",
            f"{stats.get('xSLG', 0):.3f}",
            f"{stats.get('K%', 0):.1f}"
        ]
        cell_text.append(row_data)
        
        # Color coding
        colors = ['white']  # Position is always white
        for col, val in zip(columns[1:], row_data[1:]):
            try:
                val_float = float(val)
                colors.append(get_color_for_percentile(val_float, col))
            except ValueError:
                colors.append('white')
        
        cell_colors.append(colors)
    
    # Create and style table
    table = ax.table(cellText=cell_text,
                    colLabels=columns,
                    cellColours=cell_colors,
                    cellLoc='center',
                    loc='center')
    
    # Style the table
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.2, 1.5)
    
    # Style header
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_text_props(weight='bold')
            cell.set_facecolor('#f0f0f0')
    
    # Remove axis
    ax.axis('off')

def create_game_preview(team1_lineup, team2_lineup):
    """
    Create a game preview visualization for two teams
    
    Parameters:
    team1_lineup, team2_lineup: List of dictionaries with keys:
        - 'name': Player full name (First Last)
        - 'position': Position abbreviation
    """
    fig = plt.figure(figsize=(15, 10))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 4])
    
    # Team logos and names
    ax_logo1 = fig.add_subplot(gs[0, 0])
    ax_logo2 = fig.add_subplot(gs[0, 1])
    ax_stats1 = fig.add_subplot(gs[1, 0])
    ax_stats2 = fig.add_subplot(gs[1, 1])
    
    # Set title
    fig.suptitle('Statcast Game Preview', fontsize=16, y=0.95)
    
    # Add team names
    ax_logo1.text(0.5, 0.5, "Arizona Diamondbacks", ha='center', va='center', fontsize=14)
    ax_logo2.text(0.5, 0.5, "Miami Marlins", ha='center', va='center', fontsize=14)
    ax_logo1.axis('off')
    ax_logo2.axis('off')
    
    # Process lineups
    def process_lineup(lineup):
        processed = []
        for player in lineup:
            name_parts = player['name'].split()
            first_name = name_parts[0]
            last_name = name_parts[-1]
            stats = get_player_stats(first_name, last_name)
            
            processed.append({
                'Pos': player['position'],
                'Name': player['name'],
                'stats': stats if stats is not None else {}
            })
        return pd.DataFrame(processed)
    
    team1_data = process_lineup(team1_lineup)
    team2_data = process_lineup(team2_lineup)
    
    # Create stat tables
    create_stat_table(ax_stats1, team1_data, False)
    create_stat_table(ax_stats2, team2_data, True)
    
    plt.tight_layout()
    plt.savefig('game_preview.png', dpi=300, bbox_inches='tight')

if __name__ == "__main__":
    # Example lineups for Diamondbacks vs Marlins
    diamondbacks = [
        {'name': 'Corbin Carroll', 'position': 'RF'},
        {'name': 'Ketel Marte', 'position': 'SS'},
        {'name': 'Christian Walker', 'position': '1B'},
        {'name': 'Tommy Pham', 'position': 'DH'},
        {'name': 'Lourdes Gurriel', 'position': 'LF'},
        {'name': 'Evan Longoria', 'position': '3B'},
        {'name': 'Alek Thomas', 'position': 'CF'},
        {'name': 'Gabriel Moreno', 'position': 'C'},
        {'name': 'Geraldo Perdomo', 'position': '2B'},
    ]
    
    marlins = [
        {'name': 'Luis Arraez', 'position': '2B'},
        {'name': 'Josh Bell', 'position': '1B'},
        {'name': 'Jorge Soler', 'position': 'DH'},
        {'name': 'Bryan De La Cruz', 'position': 'LF'},
        {'name': 'Jazz Chisholm', 'position': 'CF'},
        {'name': 'Jesus Sanchez', 'position': 'RF'},
        {'name': 'Jean Segura', 'position': '3B'},
        {'name': 'Joey Wendle', 'position': 'SS'},
        {'name': 'Jacob Stallings', 'position': 'C'},
    ]
    
    create_game_preview(diamondbacks, marlins) 