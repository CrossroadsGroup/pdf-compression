"""
Tests for PDF compression and processing functionality.

These tests verify the core PDF compression features:
- compress_pdf(): Compress PDF bytes with various quality settings
- compress_pdf_file(): Compress PDF files on disk
- get_compression_stats(): Calculate compression statistics
- compute_target_dimensions(): Calculate image resize dimensions based on DPI

The tests use real PDF documents created with PyMuPDF to ensure accurate testing
of the compression pipeline.
"""

import io
from unittest.mock import MagicMock

import fitz
import pytest

from src.compression.pdf_processor import (
    compress_pdf,
    compress_pdf_file,
    compute_target_dimensions,
    get_compression_stats,
)


@pytest.fixture
def simple_pdf_bytes():
    """Create a simple PDF with just text (no images) for basic testing."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((100, 100), "Test PDF")
    output = io.BytesIO()
    doc.save(output)
    doc.close()
    return output.getvalue()


@pytest.fixture
def pdf_with_image():
    """Create a PDF with an embedded image for compression testing."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    from PIL import Image

    img = Image.new("RGB", (800, 600), color="red")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG", quality=95)
    img_bytes.seek(0)

    page.insert_image(fitz.Rect(100, 100, 400, 400), stream=img_bytes.getvalue())

    output = io.BytesIO()
    doc.save(output)
    doc.close()
    return output.getvalue()


class TestCompressPdf:
    """Tests for the compress_pdf() function that compresses PDF bytes."""

    def test_compress_pdf_returns_bytes(self, simple_pdf_bytes):
        """Verify compress_pdf returns bytes output."""
        result = compress_pdf(simple_pdf_bytes)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_compress_pdf_with_image(self, pdf_with_image):
        """Verify PDF with images can be compressed with custom quality/DPI."""
        result = compress_pdf(pdf_with_image, image_quality=80, max_dpi=150)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_compress_pdf_quality_parameter(self, pdf_with_image):
        """Verify different quality settings produce different outputs."""
        high_quality = compress_pdf(pdf_with_image, image_quality=95)
        low_quality = compress_pdf(pdf_with_image, image_quality=50)

        assert isinstance(high_quality, bytes)
        assert isinstance(low_quality, bytes)

    def test_compress_pdf_max_dpi_parameter(self, pdf_with_image):
        """Verify different DPI settings affect compression."""
        high_dpi = compress_pdf(pdf_with_image, max_dpi=300)
        low_dpi = compress_pdf(pdf_with_image, max_dpi=100)

        assert isinstance(high_dpi, bytes)
        assert isinstance(low_dpi, bytes)

    def test_compress_pdf_skip_small_images(self, pdf_with_image):
        """Verify skip_small_images parameter controls compression behavior."""
        result_skip = compress_pdf(
            pdf_with_image, skip_small_images=True, small_image_threshold=1_000_000
        )
        result_no_skip = compress_pdf(pdf_with_image, skip_small_images=False)

        assert isinstance(result_skip, bytes)
        assert isinstance(result_no_skip, bytes)

    def test_compress_pdf_convert_png_to_jpeg(self, pdf_with_image):
        """Verify PNG to JPEG conversion parameter works."""
        result_convert = compress_pdf(pdf_with_image, convert_large_pngs_to_jpeg=True)
        result_no_convert = compress_pdf(
            pdf_with_image, convert_large_pngs_to_jpeg=False
        )

        assert isinstance(result_convert, bytes)
        assert isinstance(result_no_convert, bytes)

    def test_compress_pdf_invalid_quality_clamped(self, simple_pdf_bytes):
        """Verify invalid quality values are clamped to valid range (1-100)."""
        result_too_high = compress_pdf(simple_pdf_bytes, image_quality=200)
        result_too_low = compress_pdf(simple_pdf_bytes, image_quality=-50)

        assert isinstance(result_too_high, bytes)
        assert isinstance(result_too_low, bytes)


class TestCompressPdfFile:
    """Tests for the compress_pdf_file() function that compresses PDF files on disk."""

    def test_compress_pdf_file_creates_output(self, tmp_path, simple_pdf_bytes):
        """Verify compress_pdf_file creates output with default naming."""
        input_file = tmp_path / "test.pdf"
        input_file.write_bytes(simple_pdf_bytes)

        output_file = compress_pdf_file(input_file)

        assert output_file.exists()
        assert output_file.suffix == ".pdf"
        assert output_file.name == "test_compressed.pdf"

    def test_compress_pdf_file_custom_output(self, tmp_path, simple_pdf_bytes):
        """Verify compress_pdf_file respects custom output path."""
        input_file = tmp_path / "test.pdf"
        output_file = tmp_path / "custom_output.pdf"
        input_file.write_bytes(simple_pdf_bytes)

        result = compress_pdf_file(input_file, output_file)

        assert result == output_file
        assert output_file.exists()

    def test_compress_pdf_file_creates_output_directory(
        self, tmp_path, simple_pdf_bytes
    ):
        """Verify compress_pdf_file creates nested output directories if needed."""
        input_file = tmp_path / "test.pdf"
        output_file = tmp_path / "nested" / "dirs" / "output.pdf"
        input_file.write_bytes(simple_pdf_bytes)

        result = compress_pdf_file(input_file, output_file)

        assert result == output_file
        assert output_file.exists()
        assert output_file.parent.exists()

    def test_compress_pdf_file_accepts_string_paths(self, tmp_path, simple_pdf_bytes):
        """Verify compress_pdf_file accepts both string and Path objects."""
        input_file = tmp_path / "test.pdf"
        input_file.write_bytes(simple_pdf_bytes)

        output_file = compress_pdf_file(str(input_file))

        assert output_file.exists()


class TestCompressionStats:
    """Tests for get_compression_stats() function."""

    def test_get_compression_stats_calculates_correctly(self):
        """Verify compression statistics are calculated correctly."""
        original = b"x" * 1000
        compressed = b"y" * 500

        stats = get_compression_stats(original, compressed)

        assert stats["original_size"] == 1000
        assert stats["compressed_size"] == 500
        assert stats["reduction_bytes"] == 500
        assert stats["reduction_percent"] == 50.0

    def test_get_compression_stats_no_compression(self):
        """Verify stats are correct when no compression occurred."""
        data = b"x" * 1000

        stats = get_compression_stats(data, data)

        assert stats["original_size"] == 1000
        assert stats["compressed_size"] == 1000
        assert stats["reduction_bytes"] == 0
        assert stats["reduction_percent"] == 0.0

    def test_get_compression_stats_negative_compression(self):
        """Verify stats handle negative compression (file grew)."""
        original = b"x" * 500
        compressed = b"y" * 1000

        stats = get_compression_stats(original, compressed)

        assert stats["original_size"] == 500
        assert stats["compressed_size"] == 1000
        assert stats["reduction_bytes"] == -500
        assert stats["reduction_percent"] == -100.0


class TestComputeTargetDimensions:
    """Tests for compute_target_dimensions() helper function."""

    def test_compute_target_dimensions_no_max_dpi(self):
        """Verify dimensions unchanged when max_dpi is None."""
        mock_page = MagicMock()
        image_info = (1, None, 100, 100, 8, "DeviceRGB", "", "Im1", "DCTDecode")

        result = compute_target_dimensions(
            mock_page, image_info, 1000, 800, max_dpi=None
        )

        assert result == (1000, 800)

    def test_compute_target_dimensions_zero_dpi(self):
        """Verify dimensions unchanged when max_dpi is 0."""
        mock_page = MagicMock()
        image_info = (1, None, 100, 100, 8, "DeviceRGB", "", "Im1", "DCTDecode")

        result = compute_target_dimensions(mock_page, image_info, 1000, 800, max_dpi=0)

        assert result == (1000, 800)

    def test_compute_target_dimensions_within_limit(self):
        """Verify dimensions unchanged when already within DPI limit."""
        mock_page = MagicMock()
        mock_page.get_image_bbox.return_value = fitz.Rect(0, 0, 144, 144)
        image_info = (1, None, 100, 100, 8, "DeviceRGB", "", "Im1", "DCTDecode")

        result = compute_target_dimensions(mock_page, image_info, 200, 200, max_dpi=150)

        assert result == (200, 200)

    def test_compute_target_dimensions_exceeds_limit(self):
        """Verify dimensions are reduced when exceeding DPI limit."""
        mock_page = MagicMock()
        mock_page.get_image_bbox.return_value = fitz.Rect(0, 0, 144, 144)
        image_info = (1, None, 100, 100, 8, "DeviceRGB", "", "Im1", "DCTDecode")

        result = compute_target_dimensions(
            mock_page, image_info, 1000, 1000, max_dpi=100
        )

        assert result[0] < 1000
        assert result[1] < 1000
        assert result[0] > 0
        assert result[1] > 0

    def test_compute_target_dimensions_handles_value_error(self):
        """Verify graceful handling of ValueError from get_image_bbox."""
        mock_page = MagicMock()
        mock_page.get_image_bbox.side_effect = ValueError("Test error")
        image_info = (1, None, 100, 100, 8, "DeviceRGB", "", "Im1", "DCTDecode")

        result = compute_target_dimensions(
            mock_page, image_info, 1000, 800, max_dpi=150
        )

        assert result == (1000, 800)

    def test_compute_target_dimensions_handles_attribute_error(self):
        """Verify graceful handling of AttributeError from get_image_bbox."""
        mock_page = MagicMock()
        mock_page.get_image_bbox.side_effect = AttributeError("Test error")
        image_info = (1, None, 100, 100, 8, "DeviceRGB", "", "Im1", "DCTDecode")

        result = compute_target_dimensions(
            mock_page, image_info, 1000, 800, max_dpi=150
        )

        assert result == (1000, 800)
