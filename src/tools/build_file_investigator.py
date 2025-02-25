import os
import binascii
import zlib
from datetime import datetime
import struct
import base64
from collections import defaultdict

def create_output_folder(base_dir):
    """Create output folder with datetime"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    my_outputs_dir = os.path.join(base_dir, "my_outputs", "build_file_investigation", timestamp)
    os.makedirs(my_outputs_dir, exist_ok=True)
    print(f"Created output directory: {my_outputs_dir}")
    return my_outputs_dir

 

def analyze_encrypted_section(data):
    """Analyze the encrypted portion of the file"""
    # Skip 4-byte header
    encrypted_data = data[4:-2]  # Exclude header and checksum
    
    def try_decrypt_block(block, key_byte):
        """Try to decrypt a single block with a key byte"""
        return bytes(b ^ key_byte for b in block)
    
    print("\nEncrypted Data Analysis:")
    print(f"Encrypted section size: {len(encrypted_data)} bytes")
    
    # Try to identify the encryption block size
    potential_blocks = [8, 16, 32, 64]
    for block_size in potential_blocks:
        if len(encrypted_data) % block_size == 0:
            print(f"Data length is divisible by {block_size} (possible block size)")
    
    # Analyze the first few blocks
    print("\nFirst block analysis (assuming 16-byte blocks):")
    for i in range(0, min(64, len(encrypted_data)), 16):
        block = encrypted_data[i:i+16]
        print(f"\nBlock {i//16}:")
        print(f"Hex: {binascii.hexlify(block).decode()}")
        
        # Try a few potential key bytes
        test_keys = [0x55, 0xAA, 0xFF, 0x33]
        for key in test_keys:
            decrypted = try_decrypt_block(block, key)
            printable_chars = sum(1 for b in decrypted if 32 <= b <= 126)
            if printable_chars > 12:  # If most chars are printable
                print(f"Key 0x{key:02x} yields {printable_chars}/16 printable chars:")
                print(f"Result: {decrypted}")
    
    return encrypted_data

def main():
    try:
        base_dir = os.getcwd()
        build_dir = os.path.join(base_dir, "preprocess build-270851.ab p")
        start_plate_dir = os.path.join(build_dir, "StartPlate")
        
        if not os.path.exists(start_plate_dir):
            print("StartPlate directory not found!")
            return
            
        xml_files = [f for f in os.listdir(start_plate_dir) if f.endswith('.xml')]
        if not xml_files:
            print("No XML files found in StartPlate directory!")
            return
            
        xml_path = os.path.join(start_plate_dir, xml_files[0])
        print(f"Found XML file: {xml_files[0]}")
        
        # Read the file
        with open(xml_path, 'rb') as f:
            data = f.read()
        
        # Analyze header
        header = data[:4]
        print("\nHeader Analysis:")
        print(f"Header (hex): {binascii.hexlify(header).decode()}")
        print(f"Header (int): {int.from_bytes(header, 'big')}")
        
        # Analyze encrypted section
        encrypted_data = analyze_encrypted_section(data)
        
        # Analyze checksum
        checksum = data[-2:]
        print(f"\nChecksum (hex): {binascii.hexlify(checksum).decode()}")
        
        # Save results
        output_dir = create_output_folder(base_dir)
        with open(os.path.join(output_dir, "encrypted_section.bin"), 'wb') as f:
            f.write(encrypted_data)
            
    except Exception as e:
        print(f"Error in main execution: {str(e)}")

if __name__ == "__main__":
    main()