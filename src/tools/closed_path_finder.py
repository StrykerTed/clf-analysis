import os
from pyarcam.clfutil import CLFFile
import numpy as np
import json
from datetime import datetime

def is_path_closed(points):
    """Check if a path is closed by comparing first and last points"""
    if not isinstance(points, np.ndarray) or len(points) < 3:
        return False
    return np.allclose(points[0], points[-1], rtol=1e-5, atol=1e-8)

def find_closed_paths(clf_file_path):
    """Analyze a CLF file for closed paths"""
    results = {
        'file': os.path.basename(clf_file_path),
        'folder': os.path.dirname(clf_file_path),
        'closed_paths': []
    }
    
    try:
        part = CLFFile(clf_file_path)
        if not hasattr(part, 'box'):
            return results
            
        # Get z range
        min_z = part.box.min[2]
        max_z = part.box.max[2]
        
        # Sample some layers throughout the part
        z_heights = np.linspace(min_z, max_z, min(20, part.nlayers))
        
        for z in z_heights:
            layer = part.find(z)
            if not layer or not hasattr(layer, 'shapes'):
                continue
                
            for shape_idx, shape in enumerate(layer.shapes):
                if hasattr(shape, 'points'):
                    for point_set in shape.points:
                        if is_path_closed(point_set):
                            shape_info = {
                                'z_height': float(z),
                                'shape_index': shape_idx,
                                'num_points': len(point_set),
                                'model_id': getattr(shape.model, 'id', None) if hasattr(shape, 'model') else None,
                                'model_name': getattr(shape.model, 'name', None) if hasattr(shape, 'model') else None
                            }
                            results['closed_paths'].append(shape_info)
                            
    except Exception as e:
        print(f"Error processing {clf_file_path}: {str(e)}")
    
    return results

def main():
    try:
        # Find the build directory
        base_dir = os.getcwd()
        build_dir = os.path.join(base_dir, "preprocess build-270851.abp")
        models_dir = os.path.join(build_dir, "Models")
        
        if not os.path.exists(models_dir):
            print("Models directory not found!")
            return
            
        print("Scanning for CLF files...")
        
        # Store results
        all_results = []
        file_count = 0
        closed_path_count = 0
        
        # Walk through all subdirectories
        for root, dirs, files in os.walk(models_dir):
            for file in files:
                if file.endswith('.clf'):
                    file_count += 1
                    clf_path = os.path.join(root, file)
                    rel_path = os.path.relpath(clf_path, models_dir)
                    print(f"\nAnalyzing: {rel_path}")
                    
                    results = find_closed_paths(clf_path)
                    
                    if results['closed_paths']:
                        closed_path_count += len(results['closed_paths'])
                        all_results.append(results)
                        print(f"Found {len(results['closed_paths'])} closed paths")
        
        # Create output
        if all_results:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"closed_paths_{timestamp}.json"
            
            summary = {
                'total_files_analyzed': file_count,
                'total_closed_paths_found': closed_path_count,
                'files_with_closed_paths': len(all_results),
                'results': all_results
            }
            
            with open(output_file, 'w') as f:
                json.dump(summary, f, indent=2)
                
            print(f"\nAnalysis complete!")
            print(f"Total CLF files analyzed: {file_count}")
            print(f"Total closed paths found: {closed_path_count}")
            print(f"Files with closed paths: {len(all_results)}")
            print(f"Results saved to: {output_file}")
            
            # Print summary of files with closed paths
            print("\nFiles containing closed paths:")
            for result in all_results:
                rel_folder = os.path.relpath(result['folder'], models_dir)
                print(f"\n{os.path.join(rel_folder, result['file'])}:")
                for path in result['closed_paths'][:3]:  # Show first 3 paths per file
                    print(f"  - At height {path['z_height']:.2f}mm, "
                          f"Shape {path['shape_index']}, "
                          f"{path['num_points']} points")
                if len(result['closed_paths']) > 3:
                    print(f"  ... and {len(result['closed_paths']) - 3} more")
                    
        else:
            print("\nNo closed paths found in any files.")
            
    except Exception as e:
        print(f"Error in main execution: {str(e)}")

if __name__ == "__main__":
    main()