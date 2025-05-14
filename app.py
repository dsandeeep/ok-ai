import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
import threading
import time
import json

# For sentiment analysis and AI conversational responses
from textblob import TextBlob

app = Flask(__name__, static_url_path='', static_folder='.')

CORS(app)  # Enable CORS for all domains on all routes

# Data management - use simple JSON files for persistence
DATA_FILE = 'user_data.json'

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    else:
        return {'tasks': [], 'conversation': []}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

data_lock = threading.Lock()
user_data = load_data()

# Helper functions

def analyze_sentiment(text):
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity  # -1 to 1
    if polarity > 0.2:
        sentiment = 'positive'
    elif polarity < -0.2:
        sentiment = 'negative'
    else:
        sentiment = 'neutral'
    return sentiment, polarity

def generate_response(user_message, sentiment):
    # Basic empathetic response based on sentiment
    if sentiment == 'positive':
        response = "That's wonderful to hear! Keep up the great vibes. 😊"
    elif sentiment == 'negative':
        response = "I'm sorry you're feeling that way. I'm here to listen. Would you like to talk more about it?"
    else:
        response = "Thanks for sharing. I'm here to support you!"
    return response

def check_reminders():
    while True:
        with data_lock:
            now = datetime.now().isoformat()
            for task in user_data['tasks']:
                if task.get('reminder') and not task.get('reminded'):
                    reminder_time = datetime.fromisoformat(task['reminder'])
                    if reminder_time <= datetime.now():
                        print(f"Reminder: Task '{task['title']}' is due now or overdue.")
                        task['reminded'] = True  # to avoid repeated reminders
            save_data(user_data)
        time.sleep(60)  # check reminders every minute

# Start reminder thread
reminder_thread = threading.Thread(target=check_reminders, daemon=True)
reminder_thread.start()

# Routes for frontend file serving
@app.route('/')
def root():
    return send_from_directory('.', 'frontend.html')

# API route for chat conversation
@app.route('/api/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message', '').strip()
    if not user_message:
        return jsonify({'error': 'Empty message'}), 400

    sentiment, polarity = analyze_sentiment(user_message)
    response_text = generate_response(user_message, sentiment)

    with data_lock:
        # Log conversation history
        user_data['conversation'].append({
            'timestamp': datetime.now().isoformat(),
            'user': user_message,
            'bot': response_text,
            'sentiment': sentiment,
            'polarity': polarity
        })
        save_data(user_data)

    return jsonify({
        'response': response_text,
        'sentiment': sentiment,
        'polarity': polarity
    })

# API route for task management
@app.route('/api/tasks', methods=['GET', 'POST', 'PUT', 'DELETE'])
def tasks():
    with data_lock:
        if request.method == 'GET':
            return jsonify(user_data['tasks'])

        elif request.method == 'POST':
            task = request.json
            if not task.get('title'):
                return jsonify({'error': 'Task title is required'}), 400
            task['id'] = max([t.get('id',0) for t in user_data['tasks']] + [0]) + 1
            if 'reminder' in task and task['reminder']:
                # validate reminder datetime format
                try:
                    datetime.fromisoformat(task['reminder'])
                except Exception:
                    task['reminder'] = None
            task['done'] = False
            task['reminded'] = False
            user_data['tasks'].append(task)
            save_data(user_data)
            return jsonify(task)

        elif request.method == 'PUT':
            task_update = request.json
            task_id = task_update.get('id')
            if task_id is None:
                return jsonify({'error': 'Task id is required'}), 400
            for task in user_data['tasks']:
                if task['id'] == task_id:
                    task.update(task_update)
                    save_data(user_data)
                    return jsonify(task)
            return jsonify({'error': 'Task not found'}), 404

        elif request.method == 'DELETE':
            task_id = request.json.get('id')
            if task_id is None:
                return jsonify({'error': 'Task id is required'}), 400
            tasks_filtered = [t for t in user_data['tasks'] if t['id'] != task_id]
            if len(tasks_filtered) == len(user_data['tasks']):
                return jsonify({'error': 'Task not found'}), 404
            user_data['tasks'] = tasks_filtered
            save_data(user_data)
            return jsonify({'success': True})

if __name__ == '__main__':
    # Run the app on port 5000
    app.run(debug=True, host='0.0.0.0', port=5000)

