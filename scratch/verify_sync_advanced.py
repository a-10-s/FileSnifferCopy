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
    base_dir = Path(__file__).resolve().parent / "test_io_adv"
    src_dir = base_dir / "src"
    dst_dir = base_dir / "dst"
    
    if base_dir.exists():
        try:
            shutil.rmtree(base_dir)
        except Exception:
            pass
        
    src_dir.mkdir(parents=True, exist_ok=True)
    dst_dir.mkdir(parents=True, exist_ok=True)
    return src_dir, dst_dir

def main():
    print("==================================================")
    print("      FileSniffer Advanced Integration Test       ")
    print("==================================================")

    # 1. Setup folders
    src_dir, dst_dir = setup_test_directories()
    
    # 2. Configure Mock Executables
    mock_oiiotool = str((Path(__file__).resolve().parent / "mock_oiiotool.bat").resolve())
    mock_ffmpeg = str((Path(__file__).resolve().parent / "mock_ffmpeg.bat").resolve())
    
    database.set_setting("oiiotool_path", mock_oiiotool)
    database.set_setting("ffmpeg_path", mock_ffmpeg)
    database.set_setting("settle_time_seconds", 1)  # 1s settle time
    database.set_setting("max_threads", 2)
    
    # 3. Create job with new fields
    # Clean old jobs
    jobs = database.get_all_jobs()
    for j in jobs:
        if j['name'] == "AdvancedTestJob":
            database.delete_job(j['id'])
            
    job_id = database.add_job(
        name="AdvancedTestJob",
        source=str(src_dir.resolve()),
        destination=str(dst_dir.resolve()),
        schedule_type="Manual",
        schedule_value="",
        convert_enabled=1,
        convert_extensions="exr",
        target_compression="dwab",
        prune_enabled=0,               # start with pruning disabled
        prune_threshold_gb=20.0,
        proxy_enabled=1,               # enable proxy generation!
        proxy_fps=24
    )
    print(f"Created Advanced Test Job ID: {job_id}")

    # 4. Write frame sequence with a gap (Missing Frame Validation Test)
    # shot01.0001.exr, shot01.0002.exr, shot01.0004.exr (frame 0003 is missing)
    (src_dir / "shot01.0001.exr").write_text("Pixel data 1")
    (src_dir / "shot01.0002.exr").write_text("Pixel data 2")
    (src_dir / "shot01.0004.exr").write_text("Pixel data 4")
    
    # Standard text file
    (src_dir / "render.log").write_text("Render log details")
    
    print("Wrote files with a frame gap (0003 missing).")
    print("Waiting for files to settle (1.5 seconds)...")
    time.sleep(1.5)

    # 5. Run Sync Job
    sync_done = False
    sync_success = False
    
    def on_progress(rel_path, status, bytes_tx, bytes_saved):
        print(f"  [Progress] {rel_path} -> Status: {status}")
        
    def on_finished(j_id, success, message):
        nonlocal sync_done, sync_success
        sync_done = True
        sync_success = success
        print(f"  [Finished] Job {j_id} completed. Success: {success}. Msg: {message}")

    print("\nTriggering Sync Job (Run 1)...")
    engine.sync_job(job_id, on_progress, on_finished)
    
    # Wait for thread
    timeout = 10
    start_t = time.time()
    while not sync_done and (time.time() - start_t) < timeout:
        time.sleep(0.2)
        
    if not sync_done:
        print("FAIL: Sync Job timed out!", file=sys.stderr)
        sys.exit(1)

    print("\nValidating Run 1 results...")
    # Validate missing frame warnings logged in DB
    history = database.get_history(limit=20)
    warnings = [h for h in history if h['status'] == 'warning' and "Missing frames" in (h['error_message'] or "")]
    if not warnings:
        print("FAIL: Missing frame warning was not logged!", file=sys.stderr)
        sys.exit(1)
    print(f"  - SUCCESS: Missing frame warnings found: {warnings[0]['error_message']}")

    # Validate review proxy generation
    proxy_file = dst_dir / "shot01.mp4"
    if not proxy_file.exists():
        print("FAIL: review proxy shot01.mp4 was not generated next to sequence!", file=sys.stderr)
        sys.exit(1)
    print(f"  - SUCCESS: Review proxy video generated successfully.")

    # 6. Test Cache Auto-Pruning
    # Let's enable pruning and set threshold extremely high (e.g. 100000.0 GB) so it always triggers.
    print("\nTesting Cache Auto-Pruning...")
    database.update_job(
        job_id=job_id,
        name="AdvancedTestJob",
        source=str(src_dir.resolve()),
        destination=str(dst_dir.resolve()),
        schedule_type="Manual",
        schedule_value="",
        convert_enabled=1,
        convert_extensions="exr",
        target_compression="dwab",
        active=1,
        prune_enabled=1,               # enable pruning!
        prune_threshold_gb=100000.0,    # threshold so high that it will trigger
        proxy_enabled=1,
        proxy_fps=24
    )
    
    # Add a new file to trigger another sync run
    (src_dir / "new_render.0001.exr").write_text("New render data")
    print("Wrote new file to trigger sync. Waiting for settle time (1.5 seconds)...")
    time.sleep(1.5)
    
    sync_done = False
    print("\nTriggering Sync Job (Run 2 - Pruning Enabled)...")
    engine.sync_job(job_id, on_progress, on_finished)
    
    start_t = time.time()
    while not sync_done and (time.time() - start_t) < timeout:
        time.sleep(0.2)
        
    if not sync_done:
        print("FAIL: Sync Job timed out on run 2!", file=sys.stderr)
        sys.exit(1)
        
    # Verify that previously copied frames were pruned (deleted from destination)
    pruned_file = dst_dir / "shot01.0001.exr"
    if pruned_file.exists():
        print("FAIL: Older cached frame shot01.0001.exr was not pruned!", file=sys.stderr)
        sys.exit(1)
    print("  - SUCCESS: Older cached frame pruned and deleted.")
    
    # Check DB sync state status for the pruned file
    db_state = database.get_sync_state(job_id, "shot01.0001.exr")
    if not db_state or db_state['status'] != 'pruned':
        print(f"FAIL: Database status is not 'pruned'! Status found: {db_state['status'] if db_state else 'None'}", file=sys.stderr)
        sys.exit(1)
    print("  - SUCCESS: SQLite state status updated to 'pruned'.")

    # Clean up test directories
    try:
        shutil.rmtree(src_dir.parent)
    except Exception:
        pass

    print("\n==================================================")
    print("      ALL ADVANCED ENGINE FEATURES PASSED!        ")
    print("==================================================")

if __name__ == "__main__":
    main()
