import os
from pyarcam.clfutil import CLFFile
import numpy as np
from pprint import pprint

def inspect_shapely_geometry(shape):
    """Inspect the shapely geometry of the shape"""
    print("\nShapely Geometry Inspection:")
    try:
        # Get the shapely geometry
        geom = shape.shapely()
        print(f"Geometry Type: {geom.geom_type}")
        print(f"Is Valid: {geom.is_valid}")
        print(f"Is Simple: {geom.is_simple}")
        print(f"Is Ring: {geom.is_ring if hasattr(geom, 'is_ring') else 'N/A'}")
        print(f"Is Closed: {geom.is_closed if hasattr(geom, 'is_closed') else 'N/A'}")
        print(f"Length: {geom.length}")
        print(f"Area: {geom.area}")
        print(f"Bounds: {geom.bounds}")
        
        # Get coordinates
        if hasattr(geom, 'coords'):
            coords = list(geom.coords)
            print(f"\nNumber of coordinates: {len(coords)}")
            print(f"First coordinate: {coords[0]}")
            print(f"Last coordinate: {coords[-1]}")
            if len(coords) > 1:
                print(f"Distance between first and last points: {np.sqrt((coords[0][0] - coords[-1][0])**2 + (coords[0][1] - coords[-1][1])**2)}")
        
    except Exception as e:
        print(f"Error in shapely inspection: {e}")

def inspect_path_method(shape):
    """Inspect the path method of the shape"""
    print("\nPath Method Inspection:")
    try:
        path = shape.path()
        print(f"Path Type: {type(path)}")
        print(f"Path Attributes: {[attr for attr in dir(path) if not attr.startswith('__')]}")
        
        # Try to get path properties
        if hasattr(path, 'closed'):
            print(f"Path Closed: {path.closed}")
        if hasattr(path, 'curves'):
            print(f"Number of curves: {len(path.curves)}")
        if hasattr(path, 'length'):
            print(f"Path Length: {path.length}")
            
    except Exception as e:
        print(f"Error in path inspection: {e}")

def inspect_points_detailed(points):
    """Detailed inspection of points"""
    print("\nPoints Inspection:")
    if isinstance(points, list) and len(points) > 0 and isinstance(points[0], np.ndarray):
        points = points[0]  # Get first point array
        
        print(f"Number of points: {len(points)}")
        print(f"First point: {points[0]}")
        print(f"Last point: {points[-1]}")
        
        # Calculate arc properties
        if len(points) > 2:
            # Calculate center and radius
            try:
                # Get three points - start, middle, and end
                p1 = points[0]
                p2 = points[len(points)//2]
                p3 = points[-1]
                
                # Calculate center using circumcenter formula
                # This is a rough approximation for checking if points lie on a circle
                a = np.linalg.norm(p2 - p3)
                b = np.linalg.norm(p1 - p3)
                c = np.linalg.norm(p1 - p2)
                
                s = (a + b + c) / 2
                area = np.sqrt(s * (s - a) * (s - b) * (s - c))
                
                if area > 0:
                    R = (a * b * c) / (4 * area)
                    print(f"\nApproximate circle properties:")
                    print(f"Estimated radius: {R:.3f}mm")
                    
                    # Check if points are roughly equidistant from estimated center
                    distances = np.sqrt(np.sum((points - points.mean(axis=0))**2, axis=1))
                    mean_dist = np.mean(distances)
                    std_dist = np.std(distances)
                    print(f"Mean distance from center: {mean_dist:.3f}mm")
                    print(f"Standard deviation of distances: {std_dist:.3f}mm")
                    
                    # Calculate angular coverage
                    angles = np.arctan2(points[:,1] - points.mean(axis=0)[1],
                                      points[:,0] - points.mean(axis=0)[0])
                    angle_range = np.ptp(angles) * 180 / np.pi
                    print(f"Angular coverage: {angle_range:.1f} degrees")
                
            except Exception as e:
                print(f"Error calculating circle properties: {e}")

def main():
    try:
        subfolder = "Cylinder"
        base_dir = os.getcwd()
        build_dir = os.path.join(base_dir, "preprocess build-270851.abp")
        models_dir = os.path.join(build_dir, "Models", subfolder)
        
        if not os.path.exists(models_dir):
            print("Directory not found!")
            return
            
        clf_files = [f for f in os.listdir(models_dir) if f.endswith('.clf')]
        if not clf_files:
            print("No CLF files found")
            return
            
        # Analyze first CLF file at 1mm height
        filepath = os.path.join(models_dir, clf_files[0])
        print(f"Analyzing: {clf_files[0]}")
        
        part = CLFFile(filepath)
        layer = part.find(1.0)
        
        if not layer or not hasattr(layer, 'shapes') or not layer.shapes:
            print("No shapes found in layer")
            return
            
        # Get first shape
        shape = layer.shapes[0]
        
        # Inspect shapely geometry
        inspect_shapely_geometry(shape)
        
        # Inspect path method
        inspect_path_method(shape)
        
        # Inspect points in detail
        if hasattr(shape, 'points'):
            inspect_points_detailed(shape.points)
            
    except Exception as e:
        print(f"Error in main execution: {e}")

if __name__ == "__main__":
    main()