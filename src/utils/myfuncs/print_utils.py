import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import os

def add_platform_labels(plt):
    """Add standard X and Y axis labels for platform views"""
    plt.xlabel('X Position (mm)')
    plt.ylabel('Y Position (mm)')
    
def print_analysis_summary(platform_info, closed_paths_found, shape_types, output_dir, summary_path):
    """Print the analysis summary information"""
    print(f"\nAnalysis complete. Results saved to: {output_dir}")
    print(f"Summary file: {summary_path}")
    
    print("\nIdentifier-specific platform views created:")
    for view_info in platform_info["identifier_platform_views"]:
        print(f"ID {view_info['identifier']}: {view_info['filename']}")
        if 'closed_paths' in view_info:
            print(f"  Closed paths: {view_info['closed_paths']}/{view_info['total_paths']}")
    
    print("\nShape Types Summary:")
    for shape_type, count in shape_types.items():
        print(f"{shape_type}: {count} instances")
        
def create_unclosed_shapes_view(shapes_by_identifier, output_dir):
    """Create a platform view showing all unclosed shapes across all heights"""
    try:
        plt.figure(figsize=(15, 15))
        
        # Draw platform boundaries
        plt.plot([-125, 125, 125, -125, -125], 
                [-125, -125, 125, 125, -125], 
                'k--', alpha=0.5, label='Platform boundary')
        
        # Reference lines
        plt.axhline(y=0, color='gray', linestyle='-', alpha=0.3)
        plt.axvline(x=0, color='gray', linestyle='-', alpha=0.3)
        plt.grid(True, alpha=0.2)
        
        # Collect all unclosed shapes
        unclosed_shapes = []
        for identifier, data in shapes_by_identifier.items():
            for shape_info in data['shapes']:
                if shape_info['points'] is not None and not shape_info['is_closed']:
                    unclosed_shapes.append(shape_info)
        
        # Draw all unclosed shapes
        shape_colors = plt.cm.viridis(np.linspace(0, 1, len(unclosed_shapes)))
        
        for shape_info, color in zip(unclosed_shapes, shape_colors):
            if shape_info['points'] is not None:
                points = shape_info['points']
                if shape_info['type'] == 'point':
                    plt.plot(points[0, 0], points[0, 1], 'o', 
                            color=color, markersize=2, alpha=0.7)
                else:
                    plt.plot(points[:, 0], points[:, 1], '-', 
                            color=color, linewidth=0.5, alpha=0.7)
        
        plt.title(f'All Unclosed Shapes Platform View\n'
                 f'Total Unclosed Shapes: {len(unclosed_shapes)}')
        add_platform_labels(plt)
        plt.axis('equal')
        
        plt.xlim(-130, 130)
        plt.ylim(-130, 130)
        
        filename = 'unclosed_shapes_platform_view.png'
        output_path = os.path.join(output_dir, filename)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return filename, len(unclosed_shapes)
        
    except Exception as e:
        print(f"Error creating unclosed shapes view: {str(e)}")
        return None, 0
    
def print_identifier_summary(file_identifier_summary, closed_paths_found):
    """Print summary information about identifiers by file"""
    print("\nIdentifier Summary by File:")
    for summary in file_identifier_summary:
        print(f"\nFile: {summary['file_path']}")
        print(f"Total Shapes: {summary['total_shapes']}")
        print(f"Unique Identifiers: {summary['unique_identifiers']}")
        print("Identifier Counts:")
        for identifier, count in summary['identifier_counts'].items():
            print(f"  ID {identifier}: {count} shapes")
            if identifier in closed_paths_found:
                cp = closed_paths_found[identifier]
                print(f"    Closed paths: {cp['closed_count']}/{cp['total_count']} "
                      f"({cp['percentage_closed']:.1f}%)")