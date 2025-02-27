# Import functions to make them available at the package level
from .file_utils import create_output_folder, find_clf_files, load_exclusion_patterns, should_skip_folder
from .shape_things import should_close_path
from .print_utils import add_platform_labels, print_analysis_summary, print_identifier_summary, create_unclosed_shapes_view
from .plotTools import (
    setup_standard_platform_view, 
    setup_platform_figure,
    draw_platform_boundary,
    add_reference_lines,
    set_platform_limits,
    draw_shape,
    draw_aligned_shape,
    save_platform_figure
)
from .logging_utils import setup_logging