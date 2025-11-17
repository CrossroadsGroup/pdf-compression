"""Image optimization utilities for PDF compression."""

from __future__ import annotations

import hashlib
import io
import logging
from dataclasses import dataclass
from typing import Any, cast

import pyvips
from PIL import Image, ImageFile

logger = logging.getLogger(__name__)

ImageFile.LOAD_TRUNCATED_IMAGES = True
# Allow processing of large legitimate PDF images
# This tool is designed for users to process their own trusted files
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

    img = pyvips.Image.new_from_buffer(image_bytes, "")

    needs_resize = (target_width, target_height) != (original_width, original_height)

    if needs_resize:
        hscale = target_width / original_width
        vscale = target_height / original_height
        img = img.resize(hscale, vscale=vscale, kernel="lanczos3")

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
        if img.interpretation != "srgb" and img.interpretation != "b-w":
            img = img.colourspace("srgb")
        return img.write_to_buffer(
            ".jpg",
            Q=image_quality,
            optimize_coding=False,
            strip=True,
            interlace=False,
            subsample_mode="off",
        )
    elif save_format == "png":
        return img.write_to_buffer(".png", compression=6)
    else:
        return img.write_to_buffer(f".{save_format}")


def _optimize_image_with_pil(
    doc,
    page,
    image_info: tuple,
    image_quality: int,
    max_dpi: int | None,
    skip_small_images: bool,
    small_image_threshold: int,
    convert_large_pngs_to_jpeg: bool,
    png_to_jpeg_threshold: int,
    cache: dict[bytes, ImageOptimizationResult],
    compute_target_dimensions_fn,
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
    target_width, target_height = compute_target_dimensions_fn(
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


def optimize_image(
    doc,
    page,
    image_info: tuple,
    image_quality: int,
    max_dpi: int | None,
    skip_small_images: bool,
    small_image_threshold: int,
    convert_large_pngs_to_jpeg: bool,
    png_to_jpeg_threshold: int,
    cache: dict[bytes, ImageOptimizationResult],
    compute_target_dimensions_fn,
) -> tuple[bool, int, int]:
    """Optimize a single image, trying pyvips first then falling back to PIL."""
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
    target_width, target_height = compute_target_dimensions_fn(
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
        compute_target_dimensions_fn,
    )
