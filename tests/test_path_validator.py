"""
Tests for path validation and security restrictions.

These tests verify that the application correctly blocks access to sensitive
system directories and enforces proper folder selection by users.

The tests are platform-specific and will automatically skip on incompatible systems:
- TestPathValidatorWindows: Only runs on Windows
- TestPathValidatorMacLinux: Only runs on Mac/Linux
- TestPathValidatorCrossPlatform: Runs on all platforms

This ensures tests use real platform-specific path behavior instead of fragile mocking.
"""

import platform
from pathlib import Path

import pytest

from src.gui.path_validator import is_path_restricted


@pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only test")
class TestPathValidatorWindows:
    """
    Windows-specific path validation tests.

    These tests verify that critical Windows system paths are blocked:
    - System directories (C:\\Windows, Program Files, etc.)
    - User AppData folders
    - Drive roots (C:\\, D:\\)
    - User folder roots (Desktop, Documents, Downloads)

    The tests ensure subfolders of user directories ARE allowed to encourage
    good file organization (e.g., Downloads\\MyProject is OK, but Downloads\\ is not).
    """

    def test_system_paths_blocked(self):
        """Verify Windows system directories are completely blocked."""
        restricted_paths = [
            "C:\\Windows",
            "C:\\Windows\\System32",
            "C:\\Program Files",
            "C:\\Program Files\\SomeApp",
            "C:\\Program Files (x86)",
            "C:\\ProgramData",
            "C:\\$Recycle.Bin",
        ]

        for path in restricted_paths:
            is_restricted, message = is_path_restricted(path)
            assert is_restricted, f"Path {path} should be restricted"
            assert "System directories are not allowed" in message

    def test_appdata_blocked(self):
        """Verify AppData directories (Local, Roaming) are blocked."""
        home = Path.home()
        appdata_paths = [
            str(home / "AppData"),
            str(home / "AppData" / "Local"),
            str(home / "AppData" / "Roaming"),
        ]

        for path in appdata_paths:
            is_restricted, _message = is_path_restricted(path)
            assert is_restricted, f"Path {path} should be restricted"

    def test_drive_root_blocked(self):
        """Verify drive roots (C:\\, D:\\) are blocked to prevent overly broad operations."""
        drive_roots = ["C:\\", "D:\\"]

        for path in drive_roots:
            is_restricted, message = is_path_restricted(path)
            assert is_restricted, f"Drive root {path} should be restricted"
            assert "drive root" in message.lower()

    def test_user_folder_roots_blocked(self):
        """Verify user folder roots are blocked but their subfolders are allowed."""
        home = Path.home()
        root_folders = [
            str(home),
            str(home / "Desktop"),
            str(home / "Documents"),
            str(home / "Downloads"),
        ]

        for path in root_folders:
            is_restricted, message = is_path_restricted(path)
            assert is_restricted, f"Root folder {path} should be restricted"
            assert "subfolder" in message.lower()

    def test_user_subfolders_allowed(self):
        """Verify specific project folders within user directories are allowed."""
        home = Path.home()
        allowed_paths = [
            str(home / "Downloads" / "MyProject"),
            str(home / "Documents" / "Work"),
            str(home / "Desktop" / "TempFiles"),
        ]

        for path in allowed_paths:
            is_restricted, _message = is_path_restricted(path)
            assert not is_restricted, f"Subfolder {path} should be allowed"


@pytest.mark.skipif(platform.system() == "Windows", reason="Unix-only test")
class TestPathValidatorMacLinux:
    """
    Mac/Linux-specific path validation tests.

    These tests verify that critical Unix system paths are blocked:
    - System directories (/etc, /bin, /usr, /var)
    - macOS-specific paths (/System, /Library)
    - Root directory (/)
    - User folder roots (~/Desktop, ~/Documents, ~/Downloads)

    Like Windows tests, subfolders are allowed to encourage organization.
    """

    def test_system_paths_blocked(self):
        """Verify Unix system directories are completely blocked."""
        restricted_paths = [
            "/etc",
            "/etc/hosts",
            "/bin",
            "/sbin",
            "/usr",
            "/usr/local",
            "/var",
        ]

        if platform.system() == "Darwin":
            restricted_paths.extend(["/System", "/Library", "/private"])

        for path in restricted_paths:
            is_restricted, message = is_path_restricted(path)
            assert is_restricted, f"Path {path} should be restricted"
            assert "System directories are not allowed" in message

    def test_root_blocked(self):
        """Verify root directory (/) is blocked to prevent system-wide operations."""
        is_restricted, message = is_path_restricted("/")
        assert is_restricted, "Root directory / should be restricted"
        assert "drive root" in message.lower()

    def test_user_folder_roots_blocked(self):
        """Verify user folder roots are blocked but their subfolders are allowed."""
        home = Path.home()
        root_folders = [
            str(home),
            str(home / "Desktop"),
            str(home / "Documents"),
            str(home / "Downloads"),
        ]

        for path in root_folders:
            is_restricted, message = is_path_restricted(path)
            assert is_restricted, f"Root folder {path} should be restricted"
            assert "subfolder" in message.lower()

    def test_user_subfolders_allowed(self):
        """Verify specific project folders within user directories are allowed."""
        home = Path.home()
        allowed_paths = [
            str(home / "Downloads" / "MyProject"),
            str(home / "Documents" / "Work"),
            str(home / "Desktop" / "TempFiles"),
        ]

        for path in allowed_paths:
            is_restricted, _message = is_path_restricted(path)
            assert not is_restricted, f"Subfolder {path} should be allowed"


class TestPathValidatorCrossPlatform:
    """
    Cross-platform path validation tests.

    These tests verify behavior that should be consistent across all platforms.
    """

    def test_nonexistent_path_handling(self):
        """Verify validation works correctly even for paths that don't exist."""
        nonexistent = str(Path.home() / "nonexistent_xyz_123" / "deep" / "path")
        is_restricted, _ = is_path_restricted(nonexistent)
        assert isinstance(is_restricted, bool)

    def test_string_and_path_input(self):
        """Verify function handles both string and Path object inputs consistently."""
        test_path = str(Path.home() / "Documents" / "TestFolder")

        is_restricted_str, msg_str = is_path_restricted(test_path)
        is_restricted_path, msg_path = is_path_restricted(Path(test_path))

        assert is_restricted_str == is_restricted_path
        assert msg_str == msg_path
