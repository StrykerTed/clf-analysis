import os
from pyarcam.clfutil import CLFFile

def inspect_layer_pointer(layer_pointer, prefix=""):
    """Deep inspect a LayerPointer object"""
    attributes = dir(layer_pointer)
    attributes = [attr for attr in attributes if not attr.startswith('__')]
    
    print(f"\n{prefix}LayerPointer inspection:")
    
    for attr in attributes:
        try:
            value = getattr(layer_pointer, attr)
            print(f"{prefix}{attr}: {type(value)}")
            print(f"{prefix}  Value: {value}")
        except Exception as e:
            print(f"{prefix}Error accessing {attr}: {str(e)}")

def main():
    try:
        # Get first CLF file
        base_dir = os.getcwd()
        build_dir = os.path.join(base_dir, "preprocess build-270851.axbp")
        models_dir = os.path.join(build_dir, "Models", "Stack_0_Skin_ Stock_Merge")
        
        clf_files = [f for f in os.listdir(models_dir) if f.endswith('.clf')]
        if not clf_files:
            print("No CLF files found")
            return
            
        filepath = os.path.join(models_dir, clf_files[0])
        print(f"Analyzing: {clf_files[0]}")
        
        part = CLFFile(filepath)
        
        # Look for LayerPointer objects
        if hasattr(part, 'layers'):
            print(f"\nFound {len(part.layers)} layer pointers")
            
            # Look at first few layer pointers
            for i, layer_pointer in enumerate(part.layers[:3]):
                print(f"\nInspecting layer pointer {i}")
                inspect_layer_pointer(layer_pointer)
                
                # Try to access the actual layer
                try:
                    layer = part.find(layer_pointer.z)
                    print(f"\nLayer at z={layer_pointer.z}:")
                    print(f"Number of shapes: {len(layer.shapes) if hasattr(layer, 'shapes') else 0}")
                except Exception as e:
                    print(f"Error accessing layer: {str(e)}")

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()