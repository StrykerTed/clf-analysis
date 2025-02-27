# get_platform_paths_shapes_shapely.py
import os
import sys
import matplotlib.pyplot as plt   
import numpy as np   
import logging
import json

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
    create_clean_platform
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


def main():
    wanted_layer_heights = list(range(1, 201, 5))
    
    # Get the directory paths using the new utility function
    paths = get_project_paths()
    script_dir = paths["script_dir"]
    project_root = paths["project_root"]
    config_dir = paths["config_dir"]
    
    print(f"Script directory: {script_dir}")
    print(f"Project root: {project_root}")

    logger, log_queue, listener = setup_logging(project_root)
    abp_file = "/Users/ted.tedford/Library/CloudStorage/OneDrive-Stryker/EBM4/preprocess build-411821.abp"

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
        
        logger.info("Configuration parameters:")
        logger.info(f"  - Draw Points: {draw_points}")
        logger.info(f"  - Draw Lines: {draw_lines}")
        logger.info(f"  - Fill Closed Shapes: {fill_closed}")
        logger.info(f"  - Exclude Folders: {exclude_folders}")
        logger.info(f"  - Save Layer Partials: {save_layer_partials}")
        logger.info(f"  - Save Clean Platforms: {save_clean}")
        logger.info(f"  - Save Clean PNG: {save_clean_png}")
        logger.info(f"  - Alignment Style Only: {alignment_style_only}")

        # Only ask for height mode if saving clean platforms
        clean_heights = None
        if save_clean:
            height_choice = 'full'
            if height_choice == 'full':
                logger.info("Will process full range of heights at 0.05mm intervals")
            else:
                logger.info("Will process sample heights only")

        # Load exclusion patterns
        exclusion_patterns = load_exclusion_patterns(config_dir) if exclude_folders else []
        
        if exclude_folders:
            logger.info("Excluding folders containing these patterns:")
            for pattern in exclusion_patterns:
                logger.info(f"  - {pattern}")

        # Create output directory based on the ABP filename
        abp_name = os.path.basename(build_dir)
        output_dir = create_output_folder(abp_name, project_root, save_layer_partials, alignment_style_only)
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
        
        # Process each CLF file
        for clf_info in clf_files:
            try:
                if should_skip_folder(clf_info['folder'], exclusion_patterns):
                    print(f"WARNING: Skipping incorrectly included file: {clf_info['name']} in {clf_info['folder']}")
                    continue
                    
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
                        # print(f"  Analyzing layer at height {height:.3f}mm")
                        layer_info = analyze_layer(part, height, output_dir, clf_info, 
                                                path_counts, shape_types, file_identifier_counts,
                                                shapes_by_identifier,
                                                draw_points=draw_points, 
                                                draw_lines=draw_lines,
                                                save_layer_partials=save_layer_partials)
                        if isinstance(layer_info, dict):
                            platform_info["layers"].append(layer_info)
                
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

        # Create clean platform views with full or sample heights
        if save_clean:
            print("\nGenerating clean platform views...")
            if height_choice == 'full':
                max_height = get_max_layer_height(clf_files)
                clean_heights = generate_full_layer_heights(max_height)
                print(f"Processing all layers from 0.0500mm to {max_height}mm at 0.05mm intervals")
            else:
                clean_heights = wanted_layer_heights
                print(f"Processing sample layers: {clean_heights}")
                
            for height in clean_heights:
                try:
                    print(f"Processing height {height}mm...")
                    clean_file = create_clean_platform(
                        clf_files, 
                        output_dir,
                        height=height,
                        fill_closed=fill_closed,
                        alignment_style_only=alignment_style_only,
                        save_clean_png=True
                    )

                    if save_clean_png and clean_file:
                        platform_info["clean_platforms"].append({
                            "height": height,
                            "filename": clean_file
                        })
                        print(f"Created clean platform at {height}mm: {clean_file}")
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