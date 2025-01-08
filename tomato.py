import tkinter as tk
from tkinter import messagebox, filedialog
import csv
import time
import threading
import os
import datetime
from pydub import AudioSegment
from pydub.playback import play

CSV_FILE = 'targets.csv'
DEFAULT_FOCUS_MINUTES = 25
DEFAULT_REST_MINUTES = 10
SOUND_FILE_PATH = "alert.mp3"  # Change this to your desired file path

class TomatoFocusApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Tomato Focus")

        # Optional: Load an icon for the main window
        # Make sure the path is correct if you have an icon file
        try:
            self.icon_image = tk.PhotoImage(file="tomato.png")
            self.master.iconphoto(False, self.icon_image)
        except Exception as e:
            print("Could not load icon:", e)

        # Configuration variables
        self.focus_minutes = DEFAULT_FOCUS_MINUTES
        self.rest_minutes = DEFAULT_REST_MINUTES
        self.mute_sound = tk.BooleanVar(value=False)

        # Main frame
        self.main_frame = tk.Frame(self.master, padx=10, pady=10)
        self.main_frame.pack()

        # Target entry
        self.target_label = tk.Label(self.main_frame, text="Next Focus Target:")
        self.target_label.pack()
        self.target_entry = tk.Entry(self.main_frame, width=50)
        self.target_entry.pack(pady=5)

        # Add target button
        self.add_button = tk.Button(self.main_frame, text="Add Target", command=self.add_target)
        self.add_button.pack()

        # Start focus section
        self.timer_label = tk.Label(self.main_frame, text="")
        self.timer_label.pack(pady=10)

        self.start_button = tk.Button(self.main_frame, text="Start Focus", command=self.start_focus)
        self.start_button.pack()

        # Mute checkbox
        self.mute_check = tk.Checkbutton(self.main_frame, text="Mute Sound", variable=self.mute_sound)
        self.mute_check.pack(pady=5)

        # Buttons to open other windows
        button_frame = tk.Frame(self.main_frame)
        button_frame.pack(pady=5)

        self.config_button = tk.Button(button_frame, text="Setting", command=self.open_config_window)
        self.config_button.pack(side=tk.LEFT, padx=5)

        self.history_button = tk.Button(button_frame, text="History", command=self.open_history_window)
        self.history_button.pack(side=tk.LEFT, padx=5)

        # Label for current focus target
        self.current_focus_label = tk.Label(self.main_frame, text=f"Current Focus: {self._get_last_target()}")
        self.current_focus_label.pack(pady=5)

        # Timer thread variables
        self.focus_thread = None
        self.stop_event = threading.Event()

        # Make sure CSV file exists
        self._ensure_csv_exists()

    def _ensure_csv_exists(self):
        """Ensure the CSV file exists with the proper header."""
        if not os.path.exists(CSV_FILE):
            with open(CSV_FILE, "w", newline="", encoding='utf-8') as f:
                writer = csv.writer(f)
                # The columns: Date, Time, Target
                writer.writerow(["Date", "Time", "Target"])

    def add_target(self):
        target_text = self.target_entry.get().strip()
        if target_text:
            # Write to CSV
            date_str = datetime.date.today().isoformat()
            time_str = datetime.datetime.now().strftime("%H:%M:%S")
            with open(CSV_FILE, "a", newline="", encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([date_str, time_str, target_text])
            
            self.target_entry.delete(0, tk.END)

            # Load the newest target from the CSV history
            last_target = self._get_last_target()
            if last_target:
                self.current_focus_label.config(text=f"Current Focus: {last_target}")
            else:
                self.current_focus_label.config(text="Current Focus: None")

        else:
            messagebox.showwarning("Warning", "Please enter a target.")

    def start_focus(self):
        """Starts the focus period in a separate thread, automatically loading
           the newest (last) target from the CSV as the current focus.
        """
        # Stop any existing timer thread
        self.stop_event.set()

        # Reset the event
        self.stop_event.clear()
        self.timer_label.config(text="")

        # Load the newest target from the CSV history
        last_target = self._get_last_target()
        if last_target:
            self.current_focus_label.config(text=f"Current Focus: {last_target}")
        else:
            self.current_focus_label.config(text="Current Focus: None")

        # Create a new thread
        self.focus_thread = threading.Thread(target=self._run_focus_timer, daemon=True)
        self.focus_thread.start()

    def _get_last_target(self):
        """Return the most recently added target from CSV, or None if none exists."""
        if not os.path.exists(CSV_FILE):
            return None
        with open(CSV_FILE, "r", encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)  # Skip header
            rows = list(reader)
            if rows:
                # The last row has the newest target
                # row format: [Date, Time, Target]
                return rows[-1][2]  # Index 2 is the 'Target' field
        return None

    def _run_focus_timer(self):
        # Focus countdown
        total_seconds = self.focus_minutes * 60
        self._countdown(total_seconds, "Focus")

        # After focus completes, play sound if not muted
        if not self.stop_event.is_set() and not self.mute_sound.get():
            self._play_sound()

        # Rest countdown
        if not self.stop_event.is_set():
            total_seconds = self.rest_minutes * 60
            self._countdown(total_seconds, "Rest")

    def _countdown(self, total_seconds, mode_label):
        """Count down from total_seconds while updating timer label in the GUI."""
        for remaining in range(total_seconds, 0, -1):
            # Check if we should stop (e.g. user restarted timer)
            if self.stop_event.is_set():
                return
            minutes, seconds = divmod(remaining, 60)
            time_str = f"{mode_label} Time Left: {minutes:02d}:{seconds:02d}"
            self._update_label(time_str)
            time.sleep(1)

        # Final update to 00:00
        self._update_label(f"{mode_label} Time Left: 00:00")

    def _update_label(self, text):
        """Update the timer label from any thread."""
        self.master.after(0, lambda: self.timer_label.config(text=text))

    def _play_sound(self):
        """Play the alert sound if the user has not muted it."""
        try:
            sound = AudioSegment.from_file(SOUND_FILE_PATH)
            play(sound)
        except Exception as e:
            print(f"Error playing sound: {e}")

    # --- Configuration Window ---
    def open_config_window(self):
        config_win = tk.Toplevel(self.master)
        config_win.title("Configuration")

        tk.Label(config_win, text="Focus Time (minutes):").grid(row=0, column=0, padx=5, pady=5)
        focus_var = tk.IntVar(value=self.focus_minutes)
        focus_entry = tk.Entry(config_win, textvariable=focus_var)
        focus_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(config_win, text="Rest Time (minutes):").grid(row=1, column=0, padx=5, pady=5)
        rest_var = tk.IntVar(value=self.rest_minutes)
        rest_entry = tk.Entry(config_win, textvariable=rest_var)
        rest_entry.grid(row=1, column=1, padx=5, pady=5)

        def submit_config():
            try:
                new_focus = int(focus_entry.get())
                new_rest = int(rest_entry.get())
                self.focus_minutes = new_focus
                self.rest_minutes = new_rest
                messagebox.showinfo("Configuration", "Settings updated!")
                config_win.destroy()
            except ValueError:
                messagebox.showerror("Error", "Please enter valid integers.")

        tk.Button(config_win, text="Submit", command=submit_config).grid(row=2, column=0, columnspan=2, pady=10)

    # --- History Window ---
    def open_history_window(self):
        history_win = tk.Toplevel(self.master)
        history_win.title("Past Targets")

        # Search frame
        search_frame = tk.Frame(history_win)
        search_frame.pack(pady=5)

        tk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=search_var)
        search_entry.pack(side=tk.LEFT, padx=5)
        search_button = tk.Button(search_frame, text="Submit",
                                  command=lambda: self._search_targets(search_var.get(), listbox))
        search_button.pack(side=tk.LEFT, padx=5)

        # Listbox for displaying results
        listbox = tk.Listbox(history_win, width=80, height=15)
        listbox.pack(padx=5, pady=5)

        # Initial load all targets
        self._search_targets("", listbox)

    def _search_targets(self, query, listbox):
        """Load targets from CSV and filter by the query, then display in the listbox."""
        listbox.delete(0, tk.END)
        with open(CSV_FILE, "r", encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            for row in reader:
                date_str, time_str, target_text = row
                if query.lower() in target_text.lower():
                    listbox.insert(tk.END, f"{date_str} {time_str} - {target_text}")

def main():
    root = tk.Tk()
    # Adjust window size as needed
    root.geometry("240x280")
    app = TomatoFocusApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
