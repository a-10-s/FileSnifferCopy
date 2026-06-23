# FileSniffer

FileSniffer is a specialized, LAN-focused Windows desktop background utility designed for VFX, Animation, and content generation studios. It automates folder synchronization and on-the-fly multi-channel EXR compression conversion (e.g., to DWAB) to optimize local and shared storage spaces while supporting raw color review pipelines.

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
* **On-the-Fly EXR Transcoding:** Optional format-preserving conversion (EXR to EXR) modifying only the compression (e.g., ZIP/PIZ to DWAB) while keeping all AOVs, custom channels (Cryptomatte, Depth, Utility), and metadata untouched.
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
├── transcoder.py          # Subprocess wrapper for oiiotool (OpenImageIO)
├── main.py                # Main PySide6 entry point & tray manager
│
├── ui/                    # User interface components
│   ├── styles.py          # Centralized dark QSS stylesheet
│   ├── dashboard.py       # Control panel window, job cards, sync status
│   ├── job_modal.py       # Sync Job config (Paths, Schedule, Transcoding, Proxy FPS options)
│   ├── settings_modal.py  # Global settings config (oiiotool pathway, threads, tick rate)
│   ├── log_window.py      # Detailed transfer logs and storage savings dashboard
│   ├── analysis_window.py # Interactive Overwrite Analysis Dialog
│   └── progress_window.py # Modeless real-time progress monitor & speed gauge
│
├── scratch/               # Testing and simulation suite
│   ├── mock_oiiotool.py   # Command-line oiiotool simulator
│   ├── mock_oiiotool.bat  # Batch wrapper for oiiotool simulation
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
Execute the verification suite to validate directory scanning, settle times, EXR compression conversion, sync modes, and proxy generation:
```bash
# Core sync/lock/transcode checks
python scratch/verify_sync.py

# Missing frame, auto-pruning, and proxy rendering validations
python scratch/verify_sync_advanced.py

# Sync mode comparison and raw proxy framerate checks
python scratch/verify_sync_modes.py
```

---

## ⚙️ Technical Details

* **OpenImageIO:** FileSniffer relies on `oiiotool` (part of the OpenImageIO suite) to transcode OpenEXR frame sequences. You can configure the path to your studio's `oiiotool.exe` binary in the application's **Settings** panel.
* **File Locking:** A file is deemed "settled" only if its modification time (`mtime`) is older than the configured settle-time threshold (default: 60 seconds) AND the file can be opened exclusively for writing.
* **SQLite Cache & Log:** Sync history, savings, and job logs are written locally in a transactions database, ensuring data persistence and uninterrupted studio pipeline reporting.
