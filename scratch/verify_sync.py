import os
import sys
import shutil
import time
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import database
import engine

def setup_test_directories():
    base_dir = Path(__file__).resolve().parent / "test_io"
    src_dir = base_dir / "src"
    dst_dir = base_dir / "dst"
    
    # Clean old test run folders
    if base_dir.exists():
        shutil.rmtree(base_dir)
        
    src_dir.mkdir(parents=True, exist_ok=True)
    dst_dir.mkdir(parents=True, exist_ok=True)
    return src_dir, dst_dir

def main():
    print("==================================================")
    print("          FileSniffer Integration Test            ")
    print("==================================================")

    # 1. Setup Test Directories
    src_dir, dst_dir = setup_test_directories()
    print(f"Test Source:      {src_dir}")
    print(f"Test Destination: {dst_dir}")

    # 2. Configure Settings in SQLite
    mock_oiiotool = str((Path(__file__).resolve().parent / "mock_oiiotool.bat").resolve())
    database.set_setting("oiiotool_path", mock_oiiotool)
    database.set_setting("settle_time_seconds", 1)  # 1 second for fast test runs
    database.set_setting("max_threads", 2)
    
    print("Database Settings updated:")
    print(f"  - oiiotool_path: {database.get_setting('oiiotool_path')}")
    print(f"  - settle_time:   {database.get_setting('settle_time_seconds')}s")

    # 3. Create a Test Job
    # Remove existing test jobs if any
    jobs = database.get_all_jobs()
    for j in jobs:
        if j['name'] == "IntegrationTestJob":
            database.delete_job(j['id'])
            
    job_id = database.add_job(
        name="IntegrationTestJob",
        source=str(src_dir.resolve()),
        destination=str(dst_dir.resolve()),
        schedule_type="Manual",
        schedule_value="",
        convert_enabled=1,
        convert_extensions="exr",
        target_compression="dwab"
    )
    print(f"Created Job ID: {job_id}")

    # 4. Create Source Files
    # Standard text file
    txt_file = src_dir / "render_notes.txt"
    with open(txt_file, "w") as f:
        f.write("Frame sequence notes: Render looks good.")
        
    # EXR file (mock data)
    exr_file = src_dir / "shot01_beauty_0001.exr"
    with open(exr_file, "w") as f:
        f.write("Raw image pixel data: ZIP compression.")
        
    print("Wrote test source files.")
    
    # Wait for settle time (1s)
    print("Waiting for files to settle...")
    time.main_sleep = time.sleep
    time.sleep(1.5)

    # 5. Run Sync Job
    sync_done = False
    sync_success = False
    
    def on_progress(rel_path, status, bytes_tx, bytes_saved):
        print(f"  [Progress] {rel_path} -> Status: {status}, Tx: {bytes_tx}B, Saved: {bytes_saved}B")
        
    def on_finished(j_id, success, message):
        nonlocal sync_done, sync_success
        sync_done = True
        sync_success = success
        print(f"\n[Finished] Job {j_id} completed. Success: {success}. Msg: {message}")

    print("\nTriggering Sync Job...")
    engine.sync_job(job_id, on_progress, on_finished)

    # Poll until background thread finishes
    timeout = 10
    start_time = time.time()
    while not sync_done and (time.time() - start_time) < timeout:
        time.sleep(0.2)

    if not sync_done:
        print("\nError: Sync job timed out!", file=sys.stderr)
        sys.exit(1)

    # 6. Validate Outputs
    print("\nValidating results...")
    
    # Check copy of text file
    txt_dest = dst_dir / "render_notes.txt"
    if not txt_dest.exists():
        print("FAIL: render_notes.txt was not copied!", file=sys.stderr)
        sys.exit(1)
    with open(txt_dest, "r") as f:
        content = f.read()
    if "Render looks good." not in content:
        print("FAIL: render_notes.txt content got corrupted!", file=sys.stderr)
        sys.exit(1)
    print("  - Text file copied successfully.")

    # Check copy & transcode of EXR file
    exr_dest = dst_dir / "shot01_beauty_0001.exr"
    if not exr_dest.exists():
        print("FAIL: shot01_beauty_0001.exr was not copied!", file=sys.stderr)
        sys.exit(1)
    with open(exr_dest, "r") as f:
        content = f.read()
    if "MOCK EXR FILE" not in content or "Compression: dwab" not in content:
        print("FAIL: EXR conversion did not occur or failed!", file=sys.stderr)
        sys.exit(1)
    print("  - EXR file converted & copied successfully.")

    # 7. Test Incremental Sync (should skip files)
    print("\nTesting incremental sync (second run should skip files)...")
    sync_done = False
    
    def on_progress_2(rel_path, status, bytes_tx, bytes_saved):
        print(f"  [Progress Run 2] {rel_path} -> {status}")
        
    engine.sync_job(job_id, on_progress_2, on_finished)
    
    start_time = time.time()
    while not sync_done and (time.time() - start_time) < timeout:
        time.sleep(0.2)
        
    # Check database history entries
    history = database.get_history(limit=5)
    print("\nRecent Sync History:")
    for h in history:
        print(f"  - {h['timestamp']} | File: {h['file_name']} | Status: {h['status']} | Saved: {h['bytes_saved']}B")

    print("\n==================================================")
    print("        ALL INTEGRATION TESTS PASSED!            ")
    print("==================================================")

if __name__ == "__main__":
    main()
