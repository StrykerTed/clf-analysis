"""PDF assembly utilities (placed inside src/utils so 'from utils.pdf_things import build_pdf_report' works).

Uses matplotlib.backends.backend_pdf.PdfPages (already available via matplotlib) so no extra
packages are required. If matplotlib is missing, report generation gracefully skips.
"""
from __future__ import annotations
import os
from typing import Iterable, List, Optional

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt  # type: ignore
    from matplotlib.backends.backend_pdf import PdfPages  # type: ignore
    MATPLOTLIB_OK = True
except Exception:  # pragma: no cover - fallback if matplotlib not present
    MATPLOTLIB_OK = False


def _gather_images(directory: str, patterns: Optional[Iterable[str]] = None) -> List[str]:
    if not os.path.isdir(directory):
        return []
    patterns_l = [p.lower() for p in patterns] if patterns else None
    images: List[str] = []
    for root, _dirs, files in os.walk(directory):
        for name in sorted(files):
            if not name.lower().endswith('.png'):
                continue
            if patterns_l and not any(pat in name.lower() for pat in patterns_l):
                continue
            images.append(os.path.join(root, name))
    # Stable order: sort by path
    images.sort()
    return images


def build_pdf_report(output_dir: str, pdf_name: str = 'paths_holes_report.pdf',
                     include_patterns: Optional[Iterable[str]] = None,
                     include_summary: bool = True) -> Optional[str]:
    """Create multi-page PDF with each PNG (filtered) plus optional summary text.

    Parameters:
        output_dir: directory containing analysis PNGs / summary text
        pdf_name: output PDF filename
        include_patterns: iterable of substrings to filter PNG names (case-insensitive)
        include_summary: append summary_*.txt content pages if found
    Returns path to created PDF or None if skipped.
    """
    if not MATPLOTLIB_OK:
        print("PDF generation skipped: matplotlib not available")
        return None

    images = _gather_images(output_dir, include_patterns)
    if not images:
        print("PDF generation: no PNG images found.")
        return None

    pdf_path = os.path.join(output_dir, pdf_name)
    with PdfPages(pdf_path) as pdf:
        for img in images:
            fig = plt.figure(figsize=(8.5, 8.5))
            ax = fig.add_subplot(111)
            ax.axis('off')
            ax.imshow(plt.imread(img))
            ax.set_title(os.path.basename(img), fontsize=9)
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)
        # Append summary text pages
        if include_summary:
            summary_path = None
            for name in sorted(os.listdir(output_dir)):
                if name.startswith('summary_') and name.endswith('.txt'):
                    summary_path = os.path.join(output_dir, name)
                    break
            if summary_path and os.path.isfile(summary_path):
                with open(summary_path, 'r') as f:
                    lines = f.read().splitlines()
                chunk = 58
                for i in range(0, len(lines), chunk):
                    piece = lines[i:i+chunk]
                    fig = plt.figure(figsize=(8.5, 11))
                    ax = fig.add_subplot(111)
                    ax.axis('off')
                    ax.text(0.02, 0.98, '\n'.join(piece), ha='left', va='top', fontsize=8, family='monospace')
                    ax.set_title(os.path.basename(summary_path), fontsize=10)
                    pdf.savefig(fig, bbox_inches='tight')
                    plt.close(fig)
    print(f"Created PDF report: {pdf_path}")
    return pdf_path
