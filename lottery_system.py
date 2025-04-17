#!/usr/bin/env python3
import os
import random
import signal
import sys
import threading
import time
from datetime import datetime

class LotterySystem:
    def __init__(self, time_scale=1.0):
        """
        Initialize the lottery system
        :param time_scale: Scale factor for time (default=1.0)
                          For example: 0.0333 will make 1 hour run in 2 minutes
        """
        self.users = {}  # username -> registration timestamp
        self.registration_open = True
        self.log_file = "lottery_log.txt"
        self.save_interval = 5 * 60 * time_scale  # 5 minutes in scaled time
        self.display_interval = 10 * 60 * time_scale  # 10 minutes in scaled time
        self.registration_time = 60 * 60 * time_scale  # 1 hour in scaled time
        self.extension_time = 30 * 60 * time_scale  # 30 minutes in scaled time
        self.extension_used = False
        self.time_scale = time_scale
        
        # Initialize log file
        if not os.path.exists(self.log_file):
            with open(self.log_file, "w") as f:
                f.write(f"Lottery Session Started: {datetime.now()}\n")
                f.write(f"Time Scale: {time_scale} (1 real second = {time_scale} simulation seconds)\n\n")
                f.write("Registration Log:\n")
        
        # Set up signal handler for clean shutdown
        signal.signal(signal.SIGINT, self.handle_interrupt)
    
    def handle_interrupt(self, sig, frame):
        """Handle keyboard interrupts (Ctrl+C)"""
        print("\nProgram interrupted. Saving progress...")
        self.save_progress()
        print("Progress saved. Exiting.")
        sys.exit(0)
    
    def save_progress(self):
        """Save current state to log file"""
        with open(self.log_file, "a") as f:
            f.write(f"\nProgress saved at: {datetime.now()}\n")
            f.write(f"Current participants ({len(self.users)}):\n")
            for username, timestamp in self.users.items():
                f.write(f"- {username} (registered at {timestamp})\n")
    
    def register_user(self, username):
        """
        Register a user to the lottery
        :param username: Username to register
        :return: True if registration successful, False otherwise
        """
        # Input validation
        if not username or not username.strip():
            print("Error: Username cannot be empty")
            return False
        
        # Check for special characters (allow alphanumeric and underscore only)
        if not username.replace("_", "").isalnum():
            print("Error: Username can only contain letters, numbers, and underscores")
            return False
        
        # Check for duplicate username
        if username in self.users:
            print(f"Error: Username '{username}' already registered")
            return False
        
        # Add user
        timestamp = datetime.now()
        self.users[username] = timestamp
        
        # Log to file
        with open(self.log_file, "a") as f:
            f.write(f"{timestamp} - Registered: {username}\n")
        
        print(f"Successfully registered user: {username}")
        print(f"Total registered users: {len(self.users)}")
        return True
    
    def display_time_remaining(self, end_time):
        """Display the time remaining for registration"""
        remaining = max(0, end_time - time.time())
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        
        # Show extension status if applicable
        extension_text = " (extended)" if self.extension_used else ""
        
        print(f"\nRegistration period{extension_text}:")
        print(f"Time remaining: {minutes} minutes, {seconds} seconds")
        print(f"Users registered so far: {len(self.users)}")
        print("Enter a username to register, or just press Enter to refresh the timer")
    
    def timer_thread(self, initial_duration):
        """
        Thread function to manage the timer and periodic operations
        :param initial_duration: Initial duration of the registration period in seconds
        """
        start_time = time.time()
        end_time = start_time + initial_duration
        last_save_time = start_time
        last_display_time = start_time - self.display_interval  # Display immediately at start
        
        while time.time() < end_time and self.registration_open:
            current_time = time.time()
            
            # Periodic save
            if current_time - last_save_time >= self.save_interval:
                self.save_progress()
                last_save_time = current_time
            
            # Periodic time display
            if current_time - last_display_time >= self.display_interval:
                self.display_time_remaining(end_time)
                last_display_time = current_time
            
            time.sleep(1)  # Sleep for 1 second to reduce CPU usage
        
        # Check if we need to extend the registration period
        if len(self.users) < 5 and not self.extension_used and self.registration_open:
            print("\n" + "="*60)
            print(f"Less than 5 users registered ({len(self.users)}). Extending registration by 30 minutes.")
            print("="*60 + "\n")
            
            with open(self.log_file, "a") as f:
                f.write(f"\n{datetime.now()} - Registration period extended by 30 minutes due to low participation\n")
            
            self.extension_used = True
            new_end_time = time.time() + self.extension_time
            
            # Continue the timer with the extension
            while time.time() < new_end_time and self.registration_open:
                current_time = time.time()
                
                # Periodic save
                if current_time - last_save_time >= self.save_interval:
                    self.save_progress()
                    last_save_time = current_time
                
                # Periodic time display
                if current_time - last_display_time >= self.display_interval:
                    self.display_time_remaining(new_end_time)
                    last_display_time = current_time
                
                time.sleep(1)
        
        # Final save before closing registration
        self.save_progress()
        self.registration_open = False
    
    def select_winner(self):
        """Select and announce a random winner from registered users"""
        if not self.users:
            print("\n" + "="*60)
            print("No users registered for the lottery. No winner to select.")
            print("="*60)
            
            with open(self.log_file, "a") as f:
                f.write(f"\n{datetime.now()} - Lottery cancelled: No participants registered\n")
            return None
        
        # Select a random username from the registered users
        winner = random.choice(list(self.users.keys()))
        winner_timestamp = self.users[winner]
        
        # Announce the winner
        print("\n" + "="*60)
        print(f"LOTTERY RESULTS")
        print("="*60)
        print(f"Total participants: {len(self.users)}")
        print(f"THE WINNER IS: {winner}")
        print(f"Registered at: {winner_timestamp}")
        print("="*60)
        
        # Log the winner
        with open(self.log_file, "a") as f:
            f.write(f"\n{datetime.now()} - Lottery Results\n")
            f.write(f"Total participants: {len(self.users)}\n")
            f.write("List of all participants:\n")
            for username, timestamp in self.users.items():
                f.write(f"- {username} (registered at {timestamp})\n")
            f.write(f"\nWINNER: {winner}\n")
            f.write(f"Winner registered at: {winner_timestamp}\n")
        
        return winner
    
    def run(self):
        """Run the lottery system"""
        print("="*60)
        print("WELCOME TO THE LOTTERY SYSTEM")
        print("="*60)
        print(f"Registration is open for 1 hour (scaled: {self.registration_time:.0f} seconds)")
        print("Enter your username to register for the lottery")
        print("Press Ctrl+C to exit at any time")
        print("="*60)
        
        # Start the timer in a separate thread
        timer_thread = threading.Thread(target=self.timer_thread, args=(self.registration_time,))
        timer_thread.daemon = True
        timer_thread.start()
        
        # Main input loop for registration
        try:
            while self.registration_open:
                try:
                    username = input("\nEnter username to register (or press Enter to refresh): ").strip()
                    
                    if not username:
                        # Just refresh the display
                        continue
                    
                    self.register_user(username)
                    
                except Exception as e:
                    print(f"Error processing input: {e}")
            
            print("\n" + "="*60)
            print("Registration period has ended!")
            print("="*60)
            
            # Wait a moment for dramatic effect
            time.sleep(1)
            
            # Select and announce the winner
            self.select_winner()
            
        except KeyboardInterrupt:
            print("\nProgram interrupted by user.")
            self.save_progress()
            return

if __name__ == "__main__":
    # For testing purposes, you can adjust the time_scale
    # Default (1.0) = Real time (1 hour registration period)
    # 0.0333 = Makes 1 hour run in 2 minutes
    
    # Parse command line arguments for time scale
    if len(sys.argv) > 1:
        try:
            time_scale = float(sys.argv[1])
            print(f"Running with time scale: {time_scale}")
            lottery = LotterySystem(time_scale=time_scale)
        except ValueError:
            print("Invalid time scale. Using default (real time).")
            lottery = LotterySystem()
    else:
        # For testing, set default to 0.0333 (1 hour in 2 minutes)
        # For real use, change this to 1.0
        lottery = LotterySystem(time_scale=0.0333)
        print(f"Running with time scale: 0.0333 (1 hour in 2 minutes)")
    
    lottery.run()
