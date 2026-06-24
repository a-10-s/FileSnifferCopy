# FileSniffer

FileSniffer is a specialized, LAN-focused Windows desktop background utility designed for VFX, Animation, and content generation studios. It automates folder synchronization to optimize local and shared storage spaces while supporting raw color review pipelines.

---

## 🚀 Key Features

* **Advanced Sync Modes:**
  * **Mirror Folder:** Bruteforce mirror sync that forces updates without confirmation prompts—ideal for automated cron jobs.
  * **Target Update:** Compares source and destination, and generates a detailed comparison report highlighting newer or changed files.
* **Interactive Overwrite Analysis Dialog:** Provides a visual comparison of file sizes, modifications, and conflict states, allowing granular file selection prior to running updates.
* **Modeless Multi-Window Progress Monitoring:** Track multiple running sync jobs concurrently. Double-clicking or clicking details opens a modeless window that won't block the rest of the interface, bringing existing monitors to the front if already open.
* **Real-Time Network Speed Gauge:** Displays EMA-smoothed aggregate transfer speed inside the progress monitor, plus live rolling copy speeds (e.g., `⚡ 42.50 MB/s`) directly on each job card.
* **Settle Time File-Lock Check:** Prevents copying files that are still actively being written by render nodes (like Arnold, Karma, or VRay) or artists.
* **Flexible Review Proxies:** Optional automated review proxy generation with customizable frame rates (FPS) and support for raw scale conversions (preserves original color spaces without baked-in sRGB gamma correction).
* **Windows System Tray Resident:** Closes to the system tray, running silently in the background. Double-click the tray icon to restore the control panel.
* **Visual Styling & Tooltips:** High-contrast, studio-friendly dark interface featuring highly readable custom tooltips and responsive explore folder shortcuts.

---

## 📁 Project Structure

```text
FileSniffer/
│
├── config.py              # Application globals, AppData resolving
├── database.py            # SQLite schema, settings, jobs configuration, transfer history
├── engine.py              # Directory scanner, file locking, concurrent thread-pool executor
├── transcoder.py          # Subprocess wrapper for FFmpeg
├── main.py                # Main PySide6 entry point & tray manager
│
├── ui/                    # User interface components
│   ├── styles.py          # Centralized dark QSS stylesheet
│   ├── dashboard.py       # Control panel window, job cards, sync status
│   ├── job_modal.py       # Sync Job config (Paths, Schedule, Proxy FPS options)
│   ├── settings_modal.py  # Global settings config (FFmpeg pathway, threads, tick rate)
│   ├── log_window.py      # Detailed transfer logs and storage savings dashboard
│   ├── analysis_window.py # Interactive Overwrite Analysis Dialog
│   └── progress_window.py # Modeless real-time progress monitor & speed gauge
│
├── scratch/               # Testing and simulation suite
│   ├── mock_ffmpeg.py     # Command-line ffmpeg simulator
│   ├── mock_ffmpeg.bat    # Batch wrapper for ffmpeg simulation
│   ├── verify_sync.py     # Core integration test runner
│   ├── verify_sync_advanced.py  # Advanced pipeline features verification
│   └── verify_sync_modes.py     # Sync modes and raw proxy output validation
│
├── DESIGN.md              # Design system tokens and specifications
└── requirements.txt       # Python dependencies
```

---

## 🛠️ Getting Started

### 1. Installation
Install the required dependencies (such as PySide6) in your virtual environment:
```bash
pip install -r requirements.txt
```

### 2. Launch the Application
Run the main script using your virtual environment's Python interpreter to launch the PySide6 dashboard:
```bash
python main.py
```

### 3. Running Verification Tests
Execute the verification suite to validate directory scanning, settle times, sync modes, and proxy generation:
```bash
# Core sync/lock checks
python scratch/verify_sync.py

# Missing frame, auto-pruning, and proxy rendering validations
python scratch/verify_sync_advanced.py

# Sync mode comparison and raw proxy framerate checks
python scratch/verify_sync_modes.py
```

---

## ⚙️ Global Configuration Settings

Click the **Settings** button in the top right corner of the dashboard to configure global engine parameters:

1. **Path to ffmpeg.exe:** The absolute path to your system's `ffmpeg` executable. This is required if you enable **Automated Review Proxies** on any job. Click the **Test Binary** button to verify that the path is valid and the executable starts correctly.
2. **File Settle Time (sec):** The wait time (default: `60` seconds) since a file's last modified timestamp before it is synced. This checks the file size and modification time, ensuring that the file is completely written and closed by the operating system (or render nodes like Arnold, Karma, or VRay) before the engine attempts to copy it, preventing corrupted or half-written transfers.
3. **Max Worker Threads:** The concurrency thread pool level (default: `4`). It defines how many files the engine copies or processes in parallel. Higher values (e.g. `8` or `16`) speed up large transfers of small files on fast local SSDs or 10Gb lines, while lower values (e.g. `2` or `3`) prevent slower mechanical drives or limited network lines from choking under disk queue overhead.
4. **Folder Scan Tick (sec):** The background polling interval (default: `30` seconds) at which the scheduler wakes up to scan source folders and run scheduled jobs. Keep it low for near-real-time updates, or increase it (e.g., `300` seconds / 5 minutes) to reduce CPU and network scanning overhead on slow servers or network-attached storage (NAS).

---

## 📅 Configuring & Using Cron Sync Jobs

Click the **New Cron Job** button on the dashboard to configure folder tasks.

### 1. Basic Fields
* **Job Identifier Name:** The descriptive name for the sync job (e.g. `Sequence_A_Sync`).
* **Source Watch Folder:** The directory where files are written (supports local, external, or LAN network paths).
* **Destination Output Folder:** The target folder where files will be copied.

### 2. Sync Copy Mode
* **Mirror Folder (Brute Force):** Copies everything from source to destination without prompts or manual confirmation. Best for fully automated schedules.
* **Target Update (Analyze & Confirm):** Scans directories and provides a detailed comparison showing new, modified, or conflicting files. You select which files are allowed to overwrite before proceeding.

### 3. Scheduling Types
* **Manual:** No automatic trigger. The job only runs when you click the **Run Now** button on the card.
* **Interval (Min):** Runs periodically every *N* minutes.
* **Daily:** Runs once every day at a specific `HH:MM` time (e.g., `18:30` for a daily backup at 6:30 PM).

### 4. Advanced Card Settings
* **Cache Auto-Pruning:** Specify the minimum free disk space on the destination drive (in GB). If space drops below this threshold, the sync engine deletes the oldest synced files in the target directory to free up space.
* **Automated Proxy Generation:** Generates a compressed MP4 review proxy movie from image sequences upon successful transfer. You can specify a custom framerate (FPS) for playback.

---

## 📦 Building Platform Installers & Standalone Binaries

If you want to package FileSniffer into a standalone executable or application bundle to distribute to artist workstations without requiring a Python installation:

> [!NOTE]
> These commands generate a standalone **executable executable binary** (`.exe` on Windows, `.app` on macOS). If you need an **installer wizard** (e.g., a `.msi` or Setup `.exe` on Windows), you can package the generated executable using tools like **Inno Setup**, **NSIS**, or **Wix Toolset**.

### Windows Build (Standalone Executable)

1. Make sure PyInstaller and Pillow are installed in your environment:
   ```bash
   pip install pyinstaller pillow
   ```
2. Generate the native `.ico` file from the SVG asset if it's missing or changed:
   ```bash
   python scratch/generate_ico.py
   ```
3. Run the compiler using the configured spec file (Recommended):
   ```bash
   pyinstaller FileSniffer.spec
   ```
   Or if building manually via the command line from scratch:
   ```bash
   pyinstaller --noconsole --onefile --name="FileSniffer" --icon="ui/resources/logo.ico" --add-data="ui/resources/logo.svg;ui/resources" main.py
   ```
4. The executable file will be built inside the `dist/` directory as `FileSniffer.exe`.

> [!TIP]
> If your default terminal `python` command points to a system-wide Python that lacks `PySide6` or `Pillow`, run the script and compiler using the project's virtual environment path:
> ```bash
> .\venv\Scripts\python.exe scratch/generate_ico.py
> .\venv\Scripts\pyinstaller FileSniffer.spec
> ```


### macOS Build (App Bundle)

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```
2. Run the compiler using colon-separated paths for resource bundle packaging:
   ```bash
   pyinstaller --noconsole --onefile --windowed --name="FileSniffer" --icon="ui/resources/logo.svg" --add-data="ui/resources/logo.svg:ui/resources" main.py
   ```
3. The app bundle will be generated under `dist/FileSniffer.app`.

*Note: Ensure that the `ffmpeg` binary is available on the target system's environment `PATH`, or set its absolute location in the application's global **Settings** panel.*
