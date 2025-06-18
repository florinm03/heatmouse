import json
import time
import threading
import sys
import os
from datetime import datetime
from collections import defaultdict
import numpy as np
from scipy import ndimage
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.colors import LinearSegmentedColormap
import seaborn as sns

# Try to import GUI libraries with fallback
GUI_AVAILABLE = True
try:
    import tkinter as tk
    from tkinter import messagebox, ttk, filedialog
    from PIL import Image, ImageTk
except ImportError as e:
    GUI_AVAILABLE = False
    print(f"Warning: GUI libraries not available ({e}). GUI functionality will be disabled.")
    print("You can still use the command-line interface.")

# Try to import input libraries
try:
    import pynput
    from pynput import mouse, keyboard
    INPUT_AVAILABLE = True
except ImportError:
    INPUT_AVAILABLE = False
    print("Warning: pynput not available. Please install with: pip install pynput")

class MouseAnalytics:
    def __init__(self, screen_width=1920, screen_height=1080):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.mouse_positions = []
        self.click_positions = []
        self.scroll_positions = []
        self.hover_data = defaultdict(int)
        self.is_recording = False
        self.start_time = None
        self.current_pos = None
        self.last_move_time = None
        self.session_stats = {}

        # Create listeners
        self.mouse_listener = None
        self.keyboard_listener = None

        # GUI components
        self.root = None
        self.status_label = None
        self.record_button = None
        self.stats_text = None

    def get_screen_resolution(self):
        """Get screen resolution automatically"""
        try:
            if GUI_AVAILABLE:
                # Create temporary root window to get screen dimensions
                temp_root = tk.Tk()
                temp_root.withdraw()  # Hide the window
                width = temp_root.winfo_screenwidth()
                height = temp_root.winfo_screenheight()
                temp_root.destroy()
                self.screen_width = width
                self.screen_height = height
                return width, height
        except Exception as e:
            print(f"Could not get screen resolution: {e}")
            pass
        return self.screen_width, self.screen_height

    def on_mouse_move(self, x, y):
        """Track mouse movement and calculate hover time"""
        if not self.is_recording:
            return

        current_time = time.time()

        # If we have a previous position, add hover time
        if self.current_pos and self.last_move_time:
            prev_x, prev_y = self.current_pos
            hover_duration = current_time - self.last_move_time
            # Grid the position to reduce noise (10x10 pixel grid)
            grid_x = (prev_x // 10) * 10
            grid_y = (prev_y // 10) * 10
            self.hover_data[(grid_x, grid_y)] += hover_duration

        # Record position with additional metadata
        self.mouse_positions.append({
            'x': x,
            'y': y,
            'timestamp': current_time - self.start_time,
            'speed': self.calculate_speed(x, y) if self.current_pos else 0
        })

        self.current_pos = (x, y)
        self.last_move_time = current_time

    def calculate_speed(self, x, y):
        """Calculate mouse movement speed"""
        if not self.current_pos or not self.last_move_time:
            return 0

        prev_x, prev_y = self.current_pos
        distance = ((x - prev_x) ** 2 + (y - prev_y) ** 2) ** 0.5
        time_diff = time.time() - self.last_move_time

        return distance / time_diff if time_diff > 0 else 0

    def on_mouse_click(self, x, y, button, pressed):
        """Track mouse clicks"""
        if not self.is_recording:
            return

        self.click_positions.append({
            'x': x,
            'y': y,
            'button': str(button),
            'pressed': pressed,
            'timestamp': time.time() - self.start_time
        })

    def on_mouse_scroll(self, x, y, dx, dy):
        """Track mouse scroll events"""
        if not self.is_recording:
            return

        self.scroll_positions.append({
            'x': x,
            'y': y,
            'dx': dx,
            'dy': dy,
            'timestamp': time.time() - self.start_time
        })

    def on_key_press(self, key):
        """Handle keyboard shortcuts"""
        try:
            if key == keyboard.Key.esc:
                self.stop_recording()
        except AttributeError:
            pass

    def start_recording(self):
        """Start recording mouse data"""
        if not INPUT_AVAILABLE:
            print("Error: pynput library not available. Cannot start recording.")
            return False

        self.is_recording = True
        self.start_time = time.time()
        self.mouse_positions = []
        self.click_positions = []
        self.scroll_positions = []
        self.hover_data = defaultdict(int)

        # Start listeners
        try:
            self.mouse_listener = mouse.Listener(
                on_move=self.on_mouse_move,
                on_click=self.on_mouse_click,
                on_scroll=self.on_mouse_scroll
            )
            self.keyboard_listener = keyboard.Listener(
                on_press=self.on_key_press
            )

            self.mouse_listener.start()
            self.keyboard_listener.start()
        except Exception as e:
            print(f"Error starting listeners: {e}")
            self.is_recording = False
            return False

        print("Recording started! Press ESC to stop or use the GUI.")
        if self.status_label:
            self.status_label.config(text="Recording... Press ESC to stop", fg="red")
        if self.record_button:
            self.record_button.config(text="Stop Recording")

        return True

    def stop_recording(self):
        """Stop recording and save data"""
        if not self.is_recording:
            return

        self.is_recording = False

        # Stop listeners safely
        try:
            if self.mouse_listener:
                self.mouse_listener.stop()
                self.mouse_listener = None
            if self.keyboard_listener:
                self.keyboard_listener.stop()
                self.keyboard_listener = None
        except Exception as e:
            print(f"Error stopping listeners: {e}")

        # Calculate session statistics
        self.calculate_session_stats()

        # Save data
        self.save_data()

        print("Recording stopped and data saved!")
        if self.status_label:
            self.status_label.config(text="Recording stopped. Data saved.", fg="green")
        if self.record_button:
            self.record_button.config(text="Start Recording")

        self.update_stats_display()

    def calculate_session_stats(self):
        """Calculate statistics from the recording session"""
        if not self.mouse_positions:
            return

        total_time = self.mouse_positions[-1]['timestamp'] if self.mouse_positions else 0
        total_distance = sum([
            ((pos['x'] - self.mouse_positions[i-1]['x']) ** 2 +
             (pos['y'] - self.mouse_positions[i-1]['y']) ** 2) ** 0.5
            for i, pos in enumerate(self.mouse_positions[1:], 1)
        ])

        speeds = [pos['speed'] for pos in self.mouse_positions if pos['speed'] > 0]
        avg_speed = sum(speeds) / len(speeds) if speeds else 0
        max_speed = max(speeds) if speeds else 0

        clicks = len([c for c in self.click_positions if c['pressed']])

        self.session_stats = {
            'total_time': total_time,
            'total_distance': total_distance,
            'avg_speed': avg_speed,
            'max_speed': max_speed,
            'total_clicks': clicks,
            'total_movements': len(self.mouse_positions),
            'scroll_events': len(self.scroll_positions)
        }

    def save_data(self):
        """Save collected data to JSON files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create data directory if it doesn't exist
        os.makedirs('mouse_data', exist_ok=True)

        try:
            # Save mouse movements
            with open(f'mouse_data/movements_{timestamp}.json', 'w') as f:
                json.dump(self.mouse_positions, f, indent=2)

            # Save clicks
            with open(f'mouse_data/clicks_{timestamp}.json', 'w') as f:
                json.dump(self.click_positions, f, indent=2)

            # Save scroll data
            with open(f'mouse_data/scrolls_{timestamp}.json', 'w') as f:
                json.dump(self.scroll_positions, f, indent=2)

            # Save hover data
            hover_list = [{'x': pos[0], 'y': pos[1], 'duration': duration}
                         for pos, duration in self.hover_data.items()]
            with open(f'mouse_data/hover_{timestamp}.json', 'w') as f:
                json.dump(hover_list, f, indent=2)

            # Save session statistics
            with open(f'mouse_data/stats_{timestamp}.json', 'w') as f:
                json.dump(self.session_stats, f, indent=2)

            print(f"Data saved with timestamp: {timestamp}")
        except Exception as e:
            print(f"Error saving data: {e}")

    def load_data(self, movements_file, clicks_file=None, hover_file=None, scrolls_file=None):
        """Load data from JSON files"""
        try:
            with open(movements_file, 'r') as f:
                self.mouse_positions = json.load(f)

            if clicks_file and os.path.exists(clicks_file):
                with open(clicks_file, 'r') as f:
                    self.click_positions = json.load(f)

            if hover_file and os.path.exists(hover_file):
                with open(hover_file, 'r') as f:
                    hover_list = json.load(f)
                    self.hover_data = {(item['x'], item['y']): item['duration']
                                     for item in hover_list}

            if scrolls_file and os.path.exists(scrolls_file):
                with open(scrolls_file, 'r') as f:
                    self.scroll_positions = json.load(f)

            # Recalculate stats
            self.calculate_session_stats()
            print(f"Data loaded successfully from {movements_file}")
            return True
        except Exception as e:
            print(f"Error loading data: {e}")
            return False

    def create_movement_heatmap(self, grid_size=50, save_path=None):
        """Create heatmap from mouse movements"""
        if not self.mouse_positions:
            print("No movement data available!")
            return

        if save_path is None:
            save_path = f'heatmaps/movement_heatmap_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'

        os.makedirs('heatmaps', exist_ok=True)

        try:
            # Create grid
            x_bins = np.linspace(0, self.screen_width, grid_size)
            y_bins = np.linspace(0, self.screen_height, grid_size)

            # Extract coordinates
            x_coords = [pos['x'] for pos in self.mouse_positions]
            y_coords = [pos['y'] for pos in self.mouse_positions]

            # Create 2D histogram
            heatmap, _, _ = np.histogram2d(x_coords, y_coords, bins=[x_bins, y_bins])

            # Apply Gaussian filter for smoother heatmap
            heatmap = ndimage.gaussian_filter(heatmap, sigma=1.0)

            # Create plot
            plt.figure(figsize=(14, 10))
            plt.imshow(heatmap.T, origin='lower', extent=[0, self.screen_width, 0, self.screen_height],
                      cmap='hot', interpolation='bilinear', alpha=0.8)
            plt.colorbar(label='Movement Intensity')
            plt.title(f'Mouse Movement Heatmap\nTotal Movements: {len(self.mouse_positions):,}')
            plt.xlabel('X Position (pixels)')
            plt.ylabel('Y Position (pixels)')
            plt.tight_layout()
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()  # Important: close the figure to free memory
            print(f"Movement heatmap saved as {save_path}")
        except Exception as e:
            print(f"Error creating movement heatmap: {e}")

    def create_comprehensive_dashboard(self, save_path=None):
        """Create a comprehensive dashboard with multiple visualizations"""
        if save_path is None:
            save_path = f'heatmaps/dashboard_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'

        os.makedirs('heatmaps', exist_ok=True)

        try:
            fig = plt.figure(figsize=(20, 16))
            gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

            # 1. Movement heatmap
            ax1 = fig.add_subplot(gs[0, 0])
            if self.mouse_positions:
                x_coords = [pos['x'] for pos in self.mouse_positions]
                y_coords = [pos['y'] for pos in self.mouse_positions]
                x_bins = np.linspace(0, self.screen_width, 50)
                y_bins = np.linspace(0, self.screen_height, 50)
                heatmap, _, _ = np.histogram2d(x_coords, y_coords, bins=[x_bins, y_bins])
                heatmap = ndimage.gaussian_filter(heatmap, sigma=1.0)

                im1 = ax1.imshow(heatmap.T, origin='lower',
                               extent=[0, self.screen_width, 0, self.screen_height],
                               cmap='hot', interpolation='bilinear', alpha=0.8)
                ax1.set_title('Movement Heatmap')
                ax1.set_xlabel('X Position')
                ax1.set_ylabel('Y Position')

            # 2. Click heatmap
            ax2 = fig.add_subplot(gs[0, 1])
            if self.click_positions:
                click_x = [pos['x'] for pos in self.click_positions if pos['pressed']]
                click_y = [pos['y'] for pos in self.click_positions if pos['pressed']]
                if click_x and click_y:
                    ax2.hexbin(click_x, click_y, gridsize=20, cmap='Reds', alpha=0.8)
                    ax2.set_title(f'Click Heatmap ({len(click_x)} clicks)')
                    ax2.set_xlabel('X Position')
                    ax2.set_ylabel('Y Position')
                    ax2.set_xlim(0, self.screen_width)
                    ax2.set_ylim(0, self.screen_height)

            # 3. Activity timeline
            ax3 = fig.add_subplot(gs[0, 2])
            if self.mouse_positions:
                timestamps = [pos['timestamp'] for pos in self.mouse_positions]
                ax3.hist(timestamps, bins=50, alpha=0.7, color='blue', edgecolor='black')
                ax3.set_title('Activity Timeline')
                ax3.set_xlabel('Time (seconds)')
                ax3.set_ylabel('Activity Count')

            # 4. Speed distribution
            ax4 = fig.add_subplot(gs[1, 0])
            if self.mouse_positions:
                speeds = [pos.get('speed', 0) for pos in self.mouse_positions if pos.get('speed', 0) > 0]
                if speeds:
                    ax4.hist(speeds, bins=30, alpha=0.7, color='green', edgecolor='black')
                    ax4.set_title('Speed Distribution')
                    ax4.set_xlabel('Speed (pixels/second)')
                    ax4.set_ylabel('Frequency')

            # 5. Hover duration analysis
            ax5 = fig.add_subplot(gs[1, 1])
            if self.hover_data:
                durations = list(self.hover_data.values())
                ax5.hist(durations, bins=30, alpha=0.7, color='orange', edgecolor='black')
                ax5.set_title('Hover Duration Distribution')
                ax5.set_xlabel('Duration (seconds)')
                ax5.set_ylabel('Frequency')

            # 6. Statistics summary
            ax6 = fig.add_subplot(gs[1, 2])
            ax6.axis('off')
            if self.session_stats:
                stats_text = f"""Session Statistics:

Total Time: {self.session_stats.get('total_time', 0):.1f}s
Total Distance: {self.session_stats.get('total_distance', 0):.0f}px
Average Speed: {self.session_stats.get('avg_speed', 0):.1f}px/s
Max Speed: {self.session_stats.get('max_speed', 0):.1f}px/s
Total Clicks: {self.session_stats.get('total_clicks', 0)}
Mouse Movements: {self.session_stats.get('total_movements', 0):,}
Scroll Events: {self.session_stats.get('scroll_events', 0)}"""
                ax6.text(0.1, 0.9, stats_text, transform=ax6.transAxes, fontsize=12,
                        verticalalignment='top', fontfamily='monospace',
                        bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray"))

            # 7. Movement path (sample)
            ax7 = fig.add_subplot(gs[2, :])
            if self.mouse_positions and len(self.mouse_positions) > 100:
                # Sample points to avoid overcrowding
                step = max(1, len(self.mouse_positions) // 1000)
                sampled_positions = self.mouse_positions[::step]

                x_path = [pos['x'] for pos in sampled_positions]
                y_path = [pos['y'] for pos in sampled_positions]

                ax7.plot(x_path, y_path, alpha=0.6, linewidth=0.5, color='blue')
                ax7.scatter(x_path[0], y_path[0], c='green', s=50, label='Start', zorder=5)
                ax7.scatter(x_path[-1], y_path[-1], c='red', s=50, label='End', zorder=5)
                ax7.set_title('Mouse Movement Path (Sampled)')
                ax7.set_xlabel('X Position')
                ax7.set_ylabel('Y Position')
                ax7.legend()
                ax7.set_xlim(0, self.screen_width)
                ax7.set_ylim(0, self.screen_height)

            plt.suptitle('Mouse Analytics Dashboard', fontsize=16, fontweight='bold')
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()  # Important: close the figure to free memory
            print(f"Comprehensive dashboard saved as {save_path}")
            return save_path
        except Exception as e:
            print(f"Error creating comprehensive dashboard: {e}")
            return None

    def update_stats_display(self):
        """Update the stats display in the GUI"""
        if not self.stats_text or not self.session_stats:
            return

        try:
            stats_text = f"""Session Statistics:

Total Time: {self.session_stats.get('total_time', 0):.1f} seconds
Total Distance: {self.session_stats.get('total_distance', 0):.0f} pixels
Average Speed: {self.session_stats.get('avg_speed', 0):.1f} pixels/second
Max Speed: {self.session_stats.get('max_speed', 0):.1f} pixels/second
Total Clicks: {self.session_stats.get('total_clicks', 0)}
Mouse Movements: {self.session_stats.get('total_movements', 0):,}
Scroll Events: {self.session_stats.get('scroll_events', 0)}
Unique Hover Locations: {len(self.hover_data)}"""

            self.stats_text.config(state="normal")
            self.stats_text.delete("1.0", tk.END)
            self.stats_text.insert("1.0", stats_text)
            self.stats_text.config(state="disabled")
        except Exception as e:
            print(f"Error updating stats display: {e}")

    def create_gui(self):
        """Create an enhanced GUI for controlling the analytics"""
        if not GUI_AVAILABLE:
            print("GUI not available. tkinter is not installed.")
            return False

        try:
            self.root = tk.Tk()
            self.root.title("Enhanced Mouse Analytics Tool")
            self.root.geometry("600x500")

            # Set protocol for window closing
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

            # Main frame
            main_frame = ttk.Frame(self.root, padding="10")
            main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

            # Status label
            self.status_label = tk.Label(main_frame, text="Ready to record", fg="green", font=("Arial", 12))
            self.status_label.grid(row=0, column=0, columnspan=2, pady=5)

            # Buttons frame
            buttons_frame = ttk.Frame(main_frame)
            buttons_frame.grid(row=1, column=0, columnspan=2, pady=10)

            # Record button
            self.record_button = tk.Button(
                buttons_frame, text="Start Recording",
                command=self.toggle_recording,
                font=("Arial", 12), bg="lightgreen", width=15
            )
            self.record_button.grid(row=0, column=0, padx=5)

            # Generate heatmaps button
            heatmap_button = tk.Button(
                buttons_frame, text="Generate Dashboard",
                command=self.generate_dashboard_threaded,
                font=("Arial", 12), bg="lightblue", width=15
            )
            heatmap_button.grid(row=0, column=1, padx=5)

            # Load data button
            load_button = tk.Button(
                buttons_frame, text="Load Data",
                command=self.load_data_gui,
                font=("Arial", 12), bg="lightyellow", width=15
            )
            load_button.grid(row=0, column=2, padx=5)

            # Statistics display
            stats_label = tk.Label(main_frame, text="Session Statistics:", font=("Arial", 11, "bold"))
            stats_label.grid(row=2, column=0, columnspan=2, pady=(20, 5), sticky="w")

            self.stats_text = tk.Text(main_frame, height=10, width=70, font=("Courier", 9))
            self.stats_text.grid(row=3, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E))

            # Scrollbar for stats
            scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.stats_text.yview)
            scrollbar.grid(row=3, column=2, sticky=(tk.N, tk.S))
            self.stats_text.configure(yscrollcommand=scrollbar.set)

            # Instructions
            instructions = """Instructions:
1. Click 'Start Recording' to begin tracking your mouse
2. Use your mouse normally - move, click, scroll
3. Press ESC or click 'Stop Recording' to finish
4. Click 'Generate Dashboard' to create comprehensive visualizations
5. Use 'Load Data' to analyze previously saved sessions

Features:
• Movement tracking with speed analysis
• Click and scroll tracking
• Hover duration analysis
• Comprehensive statistics
• Multiple visualization types

Note: Dashboard images are saved to 'heatmaps' folder"""

            info_text = tk.Text(main_frame, height=14, width=70, font=("Arial", 9))
            info_text.grid(row=4, column=0, columnspan=2, pady=10, sticky=(tk.W, tk.E))
            info_text.insert("1.0", instructions)
            info_text.config(state="disabled")

            # Configure grid weights
            self.root.columnconfigure(0, weight=1)
            self.root.rowconfigure(0, weight=1)
            main_frame.columnconfigure(0, weight=1)

            return True
        except Exception as e:
            print(f"Error creating GUI: {e}")
            return False

    def on_closing(self):
        """Handle window closing"""
        if self.is_recording:
            self.stop_recording()
        self.root.destroy()

    def toggle_recording(self):
        """Toggle recording on/off"""
        if self.is_recording:
            self.stop_recording()
        else:
            success = self.start_recording()
            if not success and self.status_label:
                self.status_label.config(text="Error: Cannot start recording (pynput not available)", fg="red")

    def generate_dashboard_threaded(self):
        """Generate comprehensive dashboard in a separate thread to prevent GUI freezing"""
        def generate():
            if not self.mouse_positions:
                if self.status_label:
                    self.status_label.config(text="No data to generate dashboard", fg="red")
                return

            if self.status_label:
                self.status_label.config(text="Generating dashboard...", fg="blue")

            try:
                result = self.create_comprehensive_dashboard()
                if result and self.status_label:
                    self.status_label.config(text="Dashboard generated successfully!", fg="green")
                elif self.status_label:
                    self.status_label.config(text="Error generating dashboard", fg="red")
            except Exception as e:
                print(f"Error in dashboard generation: {e}")
                if self.status_label:
                    self.status_label.config(text="Error generating dashboard", fg="red")

        # Run in separate thread to prevent GUI freezing
        thread = threading.Thread(target=generate, daemon=True)
        thread.start()

    def generate_dashboard(self):
        """Generate comprehensive dashboard (non-threaded version)"""
        if not self.mouse_positions:
            if GUI_AVAILABLE:
                messagebox.showwarning("No Data", "No mouse tracking data available. Please record some data first.")
            else:
                print("No mouse tracking data available. Please record some data first.")
            return

        try:
            result = self.create_comprehensive_dashboard()
            if result:
                if GUI_AVAILABLE:
                    messagebox.showinfo("Success", f"Dashboard generated successfully!\nSaved as: {result}")
                else:
                    print(f"Dashboard generated successfully! Saved as: {result}")
            else:
                if GUI_AVAILABLE:
                    messagebox.showerror("Error", "Failed to generate dashboard")
                else:
                    print("Failed to generate dashboard")
        except Exception as e:
            error_msg = f"Error generating dashboard: {str(e)}"
            if GUI_AVAILABLE:
                messagebox.showerror("Error", error_msg)
            else:
                print(error_msg)

    def load_data_gui(self):
        """Load data using GUI file dialog"""
        if not GUI_AVAILABLE:
            print("GUI not available for file selection.")
            return

        try:
            movements_file = filedialog.askopenfilename(
                title="Select movements JSON file",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                initialdir="mouse_data" if os.path.exists("mouse_data") else "."
            )

            if movements_file:
                success = self.load_data(movements_file)
                if success:
                    messagebox.showinfo("Success", "Data loaded successfully!")
                    self.update_stats_display()
                else:
                    messagebox.showerror("Error", "Failed to load data.")
        except Exception as e:
            messagebox.showerror("Error", f"Error loading data: {str(e)}")

    def run_gui(self):
        """Run the GUI application"""
        if self.create_gui():
            try:
                self.root.mainloop()
            except Exception as e:
                print(f"Error running GUI: {e}")
        else:
            print("Cannot run GUI. Please use command-line interface.")

def main():
    """Main function to run the mouse analytics tool"""
    # Get screen resolution
    analytics = MouseAnalytics()
    analytics.get_screen_resolution()

    print("Enhanced Mouse Analytics Tool")
    print("=" * 40)

    if not INPUT_AVAILABLE:
        print("Warning: pynput not available. Recording functionality disabled.")
        print("Install with: pip install pynput")

    if not GUI_AVAILABLE:
        print("Warning: GUI libraries not available. GUI functionality disabled.")
        print("You can still use command-line features.")

    print("\nChoose an option:")
    print("1. Run with GUI (if available)")
    print("2. Run command line recording")
    print("3. Load existing data and generate dashboard")
    print("4. Exit")

    while True:
        try:
            choice = input("\nEnter choice (1-4): ").strip()

            if choice == "1":
                if GUI_AVAILABLE:
                    analytics.run_gui()
                else:
                    print("GUI not available. Try option 2 or 3.")
                    continue
                break

            elif choice == "2":
                if not INPUT_AVAILABLE:
                    print("Recording not available. pynput library not installed.")
                    continue

                print("Starting recording... Press ESC to stop")
                success = analytics.start_recording()
                if success:
                    try:
                        # Keep the program running
                        while analytics.is_recording:
                            time.sleep(1)
                    except KeyboardInterrupt:
                        analytics.stop_recording()

                    # Generate dashboard
                    if analytics.mouse_positions:
                        print("\nGenerating comprehensive dashboard...")
                        analytics.create_comprehensive_dashboard()
                        print("Analysis complete!")
                break

            elif choice == "3":
                # Load existing data
                print("\nAvailable data files:")
                data_dir = "mouse_data"
                if os.path.exists(data_dir):
                    files = [f for f in os.listdir(data_dir) if f.startswith('movements_')]
                    if files:
                        for i, file in enumerate(files, 1):
                            print(f"{i}. {file}")

                        try:
                            file_choice = int(input("Select file number (or 0 for custom path): "))
                            if file_choice == 0:
                                movements_file = input("Enter path to movements JSON file: ").strip()
                            else:
                                movements_file = os.path.join(data_dir, files[file_choice - 1])
                        except (ValueError, IndexError):
                            print("Invalid selection.")
                            continue
                    else:
                        movements_file = input("Enter path to movements JSON file: ").strip()
                else:
                    movements_file = input("Enter path to movements JSON file: ").strip()

                # Try to find corresponding files
                base_name = os.path.basename(movements_file).replace('movements_', '').replace('.json', '')
                data_path = os.path.dirname(movements_file)

                clicks_file = os.path.join(data_path, f'clicks_{base_name}.json')
                hover_file = os.path.join(data_path, f'hover_{base_name}.json')
                scrolls_file = os.path.join(data_path, f'scrolls_{base_name}.json')

                # Load data
                success = analytics.load_data(
                    movements_file,
                    clicks_file if os.path.exists(clicks_file) else None,
                    hover_file if os.path.exists(hover_file) else None,
                    scrolls_file if os.path.exists(scrolls_file) else None
                )

                if success:
                    print("Generating comprehensive dashboard...")
                    analytics.create_comprehensive_dashboard()
                    print("Analysis complete!")
                else:
                    print("Failed to load data.")
                break

            elif choice == "4":
                print("Goodbye!")
                break

            else:
                print("Invalid choice. Please enter 1, 2, 3, or 4.")

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
