import os
import shutil
import time
from datetime import datetime
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import subprocess

import database

def collapse_ranges(lst):
    if not lst:
        return ""
    lst = sorted(list(set(lst)))
    ranges = []
    start = lst[0]
    end = lst[0]
    for val in lst[1:]:
        if val == end + 1:
            end = val
        else:
            if start == end:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{end}")
            start = val
            end = val
    if start == end:
        ranges.append(str(start))
    else:
        ranges.append(f"{start}-{end}")
    return ", ".join(ranges)

def validate_missing_frames(job_id, source_dir):
    """
    Scans the source directory recursively, groups files by sequence prefixes,
    checks for missing frames, and logs warning flags to database sync history.
    """
    # Match pattern: base_name.0001.ext or base_name_0001.ext
    seq_pattern = re.compile(r"^(.*?)(?:\.|_)(?P<frame>\d+)\.(?P<ext>[a-zA-Z0-9]+)$")
    
    # Traverse source folder and group sequences
    # Key: (dir_path, base_name, ext) -> list of frame numbers (ints)
    sequences = {}
    
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            m = seq_pattern.match(file)
            if m:
                base = m.group(1)
                frame_str = m.group("frame")
                ext = m.group("ext").lower()
                
                # Exclude temporary/lock files
                if ext in ("tmp", "tmp_transcode", "tmp_copy"):
                    continue
                    
                key = (root, base, ext)
                if key not in sequences:
                    sequences[key] = []
                sequences[key].append(int(frame_str))
                
    # Check each sequence for gaps
    for (dir_path, base, ext), frames in sequences.items():
        if len(frames) < 2:
            continue # Skip single files (not a sequence)
            
        frames = sorted(list(set(frames)))
        min_f = frames[0]
        max_f = frames[-1]
        
        expected = set(range(min_f, max_f + 1))
        actual = set(frames)
        missing = expected - actual
        
        if missing:
            gaps_str = collapse_ranges(list(missing))
            try:
                rel_dir = Path(dir_path).relative_to(source_dir).as_posix()
            except ValueError:
                rel_dir = "."
            display_name = f"{rel_dir}/{base}.####.{ext}" if rel_dir != "." else f"{base}.####.{ext}"
            # Log warnings to DB
            database.add_history_entry(
                job_id=job_id,
                file_name=display_name,
                status='warning',
                bytes_transferred=0,
                bytes_saved=0,
                error_message=f"Missing frames: {gaps_str}"
            )

def prune_destination_cache(job):
    """
    Pre-sync check: monitors target disk space. If space is below a threshold,
    deletes the oldest synced frames (checking SQLite history logs) and sets
    their database status to 'pruned' to avoid redundant recopying.
    """
    if not job.get('prune_enabled'):
        return
        
    threshold_gb = job.get('prune_threshold_gb', 20.0)
    dest_path = job['destination']
    
    if not os.path.exists(dest_path):
        return
        
    # Check free space
    try:
        total, used, free = shutil.disk_usage(dest_path)
        free_gb = free / (1024**3)
    except Exception:
        return
        
    if free_gb >= threshold_gb:
        return
        
    # We are low on space! Let's delete oldest synced files
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, relative_path, file_size 
        FROM sync_state 
        WHERE job_id = ? AND status = 'synced' 
        ORDER BY last_sync ASC
    """, (job['id'],))
    synced_files = [dict(r) for r in cursor.fetchall()]
    
    deleted_count = 0
    space_freed = 0
    
    for f in synced_files:
        file_to_del = Path(dest_path) / f['relative_path']
        if file_to_del.exists():
            try:
                # Delete the file
                file_size = file_to_del.stat().st_size
                file_to_del.unlink()
                deleted_count += 1
                space_freed += file_size
                
                # Delete empty parent folders up to destination
                parent = file_to_del.parent
                while parent != Path(dest_path):
                    if not any(parent.iterdir()):
                        parent.rmdir()
                        parent = parent.parent
                    else:
                        break
            except Exception:
                pass
                
        # Set state to 'pruned' in database
        cursor.execute("UPDATE sync_state SET status = 'pruned' WHERE id = ?", (f['id'],))
        conn.commit()
        
        # Check space again
        try:
            total, used, free = shutil.disk_usage(dest_path)
            free_gb = free / (1024**3)
        except Exception:
            break
            
        if free_gb >= threshold_gb:
            break
            
    conn.close()
    
    if deleted_count > 0:
        freed_mb = space_freed / (1024**2)
        # Log prune run to database history log
        database.add_history_entry(
            job_id=job['id'],
            file_name=f"Cache Pruner ({deleted_count} files)",
            status='warning',
            bytes_transferred=0,
            bytes_saved=0,
            error_message=f"Low disk space. Deleted {deleted_count} cached files to free {freed_mb:.1f} MB."
        )

def generate_mp4_proxies(job):
    """
    Post-sync process: scan destination folder for EXR sequences, and compile
    them into a lightweight review .mp4 next to the sequence.
    """
    if not job.get('proxy_enabled'):
        return
        
    ffmpeg_path = database.get_setting("ffmpeg_path", "ffmpeg")
    dest_dir = job['destination']
    if not os.path.exists(dest_dir):
        return
        
    # Match pattern: base_name.0001.exr or base_name_0001.exr
    seq_pattern = re.compile(r"^(.*?)(?:\.|_)(?P<frame>\d+)\.(?P<ext>exr)$", re.IGNORECASE)
    
    sequences = {}
    
    # Traverse destination folder and group EXR sequences
    for root, dirs, files in os.walk(dest_dir):
        for file in files:
            m = seq_pattern.match(file)
            if m:
                base = m.group(1)
                frame_str = m.group("frame")
                ext = m.group("ext").lower()
                
                key = (root, base)
                if key not in sequences:
                    sequences[key] = {
                        'frames': [],
                        'padding': len(frame_str),
                        'separator': '_' if '_' in file else '.'
                    }
                sequences[key]['frames'].append(int(frame_str))
                
    # Run FFmpeg for each sequence
    for (dir_path, base), info in sequences.items():
        frames = sorted(list(set(info['frames'])))
        if len(frames) < 2:
            continue
            
        min_frame = frames[0]
        padding = info['padding']
        sep = info['separator']
        
        # FFmpeg input pattern: e.g. base.%04d.exr
        input_pattern = f"{base}{sep}%0{padding}d.exr"
        input_path = Path(dir_path) / input_pattern
        output_mp4 = Path(dir_path) / f"{base}.mp4"
        
        # Construct FFmpeg command
        # scale=trunc(iw/2)*2... forces even dimensions required by libx264
        cmd = [
            ffmpeg_path,
            "-y",
            "-framerate", str(job.get('proxy_fps', 24) or 24),
            "-start_number", str(min_frame),
            "-i", str(input_path),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
            str(output_mp4)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            if result.returncode == 0:
                database.add_history_entry(
                    job_id=job['id'],
                    file_name=f"{base}.mp4",
                    status='success',
                    bytes_transferred=0,
                    bytes_saved=0,
                    error_message="MP4 review proxy generated successfully next to sequence."
                )
            else:
                # Log failure
                database.add_history_entry(
                    job_id=job['id'],
                    file_name=f"{base}.mp4",
                    status='failed',
                    bytes_transferred=0,
                    bytes_saved=0,
                    error_message=f"FFmpeg proxy compilation failed: {result.stderr or result.stdout}"
                )
        except Exception as e:
            database.add_history_entry(
                job_id=job['id'],
                file_name=f"{base}.mp4",
                status='failed',
                bytes_transferred=0,
                bytes_saved=0,
                error_message=f"Could not run FFmpeg: {str(e)}"
            )


# A lock to prevent multiple concurrent sync runs on the same job
_job_locks = {}
_job_locks_lock = threading.Lock()

def get_job_lock(job_id):
    with _job_locks_lock:
        if job_id not in _job_locks:
            _job_locks[job_id] = threading.Lock()
        return _job_locks[job_id]

# Keep track of active jobs currently running
active_syncs = {}
active_syncs_lock = threading.Lock()

def is_file_settled(file_path: Path, settle_time_seconds: int) -> bool:
    """
    Check if a file is settled and not locked.
    1. Compares current time with mtime.
    2. Attempts to open the file exclusively to ensure no other process (like a renderer) is writing to it.
    """
    try:
        if not file_path.exists():
            return False
            
        stat = file_path.stat()
        mtime = stat.st_mtime
        current_time = time.time()
        
        # 1. Settle time check
        if (current_time - mtime) < settle_time_seconds:
            return False
            
        # 2. File lock check (try opening in append/write mode)
        # On Windows, if a file is open by a renderer for writing, this will raise a PermissionError.
        try:
            with open(file_path, 'ab') as f:
                pass
        except (IOError, PermissionError):
            return False
            
        return True
    except Exception:
        return False

def scan_job_files(job):
    """
    Scan source directory, compare with DB sync state, and find files that need syncing.
    Returns:
        List of dicts: [{'relative_path': ..., 'abs_src': ..., 'abs_dst': ..., 'size': ..., 'mtime': ...}]
    """
    job_id = job['id']
    source_dir = Path(job['source'])
    dest_dir = Path(job['destination'])
    
    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory '{source_dir}' does not exist.")
        
    pending_files = []
    
    # Recursively traverse source directory
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            abs_src = Path(root) / file
            # Get path relative to the source directory
            try:
                rel_path = abs_src.relative_to(source_dir).as_posix()
            except ValueError:
                continue
                
            abs_dst = dest_dir / rel_path
            
            try:
                stat = abs_src.stat()
                file_size = stat.st_size
                mtime = stat.st_mtime
            except Exception:
                # File might have been deleted or inaccessible
                continue
                
            # Check DB state
            db_state = database.get_sync_state(job_id, rel_path)
            
            needs_sync = False
            if not db_state:
                needs_sync = True
            else:
                # If size changed or modification time is newer in source
                # Allow a small float threshold for mtime comparisons
                if db_state['file_size'] != file_size or abs(db_state['mtime'] - mtime) > 0.1 or db_state['status'] == 'failed':
                    needs_sync = True
                    
            if needs_sync:
                target_exists = abs_dst.exists()
                target_size = 0
                target_mtime = 0.0
                conflict_type = 'new'
                
                if target_exists:
                    try:
                        dst_stat = abs_dst.stat()
                        target_size = dst_stat.st_size
                        target_mtime = dst_stat.st_mtime
                        if file_size != target_size:
                            conflict_type = 'overwrite_size'
                        elif mtime > target_mtime + 0.1:
                            conflict_type = 'overwrite_newer'
                        else:
                            conflict_type = 'overwrite_forced'
                    except Exception:
                        target_exists = False

                pending_files.append({
                    'relative_path': rel_path,
                    'abs_src': abs_src,
                    'abs_dst': abs_dst,
                    'size': file_size,
                    'mtime': mtime,
                    'target_exists': target_exists,
                    'target_size': target_size,
                    'target_mtime': target_mtime,
                    'conflict_type': conflict_type
                })
                
    return pending_files

def process_file_sync(job, file_info, settle_time, oiiotool_path, progress_callback=None):
    """
    Process single file: settle check, transcode if needed, or copy directly.
    """
    job_id = job['id']
    rel_path = file_info['relative_path']
    abs_src = file_info['abs_src']
    abs_dst = file_info['abs_dst']
    file_size = file_info['size']
    mtime = file_info['mtime']
    
    # Update state to 'Copying'
    with active_syncs_lock:
        if job_id in active_syncs:
            active_syncs[job_id]['file_transfers'][rel_path] = {
                'relative_path': rel_path,
                'size': file_size,
                'status': 'Copying',
                'speed': 0.0,
                'duration': 0.0,
                'error': None
            }
            
    t_start = time.time()
    
    # 1. Ensure file is settled
    if not is_file_settled(abs_src, settle_time):
        with active_syncs_lock:
            if job_id in active_syncs and rel_path in active_syncs[job_id]['file_transfers']:
                active_syncs[job_id]['file_transfers'][rel_path]['status'] = 'Skipped'
                active_syncs[job_id]['file_transfers'][rel_path]['error'] = 'File not settled / locked'
        return {'status': 'skipped', 'reason': 'File not settled / locked'}
        
    # Ensure destination subfolders exist
    abs_dst.parent.mkdir(parents=True, exist_ok=True)
    
    bytes_transferred = file_size
    bytes_saved = 0
    success = False
    err_msg = None
    
    try:
        # Direct binary copy (with temp file swap for safety)
        temp_dst = abs_dst.with_suffix(abs_dst.suffix + ".tmp_copy")
        shutil.copy2(abs_src, temp_dst)
        if abs_dst.exists():
            abs_dst.unlink()
        temp_dst.rename(abs_dst)
        success = True
            
    except Exception as e:
        success = False
        err_msg = str(e)
        # Clean up partially written temp files
        try:
            if 'temp_dst' in locals() and temp_dst.exists():
                temp_dst.unlink()
        except Exception:
            pass
            
    duration = time.time() - t_start
    duration = max(0.001, duration)
    speed = bytes_transferred / duration
        
    if success:
        # Update Database states
        sync_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        database.set_sync_state(job_id, rel_path, file_size, mtime, 'synced', sync_time_str)
        database.add_history_entry(job_id, abs_src.name, 'success', bytes_transferred, bytes_saved)
        if progress_callback:
            progress_callback(rel_path, 'success', bytes_transferred, bytes_saved)
            
        with active_syncs_lock:
            if job_id in active_syncs and rel_path in active_syncs[job_id]['file_transfers']:
                f_transfer = active_syncs[job_id]['file_transfers'][rel_path]
                f_transfer['status'] = 'Success'
                f_transfer['duration'] = duration
                f_transfer['speed'] = speed
                
        return {'status': 'success', 'bytes_transferred': bytes_transferred, 'bytes_saved': bytes_saved}
    else:
        # Failed copy/transcode
        sync_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        database.set_sync_state(job_id, rel_path, file_size, mtime, 'failed', sync_time_str)
        database.add_history_entry(job_id, abs_src.name, 'failed', 0, 0, err_msg)
        if progress_callback:
            progress_callback(rel_path, 'failed', 0, 0, err_msg)
            
        with active_syncs_lock:
            if job_id in active_syncs and rel_path in active_syncs[job_id]['file_transfers']:
                f_transfer = active_syncs[job_id]['file_transfers'][rel_path]
                f_transfer['status'] = 'Failed'
                f_transfer['duration'] = duration
                f_transfer['speed'] = 0.0
                f_transfer['error'] = err_msg
                
        return {'status': 'failed', 'error': err_msg}

def sync_job(job_id, progress_callback=None, finished_callback=None, files_to_sync=None):
    """
    Run sync process for a single job in a thread-safe manner.
    """
    job = database.get_job(job_id)
    if not job or not job['active']:
        if finished_callback:
            finished_callback(job_id, False, "Job is invalid or inactive")
        return
        
    # Get exclusive lock for this job to prevent double-runs
    lock = get_job_lock(job_id)
    if not lock.acquire(blocking=False):
        if finished_callback:
            finished_callback(job_id, False, "Job is already running")
        return
        
    # Register as running
    with active_syncs_lock:
        active_syncs[job_id] = {
            'name': job['name'],
            'total_files': 0,
            'processed_files': 0,
            'current_file': '',
            'bytes_transferred': 0,
            'bytes_saved': 0,
            'cancel_requested': False,
            'file_transfers': {},
            'start_time': time.time(),
            'job_id': job_id
        }
        
    def run():
        error_occurred = False
        message = "Sync completed successfully"
        
        try:
            settle_time = database.get_setting("settle_time_seconds", 60)
            max_threads = database.get_setting("max_threads", 4)
            oiiotool_path = database.get_setting("oiiotool_path", "oiiotool.exe")
            
            # --- PRE-SYNC HOOKS ---
            
            # 1. Missing Frame Validation (Source)
            try:
                validate_missing_frames(job_id, job['source'])
            except Exception:
                pass
                
            # 2. Cache Auto-Pruning (Destination)
            try:
                prune_destination_cache(job)
            except Exception:
                pass
            
            # Scan files or use pre-selected list
            if files_to_sync is not None:
                pending_files = files_to_sync
            else:
                pending_files = scan_job_files(job)
            total_files = len(pending_files)

            
            with active_syncs_lock:
                active_syncs[job_id]['total_files'] = total_files
                for f_info in pending_files:
                    active_syncs[job_id]['file_transfers'][f_info['relative_path']] = {
                        'relative_path': f_info['relative_path'],
                        'size': f_info['size'],
                        'status': 'Pending',
                        'speed': 0.0,
                        'duration': 0.0,
                        'error': None
                    }
                
            if total_files > 0:
                # Run parallel worker thread pool
                with ThreadPoolExecutor(max_workers=max_threads) as executor:
                    futures = {}
                    for f_info in pending_files:
                        fut = executor.submit(
                            process_file_sync, job, f_info, settle_time, oiiotool_path, progress_callback
                        )
                        futures[fut] = f_info
                        
                    for fut in as_completed(futures):
                        # Check cancel flag
                        with active_syncs_lock:
                            if active_syncs[job_id]['cancel_requested']:
                                executor.shutdown(wait=False, cancel_futures=True)
                                message = "Sync cancelled by user"
                                break
                                
                        f_info = futures[fut]
                        try:
                            res = fut.result()
                            with active_syncs_lock:
                                active_syncs[job_id]['processed_files'] += 1
                                active_syncs[job_id]['current_file'] = f_info['relative_path']
                                if res['status'] == 'success':
                                    active_syncs[job_id]['bytes_transferred'] += res['bytes_transferred']
                                    active_syncs[job_id]['bytes_saved'] += res['bytes_saved']
                        except Exception as e:
                            error_occurred = True
                            message = f"Error processing file: {e}"
            
            # --- POST-SYNC HOOKS ---
            
            # 3. Post-Sync MP4 Proxy Generation
            if total_files > 0 and not error_occurred and not active_syncs[job_id]['cancel_requested']:
                try:
                    generate_mp4_proxies(job)
                except Exception:
                    pass
                            
            # Update last run timestamp
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            database.update_job_last_run(job_id, now_str)
            
        except Exception as e:
            error_occurred = True
            message = str(e)
        finally:
            lock.release()
            with active_syncs_lock:
                if job_id in active_syncs:
                    del active_syncs[job_id]
            if finished_callback:
                finished_callback(job_id, not error_occurred, message)
                
    # Run in a daemon thread so it doesn't block GUI exit
    t = threading.Thread(target=run, daemon=True)
    t.start()


def request_cancel_sync(job_id):
    with active_syncs_lock:
        if job_id in active_syncs:
            active_syncs[job_id]['cancel_requested'] = True
            return True
    return False

def check_and_run_schedules(progress_callback=None, finished_callback=None):
    """
    Scan all active jobs and execute them if their schedule matches.
    """
    jobs = database.get_all_jobs()
    now = datetime.now()
    
    for job in jobs:
        if not job['active']:
            continue
            
        schedule_type = job['schedule_type'].lower()
        schedule_val = job['schedule_value']
        last_run = job['last_run']
        
        should_run = False
        
        if schedule_type == 'hourly' or schedule_type == 'interval':
            try:
                val = int(schedule_val) if schedule_val else 1
            except ValueError:
                val = 1
                
            multiplier = 60 if schedule_type == 'interval' else 3600
            
            if not last_run:
                should_run = True
            else:
                last_run_dt = datetime.strptime(last_run, "%Y-%m-%d %H:%M:%S")
                delta_sec = (now - last_run_dt).total_seconds()
                if delta_sec >= (val * multiplier):
                    should_run = True
                    
        elif schedule_type == 'daily':
            # schedule_val is expected to be "HH:MM", e.g., "18:30"
            if not schedule_val:
                schedule_val = "18:00" # Default 6pm
                
            try:
                sched_h, sched_m = map(int, schedule_val.split(':'))
            except Exception:
                sched_h, sched_m = 18, 0
                
            # Target datetime for today
            sched_today = now.replace(hour=sched_h, minute=sched_m, second=0, microsecond=0)
            
            if not last_run:
                # If we've passed the daily scheduled time today, run it.
                if now >= sched_today:
                    should_run = True
            else:
                last_run_dt = datetime.strptime(last_run, "%Y-%m-%d %H:%M:%S")
                # If last run was before the scheduled time today AND current time is past the scheduled time today
                if last_run_dt < sched_today and now >= sched_today:
                    should_run = True
                    
        # Manual jobs are skipped in schedule loops
        if should_run:
            sync_job(job['id'], progress_callback, finished_callback)
