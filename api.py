from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
from statcast_preview import create_game_preview

app = Flask(__name__)
CORS(app)

@app.route('/generate', methods=['POST'])
def generate_preview():
    try:
        data = request.json
        team1 = data.get('team1', [])
        team2 = data.get('team2', [])
        
        # Generate the preview
        create_game_preview(team1, team2)
        
        # Return the image file
        return send_file('game_preview.png', mimetype='image/png')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000) 