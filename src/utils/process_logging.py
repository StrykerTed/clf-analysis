# process_logging.py
"""
Process logging utilities for tracking program execution status.
"""
import json
import os
from pathlib import Path
from datetime import datetime


def create_process_log_start(build_path, program_name, start_time):
    """
    Create or update the processes_run.json file to mark the start of a program execution.
    This creates a log entry with status "running" that can be monitored externally.
    
    Args:
        build_path (str): Path to the build directory
        program_name (str): Name of the program that was run
        start_time (datetime): When the program started
    
    Returns:
        str: Unique run_id for this execution (timestamp format)
    """
    processes_file = Path(build_path) / "processes_run.json"
    run_id = start_time.strftime("%Y%m%d_%H%M%S")
    
    # Create the entry for this program run (initial state)
    run_entry = {
        "run_id": run_id,
        "start_time": start_time.isoformat(),
        "end_time": None,
        "duration_seconds": None,
        "status": "running",
        "timestamp_folder": run_id
    }
    
    # Load existing data or create new structure
    if processes_file.exists():
        try:
            with open(processes_file, 'r') as f:
                processes_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            processes_data = {}
    else:
        processes_data = {}
    
    # Initialize program entry if it doesn't exist or has old structure
    if program_name not in processes_data:
        processes_data[program_name] = {
            "description": "CLF analysis and platform path processing",
            "runs": []
        }
    else:
        # Check if existing entry has the new "runs" structure
        if "runs" not in processes_data[program_name]:
            # Convert old structure to new structure
            old_entry = processes_data[program_name].copy()
            processes_data[program_name] = {
                "description": "CLF analysis and platform path processing",
                "runs": []
            }
            # If there was old data, preserve it as a legacy run
            if "start_time" in old_entry:
                legacy_run = {
                    "run_id": "legacy_run",
                    "start_time": old_entry.get("start_time"),
                    "end_time": old_entry.get("end_time"),
                    "duration_seconds": old_entry.get("duration_seconds"),
                    "status": old_entry.get("status", "unknown"),
                    "timestamp_folder": "legacy"
                }
                processes_data[program_name]["runs"].append(legacy_run)
    
    # Add this run to the program's history
    processes_data[program_name]["runs"].append(run_entry)
    
    # Save the updated data
    try:
        with open(processes_file, 'w') as f:
            json.dump(processes_data, f, indent=2)
        return run_id
    except Exception as e:
        # Don't fail the main program if logging fails
        print(f"Warning: Could not create process log start: {e}")
        return run_id


def update_process_log_finish(build_path, program_name, run_id, end_time, status="completed"):
    """
    Update the processes_run.json file to mark the completion of a program execution.
    This updates an existing log entry from "running" to the final status.
    
    Args:
        build_path (str): Path to the build directory
        program_name (str): Name of the program that was run
        run_id (str): Unique run identifier from create_process_log_start
        end_time (datetime): When the program finished
        status (str): Status of the execution (completed, failed, etc.)
    """
    processes_file = Path(build_path) / "processes_run.json"
    
    # Load existing data
    if not processes_file.exists():
        print(f"Warning: Process log file not found: {processes_file}")
        return False
    
    try:
        with open(processes_file, 'r') as f:
            processes_data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        print(f"Warning: Could not read process log file: {processes_file}")
        return False
    
    # Find and update the specific run entry
    if program_name not in processes_data:
        print(f"Warning: Program {program_name} not found in process log")
        return False
    
    # Check if the program entry has the new "runs" structure
    if "runs" not in processes_data[program_name]:
        print(f"Warning: Program {program_name} has old structure without 'runs' array")
        return False
    
    # Find the run entry with matching run_id
    run_found = False
    for run_entry in processes_data[program_name]["runs"]:
        if run_entry.get("run_id") == run_id:
            # Parse start time to calculate duration
            try:
                start_time_str = run_entry["start_time"]
                start_time = datetime.fromisoformat(start_time_str)
                duration_seconds = (end_time - start_time).total_seconds()
            except Exception as e:
                print(f"Warning: Could not calculate duration: {e}")
                duration_seconds = None
            
            # Update the entry
            run_entry["end_time"] = end_time.isoformat()
            run_entry["duration_seconds"] = duration_seconds
            run_entry["status"] = status
            run_found = True
            break
    
    if not run_found:
        print(f"Warning: Run with ID {run_id} not found for program {program_name}")
        return False
    
    # Save the updated data
    try:
        with open(processes_file, 'w') as f:
            json.dump(processes_data, f, indent=2)
        return True
    except Exception as e:
        print(f"Warning: Could not update process log finish: {e}")
        return False
