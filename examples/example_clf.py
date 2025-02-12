from pyarcam.clfutil import CLFFile
import numpy as np
import matplotlib.pyplot as plt

def read_clf_file(file_path):
    file = CLFFile(file_path)
    print(file)  # Print the header content
    
    if hasattr(file, 'layers') and len(file.layers) > 0:
        first_layer = file.layers[0]
        image = first_layer.load()
        
        print("\nFirst Layer Information:")
        print(f"Number of shapes: {len(image.shapes)}")
        
        if len(image.shapes) > 0:
            first_shape = image.shapes[0]
            print(f"First shape type: {type(first_shape)}")
            
            if hasattr(first_shape, 'points'):
                points = first_shape.points
                print(f"Number of points: {len(points)}")
                
                # Extract x and y coordinates
                x_coords = [p[0][0] for p in points]
                y_coords = [p[0][1] for p in points]
                
                # Plot the shape
                plt.figure(figsize=(10, 8))
                plt.plot(x_coords, y_coords, 'b-')
                plt.title('First Shape in Layer 0')
                plt.xlabel('X coordinate')
                plt.ylabel('Y coordinate')
                plt.axis('equal')
                plt.grid(True)
                plt.savefig('first_shape_plot.png')
                print("Plot of the first shape saved as 'first_shape_plot.png'")
            else:
                print("Shape does not have 'points' attribute")
        else:
            print("No shapes found in the first layer")
    else:
        print("No layers found in the file")

    print("\nAvailable attributes and methods of CLFFile:")
    for attr in dir(file):
        if not attr.startswith('__'):
            print(attr)

    print("\nBounding Box Information:")
    if hasattr(file, 'box'):
        print(f"Box: {file.box}")
    else:
        print("No 'box' attribute found")

if __name__ == "__main__":
    read_clf_file("Net.clf")