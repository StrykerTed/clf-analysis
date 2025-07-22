# get_platform_paths_shapes_shapely.py
import os
import sys
import matplotlib.pyplot as plt   
import numpy as np   
import logging
import json
import multiprocessing
from multiprocessing import Pool
from config import PROJECT_ROOT, MY_OUTPUTS

# Add parent directory to path to find setup_paths
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import setup_paths

from utils.pyarcam.clfutil import CLFFile

from utils.platform_analysis.file_handlers import (
    setup_abp_folders,
)

from utils.myfuncs.file_utils import (
    create_output_folder,
    find_clf_files,
    load_exclusion_patterns,
    should_skip_folder
)

from utils.myfuncs.print_utils import (
    print_analysis_summary,
    print_identifier_summary,
    create_unclosed_shapes_view
)

from utils.myfuncs.logging_utils import setup_logging

# Import new modularized functions
from utils.platform_analysis.visualization_utils import (
    create_combined_identifier_platform_view,
    create_non_identifier_platform_view,
    create_identifier_platform_view,
    create_platform_composite_with_folders, 
    create_platform_composite,
    create_clean_platform,
    create_combined_holes_platform_view
)

from utils.platform_analysis.exclusion_handler import (
    process_excluded_files_details,
    track_excluded_file_detail
)

from utils.platform_analysis.data_processing import (
    analyze_layer,
    generate_full_layer_heights,
    get_max_layer_height
)

from utils.platform_analysis.config_utils import (
    get_project_paths,
    setup_directories
)

# Define helper function for multiprocessing
def process_height(args):
    height, clf_files, output_dir, fill_closed, alignment_style_only, save_clean_png = args
    try:
        print(f"Processing height {height}mm...")
        clean_file = create_clean_platform(
            clf_files, 
            output_dir,
            height=height,
            fill_closed=fill_closed,
            alignment_style_only=alignment_style_only,
            save_clean_png=save_clean_png
        )
        
        if save_clean_png and clean_file:
            result = {
                "height": height,
                "filename": clean_file,
                "success": True
            }
            print(f"Created clean platform at {height}mm: {clean_file}")
            return result
        return {"height": height, "success": False}
    except Exception as e:
        print(f"Error creating clean platform at height {height}mm: {str(e)}")
        return {"height": height, "error": str(e), "success": False}


# Define helper function for holes processing
def process_holes_height(args):
    height, clf_files, output_dir = args
    try:
        print(f"Processing holes view at height {height}mm...")
        holes_view_file, holes_stats = create_combined_holes_platform_view(clf_files, output_dir, height=height)
        if holes_view_file:
            result = {
                "height": height,
                "filename": holes_view_file,
                "holes_statistics": holes_stats,
                "success": True
            }
            print(f"Created holes view at {height}mm: {holes_stats['total_holes']} holes found")
            return result
        return {"height": height, "success": False}
    except Exception as e:
        print(f"Error creating holes view at height {height}mm: {str(e)}")
        return {"height": height, "error": str(e), "success": False}

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
    import json
    from pathlib import Path
    
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
    import json
    from pathlib import Path
    from datetime import datetime
    
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


def main():
    # Clear the terminal screen based on OS
    import platform
    import os
    from datetime import datetime
    if platform.system() == "Windows":
        os.system('cls')
    else:  # For Mac and Linux
        os.system('clear')
        
    # Record start time
    start_time = datetime.now()
    
    wanted_layer_heights = list(range(1, 201, 5))
    
    # Use config.py for project paths
    project_root = PROJECT_ROOT
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(project_root, "config")
    
    print(f"Script directory: {script_dir}")
    print(f"Project root: {project_root}")

    logger, log_queue, listener = setup_logging(project_root)
    
    # Get build ID from user
    build_id = input("Enter the build ID (e.g., 271360): ").strip()
    if not build_id:
        print("Build ID is required. Exiting.")
        return
    
    # Set up build path early so we can log the start
    main_build_folder = "/Users/ted.tedford/Documents/MIDAS"
    build_path = os.path.join(main_build_folder, build_id)
    os.makedirs(build_path, exist_ok=True)
    
    # Create process log entry to mark the start of execution using new function
    run_id = create_process_log_start(build_path, "clf_analysis", start_time)
    logger.info(f"Started process logging with run_id: {run_id}")
    
    abp_file = f"/Users/ted.tedford/Public/MyLocalRepos/clf_analysis_clean/abp_sourcefiles/preprocess build-{build_id}.abp"
    
    # Check if the ABP file exists
    if not os.path.exists(abp_file):
        print(f"ABP file not found: {abp_file}")
        print("Please check the build ID and ensure the file exists.")
        # Log the failure and stop
        end_time = datetime.now()
        update_process_log_finish(build_path, "clf_analysis", run_id, end_time, "failed")
        return

    logger.info(f"Processing ABP file: {abp_file}")
    
    build_dir = setup_abp_folders(abp_file)
    logger.info(f"Build directory set up at: {build_dir}")

    try:
        draw_points = 'y'
        draw_lines = 'y'
        fill_closed = 'y'
        exclude_folders = 'y'
        save_layer_partials = False 
        save_clean = 'y'
        save_clean_png = False
        alignment_style_only = False
        draw_excluded = False  # Temporarily disable to avoid blocking multiprocessing
        
        # Get holes view interval from user at startup
        holes_interval = input("Create Holes View for every x mm (default 10): ").strip()
        if not holes_interval:
            holes_interval = 10
        else:
            try:
                holes_interval = float(holes_interval)
            except ValueError:
                print("Invalid input, using default 10mm")
                holes_interval = 10
        
        # Get composite platform views preference from user
        composite_views_input = input("Create composite platform views? yes/no (default no): ").strip().lower()
        create_composite_views = composite_views_input in ['yes', 'y', '1', 'true']
        
        # Control variables for PNG creation
        create_composite_transparent_pngs = False  # Set to True to enable transparent composite PNG creation
        
        logger.info("Configuration parameters:")
        logger.info(f"  - Draw Points: {draw_points}")
        logger.info(f"  - Draw Lines: {draw_lines}")
        logger.info(f"  - Fill Closed Shapes: {fill_closed}")
        logger.info(f"  - Exclude Folders: {exclude_folders}")
        logger.info(f"  - Save Layer Partials: {save_layer_partials}")
        logger.info(f"  - Save Clean Platforms: {save_clean}")
        logger.info(f"  - Save Clean PNG: {save_clean_png}")
        logger.info(f"  - Alignment Style Only: {alignment_style_only}")
        logger.info(f"  - Draw Excluded Paths: {draw_excluded}")
        logger.info(f"  - Holes View Interval: {holes_interval}mm")
        logger.info(f"  - Create Composite Views: {create_composite_views}")
        logger.info(f"  - Create Composite Transparent PNGs: {create_composite_transparent_pngs}")

        # Load exclusion patterns
        exclusion_patterns = load_exclusion_patterns(config_dir) if exclude_folders else []
        
        if exclude_folders:
            logger.info("Excluding folders containing these patterns:")
            for pattern in exclusion_patterns:
                logger.info(f"  - {pattern}")

        # Create output directory using MIDAS-style structure with build ID
        # build_path was already created earlier for logging
        
        # Create clf_analysis subfolder
        clf_analysis_path = os.path.join(build_path, "clf_analysis")
        
        # Clear existing clf_analysis folder if it exists and recreate it
        if os.path.exists(clf_analysis_path):
            import shutil
            shutil.rmtree(clf_analysis_path)
            print(f"Cleared existing clf_analysis folder: {clf_analysis_path}")
        
        os.makedirs(clf_analysis_path, exist_ok=True)
        
        # Create subdirectories within clf_analysis
        layer_partials_dir = os.path.join(clf_analysis_path, "layer_partials")
        composite_platforms_dir = os.path.join(clf_analysis_path, "composite_platforms")
        identifier_views_dir = os.path.join(clf_analysis_path, "identifier_views")
        clean_platforms_dir = os.path.join(clf_analysis_path, "clean_platforms")
        
        os.makedirs(layer_partials_dir, exist_ok=True)
        os.makedirs(composite_platforms_dir, exist_ok=True)
        os.makedirs(identifier_views_dir, exist_ok=True)
        os.makedirs(clean_platforms_dir, exist_ok=True)
        
        output_dir = clf_analysis_path
        
        print(f"Created build directory: {build_path}")
        print(f"Created clf_analysis directory: {clf_analysis_path}")
        print(f"Created subdirectories: layer_partials, composite_platforms, identifier_views, clean_platforms")
        
        logger.info(f"Created output directory at: {output_dir}")
        
        logger.info(f"Looking for build directory at: {build_dir}")
        if not os.path.exists(build_dir):
            logger.error("Build directory not found!")
            # Log the failure and stop
            end_time = datetime.now()
            update_process_log_finish(build_path, "clf_analysis", run_id, end_time, "failed")
            return
            
        logger.info("Finding CLF files...")
        all_clf_files = find_clf_files(build_dir)
        
        # Filter CLF files based on exclusion patterns
        if exclude_folders:
            clf_files = []
            for clf_info in all_clf_files:
                should_skip = should_skip_folder(clf_info['folder'], exclusion_patterns)
                if should_skip:
                    logger.debug(f"Skipping file: {clf_info['name']} in {clf_info['folder']}")
                else:
                    clf_files.append(clf_info)
                    logger.debug(f"Keeping file: {clf_info['name']} in {clf_info['folder']}")
                    
            excluded_count = len(all_clf_files) - len(clf_files)
            logger.info(f"Found {len(all_clf_files)} total CLF files")
            logger.info(f"Excluded {excluded_count} files based on folder patterns")
            logger.info(f"Processing {len(clf_files)} CLF files")
        else:
            clf_files = all_clf_files
            logger.info(f"Found {len(clf_files)} CLF files")
        
        # Dictionaries to track statistics
        path_counts = {}
        shape_types = {}
        file_identifier_counts = {}
        shapes_by_identifier = {}
        closed_paths_found = {}
        
        # Add dictionaries for excluded paths
        excluded_shapes_by_identifier = {}
        excluded_file_identifier_counts = {}
        excluded_closed_paths_found = {}
        
        platform_info = {
            "files_analyzed": [],
            "layers": [],
            "platform_composites": [],
            "clean_platforms": [],
            "file_identifier_summary": [],
            "identifier_platform_views": [],
            "non_identifier_views": None,  # Add this line
            "closed_paths_summary": {},
            "global_height_info": {
                "min_height": None,
                "max_height": None,
                "num_samples": None,
                "height_samples": [],
                "padding_applied": None
            },
            "exclusion_info": {
                "exclusions_enabled": exclude_folders,
                "patterns_used": exclusion_patterns if exclude_folders else [],
                "files_excluded": excluded_count if exclude_folders else 0
            }
        }
        
        # Process each CLF file (both included and excluded for analysis)
        all_files_to_process = all_clf_files if draw_excluded else clf_files
        
        # Track excluded files for reporting
        excluded_files_details = []
        
        # STEP 1: Determine global height range across all files
        print(f"\nStep 1: Determining global height range across all files...")
        global_min_height = float('inf')
        global_max_height = float('-inf')
        valid_files = []
        
        for clf_info in all_files_to_process:
            try:
                is_excluded = should_skip_folder(clf_info['folder'], exclusion_patterns) if exclude_folders else False
                
                if is_excluded and not draw_excluded:
                    continue
                    
                part = CLFFile(clf_info['path'])
                
                if hasattr(part, 'box'):
                    file_min = float(part.box.min[2])
                    file_max = float(part.box.max[2])
                    
                    global_min_height = min(global_min_height, file_min)
                    global_max_height = max(global_max_height, file_max)
                    
                    # Store file info for processing
                    file_info = {
                        "filename": clf_info['name'],
                        "folder": clf_info['folder'],
                        "num_layers": part.nlayers,
                        "z_range": [file_min, file_max],
                        "bounds": {
                            "x_range": [float(part.box.min[0]), float(part.box.max[0])],
                            "y_range": [float(part.box.min[1]), float(part.box.max[1])],
                            "z_range": [file_min, file_max]
                        },
                        "clf_info": clf_info,
                        "is_excluded": is_excluded,
                        "part_object": part  # Keep reference for processing
                    }
                    valid_files.append(file_info)
                    
                    if not is_excluded:
                        platform_info["files_analyzed"].append({
                            "filename": clf_info['name'],
                            "folder": clf_info['folder'],
                            "num_layers": part.nlayers,
                            "z_range": [file_min, file_max],
                            "bounds": file_info["bounds"]
                        })
                    
            except Exception as e:
                print(f"Error reading {clf_info['name']}: {str(e)}")
        
        if global_min_height == float('inf'):
            print("No valid CLF files found with height data!")
            # Log the failure and stop
            end_time = datetime.now()
            update_process_log_finish(build_path, "clf_analysis", run_id, end_time, "failed")
            return
        
        # Add more generous padding to ensure we capture ALL edge cases
        height_range = global_max_height - global_min_height
        height_padding = max(height_range * 0.1, 5.0)  # 10% padding OR 5mm, whichever is larger
        global_min_height = max(0, global_min_height - height_padding)
        global_max_height = global_max_height + height_padding
        
        print(f"Global height range: {global_min_height:.2f} mm to {global_max_height:.2f} mm")
        print(f"Applied padding: {height_padding:.2f} mm to ensure complete coverage")
        
        # STEP 2: Generate comprehensive height samples
        # Use even more samples (25 instead of 15) to ensure complete coverage
        num_height_samples = 25
        global_heights = np.linspace(global_min_height, global_max_height, num_height_samples)
        
        # Also add specific heights that are commonly used in manufacturing
        additional_heights = []
        # Add heights at 0.1mm intervals around the edges
        edge_sampling_range = 2.0  # Sample 2mm beyond detected range
        for offset in np.arange(0.1, edge_sampling_range + 0.1, 0.1):
            if global_min_height + offset <= global_max_height:
                additional_heights.append(global_min_height + offset)
            if global_max_height - offset >= global_min_height:
                additional_heights.append(global_max_height - offset)
        
        # Combine and sort all heights
        all_heights = np.concatenate([global_heights, additional_heights])
        global_heights = np.unique(np.round(all_heights, 2))  # Remove duplicates and round
        num_height_samples = len(global_heights)
        
        # Store global height info in platform_info
        platform_info["global_height_info"] = {
            "min_height": float(global_min_height),
            "max_height": float(global_max_height),
            "num_samples": num_height_samples,
            "height_samples": [float(h) for h in global_heights],
            "padding_applied": float(height_padding)
        }
        
        print(f"Using {num_height_samples} height samples with enhanced edge coverage:")
        print(f"  Range: {global_heights[0]:.2f} mm to {global_heights[-1]:.2f} mm")
        print(f"  Samples include: {global_heights[0]:.2f}, {global_heights[1]:.2f}, ..., {global_heights[-2]:.2f}, {global_heights[-1]:.2f}")
        print(f"  This should capture shapes at heights like 141.3mm that were previously missed")
        
        # STEP 3: Process each file at all global heights
        print(f"\nStep 2: Processing {len(valid_files)} files at {num_height_samples} heights...")
        
        for file_info in valid_files:
            clf_info = file_info["clf_info"]
            part = file_info["part_object"]
            is_excluded = file_info["is_excluded"]
            
            print(f"\nProcessing {'EXCLUDED' if is_excluded else 'INCLUDED'}: {clf_info['name']} in {clf_info['folder']}")
            print(f"  File height range: {file_info['z_range'][0]:.2f} to {file_info['z_range'][1]:.2f} mm")
            
            heights_processed = 0
            heights_in_range = 0
            
            # Process at all global heights (not just file-specific heights)
            for height in global_heights:
                # Use more generous tolerance to ensure we don't miss edge cases
                tolerance = 1.0  # Increased from 0.1mm to 1.0mm for better coverage
                if (height >= file_info['z_range'][0] - tolerance and 
                    height <= file_info['z_range'][1] + tolerance):
                    
                    heights_in_range += 1
                    
                    if not is_excluded:
                        # Process included files normally
                        layer_info = analyze_layer(part, height, output_dir, clf_info, 
                                                path_counts, shape_types, file_identifier_counts,
                                                shapes_by_identifier,
                                                draw_points=draw_points, 
                                                draw_lines=draw_lines,
                                                save_layer_partials=save_layer_partials)
                        if isinstance(layer_info, dict):
                            platform_info["layers"].append(layer_info)
                        heights_processed += 1
                        
                    elif draw_excluded:
                        # Process excluded files for excluded view
                        analyze_layer(part, height, output_dir, clf_info, 
                                    {}, {}, excluded_file_identifier_counts,
                                    excluded_shapes_by_identifier,
                                    draw_points=draw_points, 
                                    draw_lines=draw_lines,
                                    save_layer_partials=False)  # Don't save partials for excluded
                        heights_processed += 1
            
            print(f"  Heights in file range: {heights_in_range}/{num_height_samples}")
            print(f"  Heights actually processed: {heights_processed}")
            if heights_in_range > heights_processed:
                print(f"  WARNING: {heights_in_range - heights_processed} heights in range were not processed!")
            
            # Track excluded file details
            if is_excluded and draw_excluded:
                excluded_file_detail = track_excluded_file_detail(
                    clf_info, part, exclusion_patterns, heights_processed
                )
                excluded_files_details.append(excluded_file_detail)
        
        print(f"\nGlobal height sampling complete!")
        print(f"Total height range processed: {global_min_height:.2f} to {global_max_height:.2f} mm")
        print(f"Height samples used: {num_height_samples}")
        
        # Create file identifier summary
        for file_path, identifiers in file_identifier_counts.items():
            summary_entry = {
                "file_path": file_path,
                "identifier_counts": {
                    str(identifier): count 
                    for identifier, count in identifiers.items()
                },
                "total_shapes": sum(identifiers.values()),
                "unique_identifiers": len(identifiers)
            }
            platform_info["file_identifier_summary"].append(summary_entry)
        
        # In main function, replace the platform view generation section with:
        print("\nGenerating identifier and non-identifier platform views...")
        for identifier, shapes_data in shapes_by_identifier.items():
            try:
                if identifier == 'no_identifier':
                    print("Creating platform view for shapes without identifiers...")
                    view_file = create_non_identifier_platform_view(shapes_data['shapes'], output_dir)
                    if view_file:
                        platform_info["non_identifier_views"] = {
                            "filename": view_file,
                            "total_shapes": shapes_data['count'],
                            "closed_paths": shapes_data['closed_paths'],
                            "total_paths": shapes_data['total_paths'],
                            "height_range": shapes_data['height_range']
                        }
                        print(f"Created non-identifier view with {shapes_data['count']} shapes")
                else:
                    print(f"Creating platform view for identifier {identifier}...")
                    view_file = create_identifier_platform_view(identifier, shapes_data, output_dir)
                    if view_file:
                        from utils.myfuncs.shape_things import should_close_path
                        closed_count = 0
                        total_count = 0
                        for shape_info in shapes_data['shapes']:
                            if shape_info['points'] is not None and len(shape_info['points']) > 2:
                                total_count += 1
                                if should_close_path(shape_info['points']):
                                    closed_count += 1
                        
                        platform_info["identifier_platform_views"].append({
                            "identifier": identifier,
                            "filename": view_file,
                            "total_shapes": shapes_data['count'],
                            "height_range": shapes_data['height_range'],
                            "closed_paths": closed_count,
                            "total_paths": total_count
                        })
                        
                        closed_paths_found[identifier] = {
                            "closed_count": closed_count,
                            "total_count": total_count,
                            "percentage_closed": (closed_count / total_count * 100) if total_count > 0 else 0
                        }
                        
                        print(f"Created identifier view for ID {identifier} "
                              f"({closed_count}/{total_count} paths closed)")
                    
            except Exception as e:
                print(f"Error creating view for {'non-identifier shapes' if identifier == 'no_identifier' else f'ID {identifier}'}: {str(e)}")
        
        # Create a combined view of all identifiers
        print("\nGenerating combined identifier platform view...")
        combined_view_file = create_combined_identifier_platform_view(shapes_by_identifier, output_dir)
        if combined_view_file:
            platform_info["combined_identifier_view"] = {
                "filename": combined_view_file,
                "total_identifiers": len([id for id in shapes_by_identifier.keys() if id != 'no_identifier'])
            }
            print(f"Created combined identifier view with {platform_info['combined_identifier_view']['total_identifiers']} identifiers")

        # Create combined holes platform view at specific height
        print("\nGenerating combined holes platform view...")
        holes_view_file, holes_stats = create_combined_holes_platform_view(clf_files, output_dir, height=134.00)
        if holes_view_file:
            platform_info["combined_holes_view"] = {
                "filename": holes_view_file,
                "holes_statistics": holes_stats
            }
            print(f"Created combined holes view with {holes_stats['total_holes']} holes found in {holes_stats['files_with_holes']} files")

        # Create holes views at regular intervals
        print("\nGenerating holes views at regular intervals...")
        
        # Get max height for the range
        max_height = get_max_layer_height(clf_files)
        holes_heights = list(np.arange(0, max_height + holes_interval, holes_interval))
        print(f"Creating holes views from 0mm to {max_height}mm every {holes_interval}mm ({len(holes_heights)} views)")
        
        # Process holes views sequentially to avoid multiprocessing issues
        successful_holes_views = []
        total_holes_found = 0
        
        for height in holes_heights:
            try:
                print(f"Processing holes view at height {height}mm...")
                holes_view_file, holes_stats = create_combined_holes_platform_view(clf_files, output_dir, height=height)
                if holes_view_file:
                    successful_holes_views.append({
                        "height": height,
                        "filename": holes_view_file,
                        "holes_statistics": holes_stats
                    })
                    total_holes_found += holes_stats["total_holes"]
                    print(f"Created holes view at {height}mm: {holes_stats['total_holes']} holes found")
                else:
                    print(f"No holes view created for {height}mm")
            except Exception as e:
                print(f"Error creating holes view at height {height}mm: {str(e)}")
        
        if successful_holes_views:
            platform_info["holes_views_interval"] = {
                "interval_mm": holes_interval,
                "total_views": len(successful_holes_views),
                "height_range": [0, max_height],
                "total_holes_across_all_views": total_holes_found,
                "views": successful_holes_views
            }
            print(f"Created {len(successful_holes_views)} holes views with total of {total_holes_found} holes across all heights")

        # Process all exclusion-related functionality
        process_excluded_files_details(
            draw_excluded, excluded_files_details, exclusion_patterns, 
            excluded_shapes_by_identifier, output_dir, platform_info
        )

        # Print summary information
        print_identifier_summary(platform_info["file_identifier_summary"], closed_paths_found)
        
        # Create composite platform views with original layer heights (conditional)
        if create_composite_views:
            print("\nGenerating platform composite views...")
            for height in wanted_layer_heights:
                try:
                    print(f"Creating composite view at height {height}mm...")
                    composite_file = create_platform_composite_with_folders(clf_files, output_dir, 
                                                            height=height, 
                                                            fill_closed=fill_closed,
                                                            create_transparent_png=create_composite_transparent_pngs)
                    platform_info["platform_composites"].append({
                        "height": height,
                        "filename": composite_file
                    })
                    print(f"Created platform composite at {height}mm: {composite_file}")
                except Exception as e:
                    print(f"Error creating composite at height {height}mm: {str(e)}")
        else:
            print("\nSkipping platform composite views (user selected no)")
            platform_info["platform_composites"] = []

        # Create clean platform views - process all heights for JSON but only create PNGs for selected heights
        if save_clean:
            print("\nGenerating clean platform views...")
            # Get all heights for data processing
            max_height = get_max_layer_height(clf_files)
            all_heights = generate_full_layer_heights(max_height)
            print(f"Processing all layers from 0.0500mm to {max_height}mm for JSON data")
            print(f"Creating PNGs only for selected heights: {wanted_layer_heights}")
            
            # Process heights sequentially to avoid multiprocessing conflicts
            print(f"Processing {len(all_heights)} heights sequentially...")
            
            for height in all_heights:
                # Only create PNG for heights that are in wanted_layer_heights
                should_create_png = height in wanted_layer_heights
                try:
                    print(f"Processing height {height}mm...")
                    clean_file = create_clean_platform(
                        clf_files, 
                        output_dir,
                        height=height,
                        fill_closed=fill_closed,
                        alignment_style_only=alignment_style_only,
                        save_clean_png=should_create_png
                    )
                    
                    if should_create_png and clean_file:
                        platform_info["clean_platforms"].append({
                            "height": height,
                            "filename": clean_file
                        })
                        print(f"Created clean platform PNG at {height}mm: {clean_file}")
                    elif should_create_png:
                        print(f"No clean platform PNG file created for {height}mm")
                    else:
                        print(f"Processed data for {height}mm (no PNG created - not in selected heights)")
                except Exception as e:
                    print(f"Error creating clean platform at height {height}mm: {str(e)}")
        
        # Add closed paths information to final JSON
        platform_info["closed_paths_summary"] = closed_paths_found
        
        unclosed_view, unclosed_count = create_unclosed_shapes_view(shapes_by_identifier, output_dir)
        if unclosed_view:
            platform_info["unclosed_shapes_view"] = {
                "filename": unclosed_view,
                "total_shapes": unclosed_count
            }
            print(f"\nCreated unclosed shapes view with {unclosed_count} shapes")
    
        # Prepare final JSON data
        json_identifier_info = {
            "path_counts": path_counts,
            "shape_types": shape_types,
            "visualization_settings": {
                "draw_points": draw_points,
                "draw_lines": draw_lines
            },
            "closed_paths": closed_paths_found
        }
        
        platform_info['analysis_summary'] = json_identifier_info
        
        # Save to JSON file
        summary_filename = "platform_info.json"
        summary_path = os.path.join(output_dir, summary_filename)
        with open(summary_path, 'w') as f:
            json.dump(platform_info, f, indent=2)
            
        logger.info(f"Saved platform info to: {summary_path}")
        print_analysis_summary(platform_info, closed_paths_found, shape_types, output_dir, summary_path)
            
        logger.info("Platform path analysis completed successfully")
        
        # Record successful completion
        end_time = datetime.now()
        logger.info(f"Program completed successfully. Total duration: {(end_time - start_time).total_seconds():.2f} seconds")
        
        # Update the process execution log
        try:
            update_process_log_finish(build_path, "clf_analysis", run_id, end_time, "completed")
            logger.info(f"Updated process log: {os.path.join(build_path, 'processes_run.json')}")
        except Exception as e:
            logger.warning(f"Could not update process log: {e}")
            
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}", exc_info=True)
        
        # Record failed completion
        end_time = datetime.now()
        if 'build_path' in locals() and 'run_id' in locals():
            update_process_log_finish(build_path, "clf_analysis", run_id, end_time, "failed")
        else:
            print(f"Could not log process failure - build_path or run_id not available: {str(e)}")
    finally:
        # Clean up the logging listener
        logger.info("Shutting down logging listener")
        listener.stop()

if __name__ == "__main__":
    main()