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
    create_combined_excluded_identifier_platform_view,
    create_non_identifier_platform_view,
    create_identifier_platform_view,
    create_platform_composite_with_folders, 
    create_platform_composite,
    create_clean_platform,
    create_combined_holes_platform_view
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


def main():
    # Clear the terminal screen based on OS
    import platform
    import os
    if platform.system() == "Windows":
        os.system('cls')
    else:  # For Mac and Linux
        os.system('clear')
        
    wanted_layer_heights = list(range(1, 201, 5))
    
    # Use config.py for project paths
    project_root = PROJECT_ROOT
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(project_root, "config")
    
    print(f"Script directory: {script_dir}")
    print(f"Project root: {project_root}")

    logger, log_queue, listener = setup_logging(project_root)
    abp_file = "/Users/ted.tedford/Public/MyLocalRepos/clf_analysis_clean/abp_sourcefiles/preprocess build-424292.abp"


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

        # Load exclusion patterns
        exclusion_patterns = load_exclusion_patterns(config_dir) if exclude_folders else []
        
        if exclude_folders:
            logger.info("Excluding folders containing these patterns:")
            for pattern in exclusion_patterns:
                logger.info(f"  - {pattern}")

        # Create output directory based on the ABP filename
        abp_name = os.path.basename(build_dir)
        # Use MY_OUTPUTS from config.py as the parent directory
        output_dir = create_output_folder(abp_name, MY_OUTPUTS, save_layer_partials, alignment_style_only)
        logger.info(f"Created output directory at: {output_dir}")
        
        # Setup all required directories
        setup_directories(output_dir, save_layer_partials, save_clean)
        
        logger.info(f"Looking for build directory at: {build_dir}")
        if not os.path.exists(build_dir):
            logger.error("Build directory not found!")
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
        
        for clf_info in all_files_to_process:
            try:
                is_excluded = should_skip_folder(clf_info['folder'], exclusion_patterns) if exclude_folders else False
                
                if is_excluded and not draw_excluded:
                    continue
                elif not is_excluded:
                    # Process included files normally
                    print(f"\nProcessing: {clf_info['name']} in {clf_info['folder']}")
                    part = CLFFile(clf_info['path'])
                    
                    file_info = {
                        "filename": clf_info['name'],
                        "folder": clf_info['folder'],
                        "num_layers": part.nlayers,
                        "z_range": [part.box.min[2], part.box.max[2]] if hasattr(part, 'box') else None,
                        "bounds": {
                            "x_range": [float(part.box.min[0]), float(part.box.max[0])] if hasattr(part, 'box') else None,
                            "y_range": [float(part.box.min[1]), float(part.box.max[1])] if hasattr(part, 'box') else None,
                            "z_range": [float(part.box.min[2]), float(part.box.max[2])] if hasattr(part, 'box') else None
                        }
                    }
                    platform_info["files_analyzed"].append(file_info)
                    
                    if hasattr(part, 'box'):
                        heights = np.linspace(part.box.min[2], part.box.max[2], 7)
                        for height in heights:
                            layer_info = analyze_layer(part, height, output_dir, clf_info, 
                                                    path_counts, shape_types, file_identifier_counts,
                                                    shapes_by_identifier,
                                                    draw_points=draw_points, 
                                                    draw_lines=draw_lines,
                                                    save_layer_partials=save_layer_partials)
                            if isinstance(layer_info, dict):
                                platform_info["layers"].append(layer_info)
                elif is_excluded and draw_excluded:
                    # Process excluded files for excluded view
                    print(f"\nProcessing EXCLUDED: {clf_info['name']} in {clf_info['folder']}")
                    part = CLFFile(clf_info['path'])
                    
                    # Track excluded file details
                    excluded_file_detail = {
                        "filename": clf_info['name'],
                        "folder": clf_info['folder'],
                        "full_path": clf_info['path'],
                        "num_layers": part.nlayers if hasattr(part, 'nlayers') else 0,
                        "matching_patterns": [pattern for pattern in exclusion_patterns if pattern in clf_info['folder']]
                    }
                    excluded_files_details.append(excluded_file_detail)
                    
                    if hasattr(part, 'box'):
                        heights = np.linspace(part.box.min[2], part.box.max[2], 7)
                        for height in heights:
                            # Use separate dictionaries for excluded files
                            analyze_layer(part, height, output_dir, clf_info, 
                                        {}, {}, excluded_file_identifier_counts,
                                        excluded_shapes_by_identifier,
                                        draw_points=draw_points, 
                                        draw_lines=draw_lines,
                                        save_layer_partials=False)  # Don't save partials for excluded
                
            except Exception as e:
                print(f"Error processing {clf_info['name']}: {str(e)}")
        
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

        # Create combined holes platform view
        print("\nGenerating combined holes platform view...")
        holes_view_file, holes_stats = create_combined_holes_platform_view(clf_files, output_dir, height=134.0)
        if holes_view_file:
            platform_info["combined_holes_view"] = {
                "filename": holes_view_file,
                "holes_statistics": holes_stats
            }
            print(f"Created combined holes view with {holes_stats['total_holes']} holes found in {holes_stats['files_with_holes']} files")

        # Create combined view of excluded identifiers if requested
        if draw_excluded and excluded_shapes_by_identifier:
            print("\nGenerating combined EXCLUDED identifier platform view...")
            excluded_combined_view_file = create_combined_excluded_identifier_platform_view(excluded_shapes_by_identifier, output_dir)
            if excluded_combined_view_file:
                platform_info["combined_excluded_identifier_view"] = {
                    "filename": excluded_combined_view_file,
                    "total_identifiers": len([id for id in excluded_shapes_by_identifier.keys() if id != 'no_identifier'])
                }
                print(f"Created combined EXCLUDED identifier view with {platform_info['combined_excluded_identifier_view']['total_identifiers']} identifiers")

        # Create exclusion details file if requested
        if draw_excluded and excluded_files_details:
            print("\nCreating exclusion details file...")
            import csv
            
            # Create CSV file
            csv_filename = "excluded_files_details.csv"
            csv_path = os.path.join(output_dir, csv_filename)
            
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['filename', 'folder', 'full_path', 'num_layers', 'matching_patterns']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for detail in excluded_files_details:
                    # Convert list to string for CSV
                    detail_copy = detail.copy()
                    detail_copy['matching_patterns'] = ', '.join(detail['matching_patterns'])
                    writer.writerow(detail_copy)
            
            # Create TXT file
            txt_filename = "excluded_files_details.txt"
            txt_path = os.path.join(output_dir, txt_filename)
            
            with open(txt_path, 'w', encoding='utf-8') as txtfile:
                txtfile.write("EXCLUDED FILES DETAILS\n")
                txtfile.write("=" * 50 + "\n\n")
                txtfile.write(f"Total excluded files: {len(excluded_files_details)}\n")
                txtfile.write(f"Exclusion patterns used: {', '.join(exclusion_patterns)}\n\n")
                
                for i, detail in enumerate(excluded_files_details, 1):
                    txtfile.write(f"{i}. {detail['filename']}\n")
                    txtfile.write(f"   Folder: {detail['folder']}\n")
                    txtfile.write(f"   Full Path: {detail['full_path']}\n")
                    txtfile.write(f"   Number of Layers: {detail['num_layers']}\n")
                    txtfile.write(f"   Matching Patterns: {', '.join(detail['matching_patterns'])}\n")
                    txtfile.write("-" * 40 + "\n\n")
            
            platform_info["exclusion_details_files"] = {
                "csv_file": csv_filename,
                "txt_file": txt_filename,
                "total_excluded": len(excluded_files_details)
            }
            
            print(f"Created exclusion details CSV: {csv_path}")
            print(f"Created exclusion details TXT: {txt_path}")
            print(f"Total excluded files documented: {len(excluded_files_details)}")

        # Print summary information
        print_identifier_summary(platform_info["file_identifier_summary"], closed_paths_found)
        
        # Create composite platform views with original layer heights
   
        print("\nGenerating platform composite views...")
        for height in wanted_layer_heights:
            try:
                print(f"Creating composite view at height {height}mm...")
                composite_file = create_platform_composite_with_folders(clf_files, output_dir, 
                                                        height=height, 
                                                        fill_closed=fill_closed)
                platform_info["platform_composites"].append({
                    "height": height,
                    "filename": composite_file
                })
                print(f"Created platform composite at {height}mm: {composite_file}")
            except Exception as e:
                print(f"Error creating composite at height {height}mm: {str(e)}")

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
            
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}", exc_info=True)
    finally:
        # Clean up the logging listener
        logger.info("Shutting down logging listener")
        listener.stop()
             
if __name__ == "__main__":
    main()