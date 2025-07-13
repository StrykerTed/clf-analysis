#!/bin/bash

# PDF Shape Report Generator Launcher
# This script runs the PDF shape report generator

echo "=== PDF Shape Report Generator ==="
echo "Make sure you've already run get_platform_paths_shapes_shapely.py first!"
echo ""

# Check if we're in the right directory
if [ ! -f "generate_pdf_shape_report.py" ]; then
    echo "Error: generate_pdf_shape_report.py not found!"
    echo "Please run this script from the root directory of the CLF analysis project."
    exit 1
fi

# Check if abp_contents directory exists
if [ ! -d "abp_contents" ]; then
    echo "Error: abp_contents directory not found!"
    echo "Please run get_platform_paths_shapes_shapely.py first to extract ABP files."
    exit 1
fi

# Run the Python script
python3 generate_pdf_shape_report.py

echo ""
echo "PDF generation complete!"
