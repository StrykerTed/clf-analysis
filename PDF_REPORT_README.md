# PDF Shape Report Generator

This tool generates comprehensive PDF reports showing shapes from CLF files organized by folder.

## Prerequisites

1. **Run the main analysis first**: You must run `get_platform_paths_shapes_shapely.py` first to extract and process the ABP files.
2. **Know your build ID**: You'll need the build ID from your ABP file (e.g., if your file is `preprocess build-430848.abp`, the build ID is `430848`).

## Usage

### Option 1: Using the Shell Script (Recommended)

```bash
./generate_pdf_report.sh
```

### Option 2: Direct Python Execution

```bash
python3 generate_pdf_shape_report.py
```

## Interactive Prompts

The program will ask you for:

1. **Build ID**: Enter the numeric build ID (e.g., `430848`)

   - The program will verify that the corresponding folder exists in `abp_contents/`
   - Shows available folders if the entered ID is not found

2. **Height**: Enter the height in millimeters (e.g., `136.55`)
   - This is the layer height at which to extract and display shapes

## Output

The program generates a PDF file named:

```
shape_report_build_{BUILD_ID}_{HEIGHT}mm_{TIMESTAMP}.pdf
```

For example: `shape_report_build_430848_136.55mm_20250707_143052.pdf`

## PDF Content

### Summary Page

- Build information
- Analysis statistics
- Processing timestamp
- Overview of folders and shapes found

### Folder Pages

Each folder gets its own page showing:

- **Platform view** with standard boundaries and reference lines
- **All shapes** from CLF files in that folder at the specified height
- **Color-coded files** - each CLF file gets a unique color
- **Legend** showing which colors represent which files
- **Statistics** showing file counts and shape counts

## Features

- **Platform-accurate visualization**: Uses the same coordinate system and boundaries as the main analysis
- **Shape type support**: Handles paths, lines, points, and circles
- **Identifier tracking**: Preserves shape identifiers from the CLF files
- **Error handling**: Gracefully handles missing files or corrupted data
- **Progress tracking**: Shows progress as pages are generated

## Example Workflow

1. **Extract and analyze ABP file**:

   ```bash
   python3 src/tools/get_platform_paths_shapes_shapely.py
   ```

2. **Generate PDF report**:

   ```bash
   ./generate_pdf_report.sh
   ```

   - Enter build ID: `430848`
   - Enter height: `136.55`

3. **View the generated PDF** to see all shapes organized by folder

## Technical Details

- **Coordinate system**: Uses the same -125 to +125 mm platform coordinates
- **Shape rendering**: Preserves original shape geometry and closure properties
- **File organization**: Automatically scans all folders in the build directory
- **Memory efficient**: Processes one folder at a time to handle large datasets

## Troubleshooting

### "Folder not found" error

- Make sure you've run the main analysis first
- Check that the build ID matches your ABP file name
- Verify the `abp_contents/` directory exists

### "No CLF files found" error

- The build directory exists but contains no CLF files
- Check if the ABP extraction completed successfully

### Import errors

- Make sure you're running from the root directory of the project
- Verify all dependencies are installed: `pip install -r requirements.txt`

## File Structure

```
clf_analysis_clean/
├── generate_pdf_shape_report.py    # Main PDF generator
├── generate_pdf_report.sh          # Launch script
├── abp_contents/                   # Extracted ABP data
│   └── preprocess build-{ID}/      # Build-specific folders
└── shape_report_build_*.pdf        # Generated reports
```
