from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import random
import threading
import time
from datetime import datetime
import json

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "lottery-secret-key")

# Global variables to manage lottery state
lottery_state = {
    "registration_open": False,
    "users": {},  # username -> registration timestamp
    "timer_thread": None,
    "end_time": 0,
    "time_scale": 0.0133,  # Default time scale (1 hour in 48 seconds)
    "extension_used": False,
    "winner": None
}

# Initialize end_time to a default value to avoid errors when checking status before starting the lottery
lottery_state["end_time"] = time.time()

# Log file path
log_file = "lottery_log.txt"

def save_progress():
    """Save current state to log file"""
    with open(log_file, "a") as f:
        f.write(f"\nProgress saved at: {datetime.now()}\n")
        f.write(f"Current participants ({len(lottery_state['users'])}):\n")
        for username, timestamp in lottery_state['users'].items():
            f.write(f"- {username} (registered at {timestamp})\n")

def register_user(username):
    """
    Register a user to the lottery
    :param username: Username to register
    :return: True if registration successful, False otherwise
    """
    # Input validation
    if not username or not username.strip():
        return False, "Username cannot be empty"
    
    # Check for special characters (allow alphanumeric and underscore only)
    if not username.replace("_", "").isalnum():
        return False, "Username can only contain letters, numbers, and underscores"
    
    # Check for duplicate username
    if username in lottery_state["users"]:
        return False, f"Username '{username}' already registered"
    
    # Add user
    timestamp = datetime.now()
    lottery_state["users"][username] = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    
    # Log to file
    with open(log_file, "a") as f:
        f.write(f"{timestamp} - Registered: {username}\n")
    
    return True, f"Successfully registered user: {username}"

def timer_thread(initial_duration):
    """
    Thread function to manage the timer and periodic operations
    :param initial_duration: Initial duration of the registration period in seconds
    """
    start_time = time.time()
    lottery_state["end_time"] = start_time + initial_duration
    last_save_time = start_time
    time_scale = lottery_state["time_scale"]
    
    # Calculate intervals in scaled time
    save_interval = 5 * 60 * time_scale  # 5 minutes in scaled time
    extension_time = 30 * 60 * time_scale  # 30 minutes in scaled time
    
    while time.time() < lottery_state["end_time"] and lottery_state["registration_open"]:
        current_time = time.time()
        
        # Periodic save
        if current_time - last_save_time >= save_interval:
            save_progress()
            last_save_time = current_time
        
        time.sleep(1)  # Sleep for 1 second to reduce CPU usage
    
    # Check if we need to extend the registration period
    if len(lottery_state["users"]) < 5 and not lottery_state["extension_used"] and lottery_state["registration_open"]:
        with open(log_file, "a") as f:
            f.write(f"\n{datetime.now()} - Registration period extended by 30 minutes due to low participation\n")
        
        lottery_state["extension_used"] = True
        lottery_state["end_time"] = time.time() + extension_time
        
        # Continue the timer with the extension
        while time.time() < lottery_state["end_time"] and lottery_state["registration_open"]:
            current_time = time.time()
            
            # Periodic save
            if current_time - last_save_time >= save_interval:
                save_progress()
                last_save_time = current_time
            
            time.sleep(1)
    
    # Final save before closing registration
    save_progress()
    lottery_state["registration_open"] = False
    
    # Select winner
    select_winner()

def select_winner():
    """Select and announce a random winner from registered users"""
    if not lottery_state["users"]:
        with open(log_file, "a") as f:
            f.write(f"\n{datetime.now()} - Lottery cancelled: No participants registered\n")
        lottery_state["winner"] = None
        return
    
    # Select a random username from the registered users
    winner = random.choice(list(lottery_state["users"].keys()))
    winner_timestamp = lottery_state["users"][winner]
    
    # Log the winner
    with open(log_file, "a") as f:
        f.write(f"\n{datetime.now()} - Lottery Results\n")
        f.write(f"Total participants: {len(lottery_state['users'])}\n")
        f.write("List of all participants:\n")
        for username, timestamp in lottery_state["users"].items():
            f.write(f"- {username} (registered at {timestamp})\n")
        f.write(f"\nWINNER: {winner}\n")
        f.write(f"Winner registered at: {winner_timestamp}\n")
    
    lottery_state["winner"] = {
        "username": winner,
        "timestamp": winner_timestamp,
        "total_participants": len(lottery_state["users"])
    }

def start_lottery(time_scale=0.0133):
    """Start a new lottery with the given time scale"""
    # Reset lottery state
    lottery_state["registration_open"] = True
    lottery_state["users"] = {}
    lottery_state["extension_used"] = False
    lottery_state["winner"] = None
    lottery_state["time_scale"] = time_scale
    
    # Initialize log file if it doesn't exist
    if not os.path.exists(log_file):
        with open(log_file, "w") as f:
            f.write(f"Lottery Session Started: {datetime.now()}\n")
            f.write(f"Time Scale: {time_scale} (1 real second = {time_scale} simulation seconds)\n\n")
            f.write("Registration Log:\n")
    else:
        # Append to existing log file
        with open(log_file, "a") as f:
            f.write(f"\n\nNew Lottery Session Started: {datetime.now()}\n")
            f.write(f"Time Scale: {time_scale} (1 real second = {time_scale} simulation seconds)\n\n")
            f.write("Registration Log:\n")
    
    # Calculate registration time in scaled seconds
    registration_time = 60 * 60 * time_scale  # 1 hour in scaled time
    
    # Start the timer in a separate thread
    lottery_state["timer_thread"] = threading.Thread(target=timer_thread, args=(registration_time,))
    lottery_state["timer_thread"].daemon = True
    lottery_state["timer_thread"].start()

@app.route('/')
def index():
    """Main page for the lottery system"""
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start():
    """Start the lottery"""
    time_scale = float(request.form.get('time_scale', 0.0133))
    start_lottery(time_scale)
    return redirect(url_for('index'))

@app.route('/register', methods=['POST'])
def register():
    """Register a user"""
    username = request.form.get('username', '').strip()
    if not lottery_state["registration_open"]:
        return jsonify({
            "success": False,
            "message": "Registration is closed"
        })
    
    success, message = register_user(username)
    return jsonify({
        "success": success,
        "message": message,
        "total_users": len(lottery_state["users"])
    })

@app.route('/status')
def status():
    """Get current lottery status"""
    current_time = time.time()
    remaining = max(0, lottery_state["end_time"] - current_time)
    minutes = int(remaining // 60)
    seconds = int(remaining % 60)
    
    return jsonify({
        "registration_open": lottery_state["registration_open"],
        "extension_used": lottery_state["extension_used"],
        "time_remaining": {
            "minutes": minutes,
            "seconds": seconds,
            "total_seconds": remaining
        },
        "users": {
            "count": len(lottery_state["users"]),
            "list": lottery_state["users"]
        },
        "winner": lottery_state["winner"]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)