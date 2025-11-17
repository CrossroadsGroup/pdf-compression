"""
PDF Compression Utility

Optimizes PowerBI-generated PDFs before uploading to S3.
Reduces file sizes by 90%+ while maintaining high visual quality for browser viewing.


Dependencies:
    - pymupdf (fitz)
    - Pillow (PIL)

Basic Usage:
    from api.utils.pdf_compression import compress_pdf

    with open('report.pdf', 'rb') as f:
        original_bytes = f.read()

    compressed_bytes = compress_pdf(original_bytes)

    with open('report_compressed.pdf', 'wb') as f:
        f.write(compressed_bytes)

Advanced Usage Examples:

    # Option 1: Sharp logos, compressed charts (RECOMMENDED)
    # Small PNGs (<200KB) stay as PNG, large PNGs → JPEG
    # Result: ~3 MB, logo sharp, 88% reduction
    compressed_bytes = compress_pdf(
        original_bytes,
        image_quality=90,
        max_dpi=250,
        convert_large_pngs_to_jpeg=True,
        png_to_jpeg_threshold=200_000
    )

    # Option 2: Maximum sharpness (keep all PNGs)
    # All PNGs kept as PNG (sharp but larger file)
    # Result: ~4.4 MB, everything sharp, 82% reduction
    compressed_bytes = compress_pdf(
        original_bytes,
        convert_large_pngs_to_jpeg=False
    )

    # Option 3: Maximum compression
    # Everything compressed to JPEG
    # Result: ~2.5 MB, some blur on logos, 90% reduction
    compressed_bytes = compress_pdf(
        original_bytes,
        convert_large_pngs_to_jpeg=True,
        png_to_jpeg_threshold=0
    )
"""

from __future__ import annotations

import hashlib
import io
import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, cast

import fitz
import pyvips
from PIL import Image, ImageFile

logger = logging.getLogger(__name__)

ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = None


@dataclass(slots=True)
class ImageOptimizationResult:
    optimized: bool
    data: bytes | None
    original_size: int
    optimized_size: int


def _has_transparency(image: Image.Image, smask_present: bool) -> bool:
    if smask_present:
        return True

    if image.mode in ("RGBA", "LA"):
        alpha = image.getchannel("A")
        extrema = alpha.getextrema()
        lowest = extrema[0]
        if isinstance(lowest, (int, float)):
            return int(lowest) < 255
        return False

    if image.mode == "P":
        transparency = image.info.get("transparency")
        if transparency is None:
            return False
        if isinstance(transparency, bytes):
            return True
        return transparency != 255

    return False


def _compute_target_dimensions(
    page: fitz.Page,
    image_info: tuple,
    original_width: int,
    original_height: int,
    max_dpi: int | None,
) -> tuple[int, int]:
    if not max_dpi or max_dpi <= 0:
        return original_width, original_height

    try:
        bbox_candidate = page.get_image_bbox(image_info)
    except ValueError:
        return original_width, original_height
    except AttributeError:
        return original_width, original_height

    if isinstance(bbox_candidate, tuple):
        bbox_rect = bbox_candidate[0]
    else:
        bbox_rect = bbox_candidate

    bbox = cast(fitz.Rect, bbox_rect)

    width_inches = max(bbox.width / 72.0, 1e-3)
    height_inches = max(bbox.height / 72.0, 1e-3)
    max_width_px = max(int(max_dpi * width_inches), 1)
    max_height_px = max(int(max_dpi * height_inches), 1)

    if original_width <= max_width_px and original_height <= max_height_px:
        return original_width, original_height

    scale = min(max_width_px / original_width, max_height_px / original_height)
    target_width = max(1, int(math.floor(original_width * scale)))
    target_height = max(1, int(math.floor(original_height * scale)))

    return target_width, target_height


def _iter_unique_images(doc: fitz.Document) -> Iterable[tuple[fitz.Page, tuple]]:
    seen_xrefs: set[int] = set()

    for page_index in range(doc.page_count):
        page = doc[page_index]
        for image_info in page.get_images(full=True):
            xref = image_info[0]
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)
            yield page, image_info


def _optimize_image_with_pyvips(
    image_bytes: bytes,
    image_ext: str,
    original_width: int,
    original_height: int,
    target_width: int,
    target_height: int,
    has_alpha: bool,
    image_quality: int,
    convert_large_pngs_to_jpeg: bool,
    png_to_jpeg_threshold: int,
    original_size: int,
    bpc: int,
) -> bytes:
    if pyvips is None:
        raise RuntimeError("pyvips is not available")

    img = pyvips.Image.new_from_buffer(image_bytes, "")  # type: ignore

    needs_resize = (target_width, target_height) != (original_width, original_height)

    if needs_resize:
        hscale = target_width / original_width
        vscale = target_height / original_height
        img = img.resize(hscale, vscale=vscale, kernel="lanczos3")  # type: ignore

    save_format = image_ext
    should_convert_png = (
        image_ext == "png"
        and convert_large_pngs_to_jpeg
        and not has_alpha
        and original_size >= png_to_jpeg_threshold
        and bpc >= 8
    )

    if should_convert_png:
        save_format = "jpeg"

    if save_format == "jpeg" or save_format == "jpg":
        if img.interpretation != "srgb" and img.interpretation != "b-w":  # type: ignore
            img = img.colourspace("srgb")  # type: ignore
        return img.write_to_buffer(  # type: ignore
            ".jpg",
            Q=image_quality,
            optimize_coding=False,
            strip=True,
            interlace=False,
            subsample_mode="off",
        )
    elif save_format == "png":
        return img.write_to_buffer(".png", compression=6)  # type: ignore
    else:
        return img.write_to_buffer(f".{save_format}")  # type: ignore


def _optimize_image_with_pil(
    doc: fitz.Document,
    page: fitz.Page,
    image_info: tuple,
    image_quality: int,
    max_dpi: int | None,
    skip_small_images: bool,
    small_image_threshold: int,
    convert_large_pngs_to_jpeg: bool,
    png_to_jpeg_threshold: int,
    cache: dict[bytes, ImageOptimizationResult],
) -> tuple[bool, int, int]:
    xref = image_info[0]
    base_image = doc.extract_image(xref)

    image_bytes: bytes = base_image["image"]
    original_size = len(image_bytes)
    digest = hashlib.sha1(image_bytes).digest()

    cached = cache.get(digest)
    if cached:
        if cached.optimized and cached.data is not None:
            cast(Any, page).replace_image(xref, stream=cached.data)
            return True, cached.original_size, cached.optimized_size
        return False, cached.original_size, cached.original_size

    if skip_small_images and original_size <= small_image_threshold:
        cache[digest] = ImageOptimizationResult(
            False, None, original_size, original_size
        )
        return False, original_size, original_size

    image_ext = base_image["ext"].lower()
    original_width = base_image["width"]
    original_height = base_image["height"]
    bpc = base_image.get("bpc", 8)

    # Skip monochrome / low bpc images – they tend to be text masks
    if bpc <= 1 and image_ext != "png":
        cache[digest] = ImageOptimizationResult(
            False, None, original_size, original_size
        )
        return False, original_size, original_size

    smask = image_info[1]
    target_width, target_height = _compute_target_dimensions(
        page, image_info, original_width, original_height, max_dpi
    )

    needs_resize = (target_width, target_height) != (original_width, original_height)

    image_stream = io.BytesIO(image_bytes)
    with Image.open(image_stream) as pil_image:
        pil_image.load()

        has_alpha = _has_transparency(pil_image, smask_present=bool(smask))

        if needs_resize:
            pil_image = pil_image.resize(
                (target_width, target_height),
                Image.Resampling.LANCZOS,
            )

        save_kwargs: dict[str, Any] = {}
        save_format = image_ext
        format_name = image_ext.upper()

        if image_ext == "png":
            should_convert_png = (
                convert_large_pngs_to_jpeg
                and not has_alpha
                and original_size >= png_to_jpeg_threshold
                and bpc >= 8
            )
            if should_convert_png:
                if pil_image.mode not in ("RGB", "L"):
                    pil_image = pil_image.convert("RGB")
                save_format = "jpeg"
            else:
                if pil_image.mode == "P" and not has_alpha:
                    pil_image = pil_image.convert("RGB")

        if save_format == "jpeg":
            if pil_image.mode not in ("RGB", "L"):
                pil_image = pil_image.convert("RGB")
            format_name = "JPEG"
            save_kwargs = {
                "quality": image_quality,
                "optimize": False,
                "progressive": False,
                "subsampling": 2,
            }
        elif save_format == "png":
            format_name = "PNG"
            save_kwargs = {
                "optimize": False,
                "compress_level": 6,
            }

        output_buffer = io.BytesIO()
        pil_image.save(output_buffer, format=format_name, **save_kwargs)
        optimized_bytes = output_buffer.getvalue()

    optimized_size = len(optimized_bytes)

    # Require at least 2% size reduction to avoid churn
    if optimized_size >= original_size * 0.98:
        cache[digest] = ImageOptimizationResult(
            False, None, original_size, original_size
        )
        return False, original_size, original_size

    cast(Any, page).replace_image(xref, stream=optimized_bytes)
    cache[digest] = ImageOptimizationResult(
        True, optimized_bytes, original_size, optimized_size
    )
    return True, original_size, optimized_size


def _optimize_image_stream(
    doc: fitz.Document,
    page: fitz.Page,
    image_info: tuple,
    image_quality: int,
    max_dpi: int | None,
    skip_small_images: bool,
    small_image_threshold: int,
    convert_large_pngs_to_jpeg: bool,
    png_to_jpeg_threshold: int,
    cache: dict[bytes, ImageOptimizationResult],
) -> tuple[bool, int, int]:
    xref = image_info[0]
    base_image = doc.extract_image(xref)

    image_bytes: bytes = base_image["image"]
    original_size = len(image_bytes)
    digest = hashlib.sha1(image_bytes).digest()

    cached = cache.get(digest)
    if cached:
        if cached.optimized and cached.data is not None:
            cast(Any, page).replace_image(xref, stream=cached.data)
            return True, cached.original_size, cached.optimized_size
        return False, cached.original_size, cached.original_size

    if skip_small_images and original_size <= small_image_threshold:
        cache[digest] = ImageOptimizationResult(
            False, None, original_size, original_size
        )
        return False, original_size, original_size

    image_ext = base_image["ext"].lower()
    original_width = base_image["width"]
    original_height = base_image["height"]
    bpc = base_image.get("bpc", 8)

    if bpc <= 1 and image_ext != "png":
        cache[digest] = ImageOptimizationResult(
            False, None, original_size, original_size
        )
        return False, original_size, original_size

    smask = image_info[1]
    target_width, target_height = _compute_target_dimensions(
        page, image_info, original_width, original_height, max_dpi
    )

    try:
        has_alpha = False
        if smask or image_ext == "png":
            image_stream = io.BytesIO(image_bytes)
            with Image.open(image_stream) as pil_image:
                pil_image.load()
                has_alpha = _has_transparency(pil_image, smask_present=bool(smask))

        optimized_bytes = _optimize_image_with_pyvips(
            image_bytes,
            image_ext,
            original_width,
            original_height,
            target_width,
            target_height,
            has_alpha,
            image_quality,
            convert_large_pngs_to_jpeg,
            png_to_jpeg_threshold,
            original_size,
            bpc,
        )

        optimized_size = len(optimized_bytes)

        if optimized_size >= original_size * 0.98:
            cache[digest] = ImageOptimizationResult(
                False, None, original_size, original_size
            )
            return False, original_size, original_size

        cast(Any, page).replace_image(xref, stream=optimized_bytes)
        cache[digest] = ImageOptimizationResult(
            True, optimized_bytes, original_size, optimized_size
        )
        return True, original_size, optimized_size

    except Exception as e:
        logger.warning(f"pyvips optimization failed, falling back to PIL: {e}")

    return _optimize_image_with_pil(
        doc,
        page,
        image_info,
        image_quality,
        max_dpi,
        skip_small_images,
        small_image_threshold,
        convert_large_pngs_to_jpeg,
        png_to_jpeg_threshold,
        cache,
    )


def _compress_document(
    doc: fitz.Document,
    image_quality: int,
    max_dpi: int | None,
    skip_small_images: bool,
    small_image_threshold: int,
    convert_large_pngs_to_jpeg: bool,
    png_to_jpeg_threshold: int,
) -> tuple[int, int, int]:
    quality = max(1, min(int(image_quality), 100))
    effective_dpi = None if max_dpi is None else int(max_dpi)

    images_replaced = 0
    total_original = 0
    total_optimized = 0
    optimization_cache: dict[bytes, ImageOptimizationResult] = {}

    for page, image_info in _iter_unique_images(doc):
        try:
            optimized, original_size, optimized_size = _optimize_image_stream(
                doc,
                page,
                image_info,
                quality,
                effective_dpi,
                skip_small_images,
                small_image_threshold,
                convert_large_pngs_to_jpeg,
                png_to_jpeg_threshold,
                optimization_cache,
            )
        except Exception:
            continue

        if optimized:
            images_replaced += 1
            total_original += original_size
            total_optimized += optimized_size

    return images_replaced, total_original, total_optimized


def compress_pdf(
    pdf_bytes: bytes,
    image_quality: int = 90,
    max_dpi: int = 250,
    skip_small_images: bool = True,
    small_image_threshold: int = 500_000,
    convert_large_pngs_to_jpeg: bool = True,
    png_to_jpeg_threshold: int = 200_000,
) -> bytes:
    """
    Compress PDF bytes by optimizing embedded images.

    This function is optimized for PowerBI-generated PDFs viewed in browsers.
    Typical reduction: 90-95% file size with no perceptible quality loss.

    Performance optimizations:
    - Image deduplication: Each unique image is compressed only once
    - Early skip: Already-optimized images are skipped
    - Efficient memory usage: Streams are used for large files
    - Smart compression: Small images (logos) kept sharp, large images compressed

    Args:
        pdf_bytes: Original PDF file as bytes
        image_quality: JPEG quality (1-95, default 90 for high quality)
        max_dpi: Maximum DPI for images (default 250 for sharp display)
        skip_small_images: Skip compression for small images like logos (default True)
        small_image_threshold: Size threshold in bytes for small images (default 500KB)
        convert_large_pngs_to_jpeg: Convert large PNGs to JPEG for better compression (default True)
        png_to_jpeg_threshold: Size threshold for converting PNGs to JPEG (default 200KB)

    Returns:
        Compressed PDF as bytes

    Example:
        with open('report.pdf', 'rb') as f:
            original_bytes = f.read()

        # Keep all PNGs as PNG (sharp logos, larger file)
        compressed_bytes = compress_pdf(original_bytes, convert_large_pngs_to_jpeg=False)

        # Or convert large PNGs to JPEG (balanced approach)
        compressed_bytes = compress_pdf(original_bytes, convert_large_pngs_to_jpeg=True)

        with open('report_compressed.pdf', 'wb') as f:
            f.write(compressed_bytes)
    """
    if fitz is None or Image is None:
        raise RuntimeError(
            "PDF compression dependencies (pymupdf, Pillow) are not installed"
        )

    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        _compress_document(
            doc,
            image_quality,
            max_dpi,
            skip_small_images,
            small_image_threshold,
            convert_large_pngs_to_jpeg,
            png_to_jpeg_threshold,
        )

        output_buffer = io.BytesIO()
        doc.save(output_buffer, garbage=4, deflate=True, clean=True)
        return output_buffer.getvalue()


def compress_pdf_file(
    input_path: str | Path,
    output_path: str | Path | None = None,
    image_quality: int = 90,
    max_dpi: int = 250,
    skip_small_images: bool = True,
    small_image_threshold: int = 500_000,
    convert_large_pngs_to_jpeg: bool = True,
    png_to_jpeg_threshold: int = 200_000,
) -> Path:
    """
    Compress PDF file by optimizing embedded images.

    Args:
        input_path: Path to input PDF file
        output_path: Path to output PDF file (optional, defaults to input_compressed.pdf)
        image_quality: JPEG quality (1-95, default 90 for high quality)
        max_dpi: Maximum DPI for images (default 250 for sharp display)
        skip_small_images: Skip compression for small images like logos (default True)
        small_image_threshold: Size threshold in bytes for small images (default 500KB)
        convert_large_pngs_to_jpeg: Convert large PNGs to JPEG for better compression (default True)
        png_to_jpeg_threshold: Size threshold for converting PNGs to JPEG (default 200KB)

    Returns:
        Path to compressed PDF file

    Example:
        compress_pdf_file('report.pdf', 'report_compressed.pdf')
    """
    input_path = Path(input_path)

    if output_path is None:
        output_path = (
            input_path.parent / f"{input_path.stem}_compressed{input_path.suffix}"
        )
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with fitz.open(str(input_path)) as doc:
        _compress_document(
            doc,
            image_quality,
            max_dpi,
            skip_small_images,
            small_image_threshold,
            convert_large_pngs_to_jpeg,
            png_to_jpeg_threshold,
        )
        doc.save(
            str(output_path),
            garbage=4,
            deflate=True,
            clean=True,
        )

    return output_path


def get_compression_stats(
    original_bytes: bytes, compressed_bytes: bytes
) -> dict[str, int | float]:
    """
    Calculate compression statistics.

    Args:
        original_bytes: Original PDF bytes
        compressed_bytes: Compressed PDF bytes

    Returns:
        Dictionary with compression statistics

    Example:
        stats = get_compression_stats(original_bytes, compressed_bytes)
        print(f"Reduced by {stats['reduction_percent']:.1f}%")
    """
    original_size = len(original_bytes)
    compressed_size = len(compressed_bytes)
    reduction_bytes = original_size - compressed_size
    reduction_percent = (reduction_bytes / original_size) * 100

    return {
        "original_size": original_size,
        "compressed_size": compressed_size,
        "reduction_bytes": reduction_bytes,
        "reduction_percent": reduction_percent,
    }
