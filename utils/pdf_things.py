"""Utilities for assembling analysis PNG outputs into a single multi-page PDF.

Relies only on matplotlib (already used in project). No new dependencies are introduced.
"""
from __future__ import annotations
import os
from typing import Iterable, List, Optional

try:
    import matplotlib
    matplotlib.use('Agg')  # ensure non-interactive
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    MATPLOTLIB_OK = True
except Exception:
    MATPLOTLIB_OK = False


def _gather_images(directory: str, patterns: Optional[Iterable[str]] = None) -> List[str]:
    if not os.path.isdir(directory):
        return []
    imgs = []
    patterns_l = [p.lower() for p in patterns] if patterns else None
    for name in sorted(os.listdir(directory)):
        if not name.lower().endswith('.png'):
            continue
        if patterns_l and not any(p in name.lower() for p in patterns_l):
            continue
        imgs.append(os.path.join(directory, name))
    return imgs


def build_pdf_report(output_dir: str, pdf_name: str = 'paths_holes_report.pdf',
                     include_patterns: Optional[Iterable[str]] = None,
                     include_summary: bool = True) -> Optional[str]:
    """Create a multi-page PDF containing each PNG in output_dir (filtered by patterns).

    Each page is a single image scaled to fit. Optionally appends a summary text page
    if a summary_*.txt file is present and include_summary=True.
    """
    if not MATPLOTLIB_OK:
        print("PDF generation skipped (matplotlib not available).")
        return None
    images = _gather_images(output_dir, include_patterns)
    if not images:
        print("No PNGs found for PDF report.")
        return None

    pdf_path = os.path.join(output_dir, pdf_name)
    with PdfPages(pdf_path) as pdf:
        for img_path in images:
            fig = plt.figure(figsize=(8.5, 8.5))
            ax = fig.add_subplot(111)
            ax.axis('off')
            ax.imshow(plt.imread(img_path))
            ax.set_title(os.path.basename(img_path), fontsize=10)
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)
        if include_summary:
            # try to find summary txt
            summary_txt = None
            for name in sorted(os.listdir(output_dir)):
                if name.startswith('summary_') and name.endswith('.txt'):
                    summary_txt = os.path.join(output_dir, name)
                    break
            if summary_txt and os.path.isfile(summary_txt):
                with open(summary_txt, 'r') as f:
                    content = f.read()
                # chunk into pages (~60 lines per page)
                lines = content.splitlines()
                chunk_size = 60
                for i in range(0, len(lines), chunk_size):
                    chunk = lines[i:i+chunk_size]
                    fig = plt.figure(figsize=(8.5, 11))
                    ax = fig.add_subplot(111)
                    ax.axis('off')
                    ax.text(0.02, 0.98, '\n'.join(chunk), ha='left', va='top', fontsize=8, family='monospace')
                    ax.set_title(os.path.basename(summary_txt), fontsize=10)
                    pdf.savefig(fig, bbox_inches='tight')
                    plt.close(fig)
    print(f"Created PDF report: {pdf_path}")
    return pdf_path
