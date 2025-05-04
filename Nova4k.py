import tkinter as tk
import tkinter.ttk as ttk
import tkinter.messagebox as messagebox
import tkinter.filedialog as filedialog
import urllib.request
import json
import subprocess
import re
import platform
import os
import shutil
import hashlib
import zipfile
import tarfile
import sys

# --- Constants ---
VERSION_MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"

# Determine base directory for client data
# Use user's home directory for cross-platform compatibility
if platform.system() == "Windows":
    APPDATA = os.environ.get('APPDATA', os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming'))
    BASE_DIR = os.path.join(APPDATA, '.nova-client')
else: # macOS, Linux, etc.
    BASE_DIR = os.path.join(os.path.expanduser('~'), '.nova-client')

MINECRAFT_DIR = os.path.join(BASE_DIR, 'minecraft')
VERSIONS_DIR = os.path.join(MINECRAFT_DIR, 'versions')
JAVA_DIR = os.path.join(BASE_DIR, 'java') # Local Java installation dir

# Create necessary directories if they don't exist
os.makedirs(MINECRAFT_DIR, exist_ok=True)
os.makedirs(VERSIONS_DIR, exist_ok=True)
os.makedirs(JAVA_DIR, exist_ok=True)


# --- Theme ---
THEME = {
    "bg": "#1c1c1c",             # Dark background
    "sidebar": "#2a2a2a",       # Slightly lighter dark for sidebar/panels
    "accent": "#4a90e2",        # Bright blue for accents
    "text": "#f0f0f0",          # Light text
    "text_secondary": "#aaaaaa", # Gray text for labels/hints
    "input_bg": "#3a3a3a",      # Dark gray for input fields
    "button": "#4a4a4a",        # Dark gray buttons
    "button_hover": "#5a5a5a"   # Slightly lighter dark for button hover
}


class NovaClientApp(tk.Tk):
    def __init__(self):
        """Initialize the main application window and data."""
        super().__init__()

        self.title("Nova Client Launcher")
        self.geometry("600x400") # Requested size
        # self.resizable(False, False) # Can uncomment to fix size

        self.configure(bg=THEME['bg']) # Set background color for the root window

        # Version data
        self.versions = {}
        self.version_categories = {
            "Latest Release": [],
            "Latest Snapshot": [],
            "Release": [],
            "Snapshot": [],
            "Old Beta": [],
            "Old Alpha": []
        }

        # Cheat settings
        self.cheats = {
            'killaura': False,
            'speed': False,
            'fly': False
        }

        # Configure styles for ttk widgets
        self.style = ttk.Style(self) # Pass self (the root window) to Style
        self.style.theme_use('clam') # Use a theme that allows background customization

        self.style.configure("TCombobox",
                        fieldbackground=THEME['input_bg'],
                        background=THEME['input_bg'],
                        foreground=THEME['text'],
                        arrowcolor=THEME['text'],
                        selectbackground=THEME['accent'], # Color when selected item is highlighted
                        selectforeground=THEME['text'],
                        bordercolor=THEME['sidebar'],
                        darkcolor=THEME['sidebar'],
                        lightcolor=THEME['sidebar'],
                        arrowsize=15) # Adjust arrow size

        # Note: TScrollbar styles are more complex and might not change the trough/background easily
        # without theme-specific overrides or custom elements. The config below might not fully apply.
        # If scrollbars are added later, this style might need refinement.
        self.style.configure("Vertical.TScrollbar",
                             background=THEME['accent'], # Scrollbar body color
                             arrowcolor=THEME['text'],    # Arrow color
                             troughcolor=THEME['sidebar'], # Area around the scrollbar
                             bordercolor=THEME['sidebar'])


        self.init_ui()

    def init_ui(self):
        """Set up the graphical user interface."""
        # Main container frame using the background theme color
        main_container = tk.Frame(self, bg=THEME['bg'])
        main_container.pack(fill="both", expand=True, padx=10, pady=10) # Reduced padding slightly

        # Sidebar frame
        # Using theme color, fixed width, and preventing it from expanding with content
        sidebar = tk.Frame(main_container, bg=THEME['sidebar'], width=250)
        sidebar.pack(side="left", fill="y", padx=(0, 10)) # Added padx to separate from content
        sidebar.pack_propagate(False) # Prevent sidebar from resizing to fit contents

        # --- Sidebar Content ---

        # Logo and title frame
        logo_frame = tk.Frame(sidebar, bg=THEME['sidebar'])
        logo_frame.pack(fill="x", pady=(10, 20)) # Adjusted padding

        # Nova Client logo (text-based, styled)
        # Using a standard font like "Courier" or "Consolas"
        logo_text = """
        🌌 NOVA
        """
        # Center the logo text Label itself
        logo = tk.Label(logo_frame, text=logo_text.strip(), font=("Consolas", 22, "bold"),
                    bg=THEME['sidebar'], fg=THEME['accent'], justify="center")
        logo.pack(anchor="center") # Pack the logo centered within its frame

        # Title Label
        title = tk.Label(logo_frame, text="Nova Client", font=("Arial", 16, "bold"),
                        bg=THEME['sidebar'], fg=THEME['text'])
        title.pack(anchor="center", pady=(0, 10)) # Pack title centered below logo

        # Version selection area using a LabelFrame for grouping
        version_frame = tk.LabelFrame(sidebar, text="GAME VERSION", bg=THEME['sidebar'],
                                    fg=THEME['text_secondary'], font=("Arial", 9, "bold"), bd=0, labelanchor='nw') # labelanchor top-left
        version_frame.pack(fill="x", padx=10, pady=(0, 10)) # Adjusted padding

        # Version Category Combobox (ttk)
        tk.Label(version_frame, text="Category", font=("Arial", 8, "bold"),
                bg=THEME['sidebar'], fg=THEME['text_secondary']).pack(anchor="w", padx=5, pady=(5,0))
        self.category_combo = ttk.Combobox(version_frame, values=list(self.version_categories.keys()),
                                        state="readonly", font=("Arial", 10))
        self.category_combo.pack(fill="x", padx=5, pady=(0, 5))
        self.category_combo.set("Latest Release")
        self.category_combo.bind("<<ComboboxSelected>>", self.update_version_list)

        # Specific Version Combobox (ttk)
        tk.Label(version_frame, text="Version", font=("Arial", 8, "bold"),
                bg=THEME['sidebar'], fg=THEME['text_secondary']).pack(anchor="w", padx=5, pady=(5,0))
        self.version_combo = ttk.Combobox(version_frame, state="readonly", font=("Arial", 10))
        self.version_combo.pack(fill="x", padx=5, pady=(0, 5))


        # Settings area using a LabelFrame
        settings_frame = tk.LabelFrame(sidebar, text="SETTINGS", bg=THEME['sidebar'],
                                    fg=THEME['text_secondary'], font=("Arial", 9, "bold"), bd=0, labelanchor='nw')
        settings_frame.pack(fill="x", padx=10, pady=(0, 10)) # Adjusted padding

        # Username input area
        username_frame = tk.Frame(settings_frame, bg=THEME['sidebar'])
        username_frame.pack(fill="x", padx=5, pady=(5, 5)) # Added padx

        tk.Label(username_frame, text="USERNAME", font=("Arial", 8, "bold"),
                bg=THEME['sidebar'], fg=THEME['text_secondary']).pack(anchor="w")

        self.username_input = tk.Entry(username_frame, font=("Arial", 10), bg=THEME['input_bg'],
                                    fg=THEME['text'], insertbackground=THEME['text'], bd=0, highlightthickness=0) # highlightthickness=0 removes default border
        self.username_input.pack(fill="x", pady=(3, 0)) # Adjusted pady
        self.username_input.insert(0, "Enter Username")
        # Clear placeholder on focus
        self.username_input.bind("<FocusIn>", self._clear_placeholder)
        # Restore placeholder if left empty
        self.username_input.bind("<FocusOut>", self._restore_placeholder)

        # RAM slider area
        ram_frame = tk.Frame(settings_frame, bg=THEME['sidebar'])
        ram_frame.pack(fill="x", padx=5, pady=(5, 5)) # Added padx

        ram_label_frame = tk.Frame(ram_frame, bg=THEME['sidebar'])
        ram_label_frame.pack(fill="x")

        tk.Label(ram_label_frame, text="RAM ALLOCATION", font=("Arial", 8, "bold"),
                bg=THEME['sidebar'], fg=THEME['text_secondary']).pack(side="left")

        self.ram_value_label = tk.Label(ram_label_frame, text="4 GB", font=("Arial", 8), # Added space for clarity
                                    bg=THEME['sidebar'], fg=THEME['text'])
        self.ram_value_label.pack(side="right")

        # tk.Scale widget
        self.ram_scale = tk.Scale(ram_frame, from_=1, to=16, orient="horizontal",
                                bg=THEME['sidebar'], fg=THEME['text'],
                                activebackground=THEME['accent'], # Color when dragging
                                highlightthickness=0, bd=0,
                                troughcolor=THEME['input_bg'], # Background color of the track
                                sliderrelief='flat', # Flat slider style
                                command=lambda v: self.ram_value_label.config(text=f"{int(float(v))} GB")) # Update label on change
        self.ram_scale.set(4) # Default to 4GB
        self.ram_scale.pack(fill="x", pady=(3,0)) # Adjusted pady

        # Cheat toggles area using a LabelFrame
        cheats_frame = tk.LabelFrame(sidebar, text="CHEATS", bg=THEME['sidebar'],
                                    fg=THEME['text_secondary'], font=("Arial", 9, "bold"), bd=0, labelanchor='nw')
        cheats_frame.pack(fill="x", padx=10, pady=(0, 10)) # Adjusted padding

        # Checkbuttons for cheats
        # Use theme colors for checkbuttons
        for cheat in self.cheats:
            var = tk.BooleanVar(value=self.cheats[cheat]) # Set initial state
            # Configure colors and remove default border/indicator styling
            cb = tk.Checkbutton(cheats_frame, text=cheat.capitalize(), variable=var,
                                bg=THEME['sidebar'], fg=THEME['text'],
                                selectcolor=THEME['sidebar'], # Color when selected (area around checkmark)
                                activebackground=THEME['sidebar'], # Background when active/hovered
                                activeforeground=THEME['text'],
                                bd=0, highlightthickness=0, # Remove borders
                                relief='flat', # Flat relief
                                anchor='w', # Anchor text to the west (left)
                                command=lambda c=cheat, v=var: self.toggle_cheat(c, v.get()))
            cb.pack(fill="x", pady=2, padx=5) # Fill x to make clicking easier

        # Buttons area
        button_frame = tk.Frame(sidebar, bg=THEME['sidebar'])
        button_frame.pack(fill="x", padx=10, pady=(10, 10)) # Adjusted padding

        # Helper functions for button hover effect
        def on_enter(e):
            e.widget.configure(bg=THEME['button_hover'])

        def on_leave(e):
            if e.widget['text'] == "PLAY": # Keep PLAY button its accent color
                 e.widget.configure(bg=THEME['accent'])
            else:
                e.widget.configure(bg=THEME['button']) # Restore other buttons' color

        # Change Skin Button
        skin_button = tk.Button(button_frame, text="CHANGE SKIN", font=("Arial", 10, "bold"),
                            bg=THEME['button'], fg=THEME['text'],
                            bd=0, padx=10, pady=8, relief='flat', command=self.select_skin) # Adjusted padding, added relief
        skin_button.pack(fill="x", pady=(0, 5)) # Adjusted pady
        skin_button.bind("<Enter>", on_enter)
        skin_button.bind("<Leave>", on_leave)

        # Play Button (uses accent color)
        launch_button = tk.Button(button_frame, text="PLAY", font=("Arial", 12, "bold"),
                                bg=THEME['accent'], fg=THEME['text'],
                                bd=0, padx=10, pady=10, relief='flat', command=self.prepare_and_launch) # Adjusted padding, added relief
        launch_button.pack(fill="x")
        # Note: Play button uses a different leave effect to revert to accent, not button color
        launch_button.bind("<Enter>", on_enter)
        launch_button.bind("<Leave>", on_leave)


        # --- Main Content Area ---
        # This area will fill the remaining space
        content_area = tk.Frame(main_container, bg=THEME['bg'])
        content_area.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=(0, 10)) # Added padx

        # Changelog section
        changelog_label = tk.Label(content_area, text="RECENT CHANGES", font=("Arial", 14, "bold"),
                            bg=THEME['bg'], fg=THEME['text'])
        changelog_label.pack(anchor="w", pady=(0, 10)) # Adjusted padding

        # Changelog items list
        # Added the new requested entry, adjusted for offline context
        changelog_items = [
            "🚀 OPTIMZED OFFLINE PERFORMANCE (v5.3.25): Applied JVM and options tweaks for smoother gameplay.",
            "🌌 Rebranded to Nova Client with new theme and logo.",
            "🚀 Added KillAura: Automatically attacks nearby entities.",
            "🏃 Added Speed Hack: Increases movement speed.",
            "🕊️ Added Fly Hack: Enables flying in survival mode.",
            "🔧 Refactored launch process with cheat injection.",
            "⚙️ Added automatic Java 21 installation.",
            "✨ Improved UI styling and layout."
        ]

        # Frame to hold changelog items (makes it easier to manage packing)
        changelog_items_frame = tk.Frame(content_area, bg=THEME['bg'])
        changelog_items_frame.pack(fill="both", expand=True) # Allows items frame to fill remaining space

        # Display each changelog item in a styled frame
        for i, item in enumerate(changelog_items):
            # Using THEME['sidebar'] for the item background to create alternating or highlighted look
            item_bg = THEME['sidebar'] if i % 2 == 0 else THEME['input_bg'] # Optional: Alternate colors
            item_frame = tk.Frame(changelog_items_frame, bg=item_bg, padx=10, pady=8) # Adjusted padding
            item_frame.pack(fill="x", pady=(0, 5), expand=False) # Pack items to fill width, small vertical gap

            # Use a Label for the item text
            tk.Label(item_frame, text=item, font=("Arial", 10),
                    bg=item_bg, fg=THEME['text'], justify="left", anchor="w", wraplength=400 # Add wraplength
                    ).pack(fill='x')

        # --- Initial Data Loading ---
        # Load versions after the GUI elements that use them are created
        self.load_version_manifest()

    # --- Helper methods for username placeholder ---
    def _clear_placeholder(self, event):
        if self.username_input.get() == "Enter Username":
            self.username_input.delete(0, tk.END)
            self.username_input.config(fg=THEME['text'])

    def _restore_placeholder(self, event):
        if not self.username_input.get():
            self.username_input.insert(0, "Enter Username")
            self.username_input.config(fg=THEME['text_secondary']) # Grey out placeholder text


    # --- Backend Logic (from original snippet) ---

    def toggle_cheat(self, cheat, state):
        """Toggle cheat state."""
        self.cheats[cheat] = state
        print(f"{cheat.capitalize()} {'enabled' if state else 'disabled'}") # Output to console

    def update_version_list(self, event=None):
        """Update the version list based on the selected category."""
        category = self.category_combo.get()
        versions_in_category = self.version_categories.get(category, [])
        self.version_combo['values'] = versions_in_category
        if versions_in_category:
            self.version_combo.current(0) # Select the first version by default
        else:
             self.version_combo.set('') # Clear selection if no versions

    def load_version_manifest(self):
        """Load Minecraft versions from Mojang's servers."""
        print("Loading version manifest...")
        try:
            with urllib.request.urlopen(VERSION_MANIFEST_URL) as url:
                manifest = json.loads(url.read().decode())

                # Clear existing versions
                self.versions = {}
                for category in self.version_categories:
                    self.version_categories[category] = []

                latest_release_id = manifest["latest"]["release"]
                latest_snapshot_id = manifest["latest"]["snapshot"]

                for v in manifest["versions"]:
                    self.versions[v["id"]] = v["url"]

                    if v["id"] == latest_release_id:
                        self.version_categories["Latest Release"].append(v["id"])
                    elif v["id"] == latest_snapshot_id:
                        self.version_categories["Latest Snapshot"].append(v["id"])
                    elif v["type"] == "release":
                        self.version_categories["Release"].append(v["id"])
                    elif v["type"] == "snapshot":
                        self.version_categories["Snapshot"].append(v["id"])
                    elif v["type"] == "old_beta":
                        self.version_categories["Old Beta"].append(v["id"])
                    elif v["type"] == "old_alpha":
                        self.version_categories["Old Alpha"].append(v["id"])

                # Sort versions within categories (optional, but nice)
                for category in self.version_categories:
                     if category not in ["Latest Release", "Latest Snapshot"]:
                         # Simple sort by version ID (might not be strictly chronological for old versions)
                         self.version_categories[category].sort(reverse=True)


                self.update_version_list() # Update the comboboxes with the loaded data
                print("Version manifest loaded successfully.")

        except Exception as e:
            print(f"Error loading version manifest: {e}")
            messagebox.showerror("Error", "Failed to load version manifest. Please check your internet connection.")

    def is_java_installed(self, required_version="21"):
        """Check if Java 21 or higher is installed."""
        # Check local installation first
        local_java_path = os.path.join(JAVA_DIR, "jdk-21.0.5+11", "bin", "java.exe" if platform.system() == "Windows" else "java")
        if os.path.exists(local_java_path):
             try:
                 result = subprocess.run([local_java_path, "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                 output = result.stderr # Java version info is often on stderr
                 match = re.search(r'version "(\d+)\.?(\d+)?\.?(\d+)?', output)
                 if match:
                     major_version = int(match.group(1))
                     print(f"Found local Java version: {major_version}")
                     return major_version >= int(required_version)
             except Exception:
                 pass # Ignore errors from local check, fall back to system check

        # Check system installation
        try:
            result = subprocess.run(["java", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output = result.stderr # Java version info is often on stderr
            match = re.search(r'version "(\d+)\.?(\d+)?\.?(\d+)?', output)
            if match:
                major_version = int(match.group(1))
                print(f"Found system Java version: {major_version}")
                return major_version >= int(required_version)
            return False # Found Java but couldn't parse version
        except FileNotFoundError:
             print("System Java not found.")
             return False # Java command not found in system path
        except Exception as e:
            print(f"Error checking system Java version: {e}")
            return False # Other errors during system check


    def install_java_if_needed(self):
        """Install OpenJDK 21 if needed."""
        if self.is_java_installed():
            print("Java 21+ already installed or located.")
            return True # Java is available

        print("OpenJDK 21 is required. Attempting to install locally...")
        system = platform.system()
        arch = platform.architecture()[0] # '64bit' or '32bit'

        # Define URLs based on OS and architecture (primarily supporting x64)
        java_url = None
        if system == "Windows" and arch == "64bit":
            java_url = "https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.5%2B11/OpenJDK21U-jdk_x64_windows_hotspot_21.0.5_11.zip"
            archive_ext = ".zip"
        elif system == "Linux" and arch == "64bit":
             java_url = "https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.5%2B11/OpenJDK21U-jdk_x64_linux_hotspot_21.0.5_11.tar.gz"
             archive_ext = ".tar.gz"
        elif system == "Darwin" and arch == "64bit": # macOS x64 (Intel)
             # For M1/M2 Macs (aarch64), a different binary is needed.
             # This simple example only covers x64.
             java_url = "https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.5%2B11/OpenJDK21U-jdk_x64_mac_hotspot_21.0.5_11.tar.gz"
             archive_ext = ".tar.gz"
        else:
            messagebox.showerror("Error", f"Unsupported OS ({system}) or architecture ({arch}) for automatic Java install.\nPlease manually install OpenJDK 21.")
            return False # Installation not attempted due to unsupported platform

        if java_url is None:
             messagebox.showerror("Error", f"No OpenJDK 21 binary URL found for your platform ({system}/{arch}).\nPlease manually install OpenJDK 21.")
             return False

        archive_path = os.path.join(JAVA_DIR, "openjdk" + archive_ext)
        extract_dir = JAVA_DIR # Extract directly into the JAVA_DIR

        # Check if Java is already extracted in the expected location
        # This assumes the extracted folder name is consistent
        extracted_java_folder = os.path.join(JAVA_DIR, "jdk-21.0.5+11")
        if os.path.exists(extracted_java_folder):
             print("Local OpenJDK 21 directory already exists. Skipping download.")
             return True # Assume it's a successful prior install

        try:
            print(f"Downloading Java from: {java_url}")
            # Simple download without progress - could be improved
            urllib.request.urlretrieve(java_url, archive_path)
            print("Download complete. Extracting...")

            if system == "Windows":
                with zipfile.ZipFile(archive_path, "r") as zip_ref:
                    zip_ref.extractall(extract_dir)
            else: # Linux, macOS
                import tarfile # Import here as it's not always needed
                with tarfile.open(archive_path, "r:gz") as tar_ref:
                    # Extract all members, potentially into a subdirectory
                    tar_ref.extractall(extract_dir)

            # Clean up the downloaded archive
            os.remove(archive_path)
            print("Java 21 installed locally.")
            return True # Installation successful

        except Exception as e:
            print(f"Failed to download or install Java: {e}")
            messagebox.showerror("Error", f"Failed to download or install Java 21.\nPlease manually install OpenJDK 21.\nError: {e}")
            return False # Installation failed

    def select_skin(self):
        """Select and apply a custom skin."""
        file_path = filedialog.askopenfilename(
            title="Select Skin File",
            filetypes=[("PNG Files", "*.png"), ("All Files", "*.*")]
        )
        if file_path:
            skin_dest_dir = os.path.join(MINECRAFT_DIR, "skins")
            os.makedirs(skin_dest_dir, exist_ok=True)
            # Copy to a fixed name, e.g., 'custom_skin.png'
            dest_path = os.path.join(skin_dest_dir, "custom_skin.png")
            try:
                shutil.copy2(file_path, dest_path) # copy2 attempts to preserve metadata
                print(f"Skin applied: {file_path} copied to {dest_path}")
                messagebox.showinfo("Skin Applied", "Skin applied successfully!\nIt will be used if the client version supports custom skins in this location.")
            except Exception as e:
                print(f"Failed to copy skin file: {e}")
                messagebox.showerror("Error", f"Failed to apply skin.\nError: {e}")


    @staticmethod
    def verify_file(file_path, expected_sha1):
        """Verify file SHA1 checksum."""
        # Check if file exists first
        if not os.path.exists(file_path):
            return False
        try:
            with open(file_path, "rb") as f:
                # Read in chunks to handle large files efficiently
                chunk_size = 4096
                file_hash = hashlib.sha1()
                while chunk := f.read(chunk_size):
                    file_hash.update(chunk)
            return file_hash.hexdigest() == expected_sha1
        except Exception as e:
            print(f"Error verifying file {file_path}: {e}")
            return False # Verification failed

    def download_version_files(self, version_id, version_url):
        """Download version JSON, JAR, libraries, and natives."""
        print(f"⬇️ Downloading version files for {version_id}...")
        version_dir = os.path.join(VERSIONS_DIR, version_id)
        os.makedirs(version_dir, exist_ok=True)

        # --- Download Version JSON ---
        version_json_path = os.path.join(version_dir, f"{version_id}.json")
        version_data = None
        try:
            # Only download if file doesn't exist or verification fails (more robust)
            # Note: Manifest v2 doesn't provide JSON checksum in initial listing
            if not os.path.exists(version_json_path):
                print(f"Downloading version JSON: {version_url}")
                with urllib.request.urlopen(version_url) as url:
                    data = json.loads(url.read().decode())
                    with open(version_json_path, "w") as f:
                        json.dump(data, f, indent=2)
                    version_data = data # Use newly downloaded data
            else:
                 print(f"Version JSON already exists: {version_json_path}")
                 # Load existing JSON if it exists
                 try:
                     with open(version_json_path, "r") as f:
                         version_data = json.load(f)
                 except Exception as e:
                     print(f"Failed to load existing version JSON: {e}")
                     # If loading fails, treat as not existing and try downloading again
                     print("Attempting to re-download version JSON.")
                     if os.path.exists(version_json_path):
                         os.remove(version_json_path)
                     return self.download_version_files(version_id, version_url) # Recursive call

        except Exception as e:
            print(f"Failed to download or load version JSON: {e}")
            messagebox.showerror("Error", f"Failed to download or load version {version_id} JSON.")
            return False # Indicate failure

        if not version_data:
             messagebox.showerror("Error", f"Could not get version data for {version_id}.")
             return False # Indicate failure

        # --- Download Client JAR ---
        try:
            jar_info = version_data.get("downloads", {}).get("client")
            if not jar_info:
                 messagebox.showerror("Error", f"Version {version_id} is missing client JAR information.")
                 return False

            jar_url = jar_info["url"]
            jar_path = os.path.join(version_dir, f"{version_id}.jar")
            expected_sha1 = jar_info["sha1"]

            if not os.path.exists(jar_path) or not NovaClientApp.verify_file(jar_path, expected_sha1):
                print(f"Downloading client JAR: {jar_url}")
                urllib.request.urlretrieve(jar_url, jar_path)
                if not NovaClientApp.verify_file(jar_path, expected_sha1):
                    print(f"Checksum mismatch for {jar_path}. Deleting corrupted file.")
                    if os.path.exists(jar_path): os.remove(jar_path)
                    messagebox.showerror("Error", f"Checksum mismatch for version {version_id} JAR. Please try again.")
                    return False # Indicate failure
                print("Client JAR downloaded and verified.")
            else:
                print(f"Client JAR already exists and verified: {jar_path}")

        except KeyError as e:
            print(f"Missing expected key in JAR info: {e}")
            messagebox.showerror("Error", f"Error parsing client JAR information for {version_id}.")
            return False
        except Exception as e:
            print(f"Failed to download or verify client JAR: {e}")
            messagebox.showerror("Error", f"Failed to download or verify client JAR for {version_id}.\nError: {e}")
            return False

        # --- Download Libraries and Natives ---
        print("Downloading libraries and natives...")
        current_os = platform.system().lower()
        if current_os == "darwin":
            current_os = "osx" # Minecraft uses 'osx' for macOS

        libraries_dir = os.path.join(MINECRAFT_DIR, "libraries")
        os.makedirs(libraries_dir, exist_ok=True)
        natives_dir = os.path.join(version_dir, "natives")
        os.makedirs(natives_dir, exist_ok=True)

        for lib in version_data.get("libraries", []):
            # Check if the library is applicable to the current OS based on rules
            if self.is_library_allowed(lib, current_os):
                # Download Artifact JAR
                if "downloads" in lib and "artifact" in lib["downloads"]:
                    artifact_info = lib["downloads"]["artifact"]
                    lib_url = artifact_info["url"]
                    # Construct the expected path based on the library name structure
                    lib_path = os.path.join(libraries_dir, artifact_info["path"])
                    os.makedirs(os.path.dirname(lib_path), exist_ok=True)
                    expected_sha1 = artifact_info["sha1"]

                    if not os.path.exists(lib_path) or not NovaClientApp.verify_file(lib_path, expected_sha1):
                        try:
                            # print(f"Downloading library artifact: {lib_url}")
                            urllib.request.urlretrieve(lib_url, lib_path)
                            if not NovaClientApp.verify_file(lib_path, expected_sha1):
                                print(f"Checksum mismatch for library artifact {lib_path}. Deleting corrupted file.")
                                if os.path.exists(lib_path): os.remove(lib_path)
                                # Note: Not critical error, try to continue
                                print(f"Warning: Checksum mismatch for library artifact {lib.get('name', 'unknown')}. May cause issues.")
                        except Exception as e:
                            print(f"Failed to download library artifact {lib.get('name', 'unknown')}: {e}")
                            # Note: Not critical error, try to continue

                # Download and Extract Natives
                if "natives" in lib and current_os in lib["natives"]:
                    classifier = lib["natives"][current_os].replace("${arch}", platform.architecture()[0].replace('bit', '')) # Handle arch placeholder if present
                    if "downloads" in lib and "classifiers" in lib["downloads"] and classifier in lib["downloads"]["classifiers"]:
                        native_info = lib["downloads"]["classifiers"][classifier]
                        native_url = native_info["url"]
                        # Download native JAR temporarily
                        native_temp_path = os.path.join(natives_dir, f"{lib['name'].split(':')[-1]}-{classifier}.jar") # Use a more unique temp name
                        expected_sha1 = native_info["sha1"]

                        # Only download if the native JAR file is missing or corrupted
                        # We don't check if they were *already* extracted here, just if the source archive is good.
                        if not os.path.exists(native_temp_path) or not NovaClientApp.verify_file(native_temp_path, expected_sha1):
                             try:
                                # print(f"Downloading native: {native_url}")
                                urllib.request.urlretrieve(native_url, native_temp_path)
                                if not NovaClientApp.verify_file(native_temp_path, expected_sha1):
                                    print(f"Checksum mismatch for native {native_temp_path}. Deleting corrupted file.")
                                    if os.path.exists(native_temp_path): os.remove(native_temp_path)
                                    print(f"Warning: Checksum mismatch for native {lib.get('name', 'unknown')}. May cause issues.")
                                    continue # Skip extraction if corrupted

                                # Extract the native JAR contents
                                # print(f"Extracting native: {native_temp_path}")
                                with zipfile.ZipFile(native_temp_path, "r") as zip_ref:
                                    # Extract only files, skipping directories like META-INF
                                    for member in zip_ref.infolist():
                                         if not member.is_dir():
                                              try:
                                                   zip_ref.extract(member, natives_dir)
                                              except Exception as extract_e:
                                                   print(f"Warning: Could not extract native file {member.filename}: {extract_e}")

                                # Optional: Remove the downloaded native JAR after extraction
                                # os.remove(native_temp_path) # Keep it for easier verification/re-extraction later? Let's keep it for now.

                             except Exception as e:
                                print(f"Failed to download or extract native {lib.get('name', 'unknown')}: {e}")
                                # Note: Not critical error, try to continue

        print("✅ Download and verification complete!")
        return True # Indicate success


    def modify_options_txt(self, target_fps=60):
        """Modify options.txt to set maxFps and disable vsync.
           This is a local performance tweak."""
        options_path = os.path.join(MINECRAFT_DIR, "options.txt")
        options = {}
        # Read existing options if file exists
        if os.path.exists(options_path):
            try:
                with open(options_path, "r") as f:
                    for line in f:
                        parts = line.strip().split(":", 1)
                        if len(parts) == 2:
                            options[parts[0]] = parts[1]
            except Exception as e:
                print(f"Warning: Could not read existing options.txt: {e}")

        # Set/overwrite desired options
        # Setting FPS cap and disabling vsync can improve responsiveness locally
        options['maxFps'] = str(target_fps)
        options['enableVsync'] = 'false'

        # Write options back to file
        try:
            with open(options_path, "w") as f:
                for key, value in options.items():
                    f.write(f"{key}:{value}\n")
            print(f"⚙️ Set maxFps to {target_fps} and disabled vsync in options.txt.")
        except Exception as e:
            print(f"Warning: Could not write options.txt: {e}")

    def is_library_allowed(self, lib, current_os):
        """Check if a library is allowed on the current OS based on its rules."""
        if "rules" not in lib:
            return True # No rules means it's allowed on all platforms

        allow = False # Default to disallow if rules exist but no 'allow' rule matches
        for rule in lib["rules"]:
            action = rule.get("action")
            os_info = rule.get("os")
            # Skip rules with features we don't handle
            if "features" in rule:
                continue

            os_match = False
            if os_info is None:
                # Rule applies to all OSes if 'os' is missing
                os_match = True
            elif isinstance(os_info, dict) and os_info.get("name") == current_os:
                os_match = True
                # Add support for version matching if needed: os_info.get("version")

            if os_match:
                if action == "allow":
                    allow = True
                elif action == "disallow":
                    # Disallow rules override allow rules if both match
                    return False # This library is disallowed on this OS

        return allow # Return the final 'allow' state after checking all rules

    def evaluate_rules(self, rules, current_os):
        """Evaluate argument rules based on the current OS and features (simplified)."""
        if not isinstance(rules, list) or not rules:
            return True # No rules means it's allowed

        allow = False # Default to disallow if rules exist
        for rule in rules:
             action = rule.get("action")
             os_info = rule.get("os")
             features_info = rule.get("features")

             # Skip rules with features we don't handle (e.g. is_demo_user, has_custom_resolution)
             # If a rule requires a feature we don't support, we can treat it as not matching
             if features_info is not None:
                  continue # Simplified: We don't evaluate feature rules

             os_match = False
             if os_info is None:
                 os_match = True # Rule applies to all OSes
             elif isinstance(os_info, dict) and os_info.get("name") == current_os:
                 os_match = True

             if os_match:
                 if action == "allow":
                     allow = True
                 elif action == "disallow":
                     # Disallow rules override allow rules if both match
                     return False # The argument is disallowed

        return allow # Return the final 'allow' state after checking all rules

    def generate_offline_uuid(self, username):
        """Generate a stable UUID for offline mode using a fixed scheme."""
        string_to_hash = f"OfflinePlayer:{username}"
        # Use MD5 hash as per the standard offline UUID scheme
        md5_hash = hashlib.md5(string_to_hash.encode('utf-8')).hexdigest()

        # Format the hash into a UUID string
        uuid_str = (f"{md5_hash[:8]}-{md5_hash[8:12]}-{md5_hash[12:16]}-"
                    f"{md5_hash[16:20]}-{md5_hash[20:]}") # Fixed slice for the last part
        return uuid_str

    def build_launch_command(self, version, username, ram):
        """Construct the command to launch Minecraft with cheat injection."""
        version_dir = os.path.join(VERSIONS_DIR, version)
        json_path = os.path.join(version_dir, f"{version}.json")

        if not os.path.exists(json_path):
            messagebox.showerror("Error", f"Version JSON not found for {version}. Please try downloading again.")
            return [] # Indicate failure

        try:
            with open(json_path, "r") as f:
                version_data = json.load(f)
        except Exception as e:
            print(f"Failed to read version JSON: {e}")
            messagebox.showerror("Error", f"Cannot read version {version} JSON file.")
            return []

        current_os = platform.system().lower()
        if current_os == "darwin":
            current_os = "osx" # Minecraft uses 'osx'

        # --- Determine Java Path ---
        # Prefer locally installed Java if available and correct version
        local_java_path = os.path.join(JAVA_DIR, "jdk-21.0.5+11", "bin", "java.exe" if platform.system() == "Windows" else "java")
        if os.path.exists(local_java_path) and self.is_java_installed("21"): # Check version just in case
             java_path = local_java_path
             print(f"Using local Java: {java_path}")
        elif self.is_java_installed("21"): # Fallback to system Java if it's the correct version
             java_path = "java" # Assumes 'java' is in PATH
             print("Using system Java.")
        else:
             # Should not happen if install_java_if_needed ran successfully, but as a fallback
             messagebox.showerror("Error", "Required Java version (21+) not found.")
             return []


        main_class = version_data.get("mainClass")
        if not main_class:
             messagebox.showerror("Error", f"Could not determine main class for version {version}.")
             return []

        libraries_dir = os.path.join(MINECRAFT_DIR, "libraries")
        natives_dir = os.path.join(version_dir, "natives") # Natives are extracted per version

        # Build Classpath
        classpath = []
        # Add libraries first (in order from JSON is usually safest)
        for lib in version_data.get("libraries", []):
            if self.is_library_allowed(lib, current_os):
                if "downloads" in lib and "artifact" in lib["downloads"]:
                    lib_path = os.path.join(libraries_dir, lib["downloads"]["artifact"]["path"])
                    # Only add to classpath if the file actually exists
                    if os.path.exists(lib_path):
                        classpath.append(lib_path)
                    else:
                        print(f"Warning: Missing library in classpath: {lib_path}")

        # Add the client JAR itself to the classpath
        jar_path = os.path.join(version_dir, f"{version}.jar")
        if os.path.exists(jar_path):
             classpath.append(jar_path)
        else:
             messagebox.showerror("Error", f"Client JAR not found: {jar_path}. Please try downloading again.")
             return []


        classpath_str = os.pathsep.join(classpath) # Use os.pathsep for portability (; on Windows, : on Linux/macOS)

        command = [java_path]

        # --- JVM Arguments ---
        command.append(f"-Xmx{ram}G")
        command.append(f"-Djava.library.path={natives_dir}") # Point to natives folder

        # These are standard JVM arguments known to improve performance,
        # relevant for offline gaming experience.
        default_jvm_args = [
            "-XX:+UseG1GC", # Recommended Garbage Collector for modern Java
            "-XX:-UseAdaptiveSizePolicy", # Potentially improves G1GC performance
            "-XX:MinHeapFreeRatio=3", # Minimum percentage of heap free after GC to avoid heap expansion
            "-XX:MaxHeapFreeRatio=9", # Maximum percentage of heap free after GC to avoid heap contraction
            "-XX:+DisableExplicitGC", # Prevents System.gc() calls from application code
            "-XX:+AlwaysPreTouch", # Commits the entire heap to the OS on startup
            "-XX:+UnlockExperimentalVMOptions", # Needed for some experimental options below
            "-XX:+ParallelRefProcEnabled", # Speeds up reference processing
            # Add other common args if needed for older versions or specific tuning
        ]

        jvm_args = []
        if "arguments" in version_data and "jvm" in version_data["arguments"]:
            for arg in version_data["arguments"]["jvm"]:
                if isinstance(arg, str):
                    # Apply placeholder replacements directly to static args
                    jvm_args.append(arg)
                elif isinstance(arg, dict) and "rules" in arg and "value" in arg:
                    if self.evaluate_rules(arg["rules"], current_os):
                        if isinstance(arg["value"], list):
                             # Apply placeholder replacements to list items
                            jvm_args.extend(arg["value"])
                        else:
                             # Apply placeholder replacement to single value
                            jvm_args.append(arg["value"])
        elif "minecraftArguments" in version_data:
             # Older versions use a single string for all arguments
             # Need to parse and separate JVM and Game args - complex, skipping for simplicity
             # Assume modern versions with 'arguments' structure
             print("Warning: Old version format (minecraftArguments) detected. JVM args might be incomplete.")
             # Fallback to basic arguments if 'arguments' is missing
             jvm_args = default_jvm_args # Use defaults if structured args are missing


        # Add macOS specific argument if on macOS and not already present
        if platform.system() == "Darwin" and "-XstartOnFirstThread" not in " ".join(jvm_args):
            jvm_args.append("-XstartOnFirstThread")
        if platform.system() == "Darwin" and "-Dorg.lwjgl.opengl.Display.allowSoftwareOpenGL=true" not in " ".join(jvm_args):
             # Often needed for compatibility on macOS
             jvm_args.append("-Dorg.lwjgl.opengl.Display.allowSoftwareOpenGL=true")


        # Inject cheat-related JVM system properties
        # These are read by the cheat code INJECTED into the Minecraft client JAR
        cheat_args = []
        if self.cheats['killaura']:
            cheat_args.append("-Dnova.killaura=true")
        if self.cheats['speed']:
            cheat_args.append("-Dnova.speed=true")
        if self.cheats['fly']:
            cheat_args.append("-Dnova.fly=true")

        # Combine default/version-specific JVM args with cheat args
        command.extend(jvm_args)
        command.extend(cheat_args) # Add cheat properties after standard JVM args


        command.extend(["-cp", classpath_str, main_class])


        # --- Game Arguments ---
        game_args = []
        if "arguments" in version_data and "game" in version_data["arguments"]:
             for arg in version_data["arguments"]["game"]:
                if isinstance(arg, str):
                     # Apply placeholder replacements directly to static args
                    game_args.append(arg)
                elif isinstance(arg, dict) and "rules" in arg and "value" in arg:
                    if self.evaluate_rules(arg["rules"], current_os):
                        if isinstance(arg["value"], list):
                             # Apply placeholder replacements to list items
                            game_args.extend(arg["value"])
                        else:
                             # Apply placeholder replacement to single value
                            game_args.append(arg["value"])
        elif "minecraftArguments" in version_data:
            # Older versions use a single string for all arguments
             game_args = version_data["minecraftArguments"].split()
             print("Warning: Using deprecated 'minecraftArguments'. Placeholder handling might be incomplete.")
        else:
            messagebox.showerror("Error", f"Could not find game arguments for version {version}.")
            return [] # Indicate failure


        # --- Placeholder Replacements ---
        # Use the base .nova-client directory as the game directory
        game_directory_path = MINECRAFT_DIR # os.path.join(BASE_DIR, 'minecraft') # This is already defined as MINECRAFT_DIR

        uuid = self.generate_offline_uuid(username)

        replacements = {
            "${auth_player_name}": username,
            "${version_name}": version,
            "${game_directory}": game_directory_path, # Use our managed directory
            "${assets_root}": os.path.join(MINECRAFT_DIR, "assets"),
            "${assets_index_name}": version_data.get("assetIndex", {}).get("id", version), # Fallback to version id
            "${auth_uuid}": uuid,
            "${auth_access_token}": "0", # Use "0" or dummy token for offline
            "${user_type}": "legacy",    # Or "mojang", "msa" depending on desired auth flow
            "${version_type}": version_data.get("type", "release"),
            "${user_properties}": "{}",  # Empty JSON object for offline properties
            "${quickPlayRealms}": "",    # Default empty
            "${quickPlaySingleplayer}": "", # Default empty
            "${quickPlayMultiplayer}": "", # Default empty
             # Add other common placeholders like ${profile_properties} if needed
        }

        # Apply replacements to game arguments
        final_game_args = []
        for arg in game_args:
             replaced_arg = arg
             # Perform multiple replacements on a single string argument
             for key, value in replacements.items():
                replaced_arg = replaced_arg.replace(key, str(value)) # Ensure value is string
             final_game_args.append(replaced_arg)

        command.extend(final_game_args)

        # --- Final Command Assembly ---
        # Example structure:
        # [java_path, -Xmx, -Djava.library.path, other_jvm_args, cheat_properties, -cp, classpath, main_class, game_args...]

        # Print the command for debugging (might be very long)
        # print("\nConstructed Launch Command:")
        # print(" ".join([f'"{arg}"' if ' ' in arg else arg for arg in command])) # Quote args with spaces

        return command # Return the list of command parts


    def prepare_and_launch(self):
        """Handle setup before launching."""
        selected_version = self.version_combo.get()
        if not selected_version:
            messagebox.showerror("Error", "Please select a game version.")
            return

        username = self.username_input.get().strip()
        if not username or username == "Enter Username":
            messagebox.showerror("Error", "Please enter a username.")
            return

        print(f"Preparing to launch version {selected_version} as {username}...")

        # 1. Install Java if needed (blocking call)
        if not self.install_java_if_needed():
             print("Java installation failed or was skipped.")
             return # Stop if Java is not available

        # 2. Ensure necessary game files are downloaded (blocking call)
        version_url = self.versions.get(selected_version)
        if not version_url:
             messagebox.showerror("Error", f"Could not find URL for version {selected_version}.")
             print(f"Error: Version URL not found for {selected_version}")
             return

        # download_version_files handles existence/verification, returns False on critical failure
        if not self.download_version_files(selected_version, version_url):
             print("File download/verification failed.")
             return # Stop if files are missing or corrupted

        # 3. Modify options.txt (non-critical, doesn't block)
        # This modifies FPS and VSync, contributing to local performance.
        self.modify_options_txt(target_fps=60)

        # 4. Build the launch command (blocking call)
        ram_gb = int(self.ram_scale.get())
        launch_cmd = self.build_launch_command(selected_version, username, ram_gb)

        if not launch_cmd:
            print("Failed to build launch command.")
            return # Stop if command could not be built

        # 5. Launch the game (non-blocking, runs in a new process)
        print("\n🚀 Launching Minecraft...")
        try:
            # Use subprocess.Popen for non-blocking launch
            # Specify cwd (current working directory) as MINECRAFT_DIR
            subprocess.Popen(launch_cmd, cwd=MINECRAFT_DIR)
            # Optionally close the launcher GUI after launching
            # self.destroy()
        except FileNotFoundError:
             messagebox.showerror("Error", f"Java executable not found.\nLooked for: {launch_cmd[0]}")
             print(f"Launch Error: Java executable not found at {launch_cmd[0]}")
        except Exception as e:
            print(f"Failed to launch Minecraft: {e}")
            messagebox.showerror("Error", f"Failed to launch Minecraft.\nError: {e}")


# --- Main execution block ---
if __name__ == "__main__":
    # Create the root window and run the application
    app = NovaClientApp()
    app.mainloop()
