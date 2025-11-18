"""
Tests for image optimization and transparency detection.

These tests verify:
- has_transparency(): Correctly detects transparency in various image formats
- ImageOptimizationResult: Data structure for optimization results
- Image format handling (JPEG, PNG, etc.)

The tests use PIL to create real image data and verify the optimization logic
works correctly with different image modes and formats.
"""

import io

from PIL import Image

from src.compression.image_optimizer import (
    ImageOptimizationResult,
    has_transparency,
)


class TestHasTransparency:
    """Tests for the _has_transparency() function."""

    def test_rgba_with_full_alpha(self):
        """Verify RGBA image with full alpha (255) is not considered transparent."""
        img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
        assert not has_transparency(img, smask_present=False)

    def test_rgba_with_partial_alpha(self):
        """Verify RGBA image with partial alpha (128) is detected as transparent."""
        img = Image.new("RGBA", (100, 100), (255, 0, 0, 128))
        assert has_transparency(img, smask_present=False)

    def test_rgba_with_zero_alpha(self):
        """Verify RGBA image with zero alpha (fully transparent) is detected."""
        img = Image.new("RGBA", (100, 100), (255, 0, 0, 0))
        assert has_transparency(img, smask_present=False)

    def test_rgb_no_transparency(self):
        """Verify RGB images (no alpha channel) are not transparent."""
        img = Image.new("RGB", (100, 100), (255, 0, 0))
        assert not has_transparency(img, smask_present=False)

    def test_la_with_full_alpha(self):
        """Verify grayscale+alpha (LA) with full alpha is not transparent."""
        img = Image.new("LA", (100, 100), (255, 255))
        assert not has_transparency(img, smask_present=False)

    def test_la_with_partial_alpha(self):
        """Verify grayscale+alpha (LA) with partial alpha is detected as transparent."""
        img = Image.new("LA", (100, 100), (255, 128))
        assert has_transparency(img, smask_present=False)

    def test_p_mode_no_transparency(self):
        """Verify palette mode (P) without transparency info is not transparent."""
        img = Image.new("P", (100, 100))
        assert not has_transparency(img, smask_present=False)

    def test_p_mode_with_transparency_bytes(self):
        """Verify palette mode (P) with transparency bytes is detected."""
        img = Image.new("P", (100, 100))
        img.info["transparency"] = b"\x00\x01\x02"
        assert has_transparency(img, smask_present=False)

    def test_p_mode_with_transparency_int_not_255(self):
        """Verify palette mode (P) with transparency index (not 255) is detected."""
        img = Image.new("P", (100, 100))
        img.info["transparency"] = 0
        assert has_transparency(img, smask_present=False)

    def test_p_mode_with_transparency_int_255(self):
        """Verify palette mode (P) with transparency=255 is not transparent."""
        img = Image.new("P", (100, 100))
        img.info["transparency"] = 255
        assert not has_transparency(img, smask_present=False)

    def test_smask_present_overrides(self):
        """Verify smask_present=True overrides image transparency detection."""
        img = Image.new("RGB", (100, 100), (255, 0, 0))
        assert has_transparency(img, smask_present=True)

    def test_smask_false_checks_image(self):
        """Verify smask_present=False causes actual image transparency check."""
        img = Image.new("RGBA", (100, 100), (255, 0, 0, 128))
        assert has_transparency(img, smask_present=False)


class TestImageOptimizationResult:
    """Tests for ImageOptimizationResult dataclass."""

    def test_create_optimized_result(self):
        """Verify optimized result stores all required fields."""
        result = ImageOptimizationResult(
            optimized=True,
            data=b"compressed_data",
            original_size=1000,
            optimized_size=500,
        )

        assert result.optimized is True
        assert result.data == b"compressed_data"
        assert result.original_size == 1000
        assert result.optimized_size == 500

    def test_create_unoptimized_result(self):
        """Verify unoptimized result (no compression) stores correctly."""
        result = ImageOptimizationResult(
            optimized=False, data=None, original_size=1000, optimized_size=1000
        )

        assert result.optimized is False
        assert result.data is None
        assert result.original_size == 1000
        assert result.optimized_size == 1000


class TestImageOptimizationIntegration:
    """Integration tests verifying image format handling with real image data."""

    def test_jpeg_image_bytes(self):
        """Verify JPEG images are created correctly with proper magic bytes."""
        img = Image.new("RGB", (800, 600), color="blue")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG", quality=95)
        img_data = img_bytes.getvalue()

        assert len(img_data) > 0
        assert img_data[:2] == b"\xff\xd8"

    def test_png_image_bytes(self):
        """Verify PNG images are created correctly with proper magic bytes."""
        img = Image.new("RGB", (800, 600), color="green")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_data = img_bytes.getvalue()

        assert len(img_data) > 0
        assert img_data[:8] == b"\x89PNG\r\n\x1a\n"

    def test_png_with_transparency(self):
        """Verify PNG with transparency is detected after save/load cycle."""
        img = Image.new("RGBA", (100, 100), (255, 0, 0, 128))
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.getvalue()

        img_bytes.seek(0)
        loaded = Image.open(img_bytes)
        loaded.load()

        assert has_transparency(loaded, smask_present=False)

    def test_jpeg_cannot_have_transparency(self):
        """Verify JPEG format (no alpha support) never reports transparency."""
        img = Image.new("RGB", (100, 100), (255, 0, 0))
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG", quality=90)
        img_bytes.getvalue()

        img_bytes.seek(0)
        loaded = Image.open(img_bytes)
        loaded.load()

        assert not has_transparency(loaded, smask_present=False)
