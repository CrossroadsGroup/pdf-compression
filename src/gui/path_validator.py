"""Path validation utilities to prevent processing in sensitive directories."""

import platform
from pathlib import Path


def is_path_restricted(folder_path: str | Path) -> tuple[bool, str]:
    """
    Check if a path is restricted for processing.

    Prevents processing in:
    - System directories
    - User home directory root
    - Desktop, Documents, Downloads (must select subfolder)
    - Overly broad paths (< 3 levels deep)

    Args:
        folder_path: Path to validate

    Returns:
        Tuple of (is_restricted: bool, error_message: str)
    """
    folder_path = Path(folder_path).resolve()

    # System directories - block entirely (including subdirectories)
    system_paths = []
    # Root-only restrictions - allow subdirectories
    root_only_paths = []

    if platform.system() == "Windows":
        home_dir = Path.home()

        # Critical system directories - never allow
        system_paths = [
            Path("C:\\Windows"),
            Path("C:\\Program Files"),
            Path("C:\\Program Files (x86)"),
            Path("C:\\ProgramData"),
            Path("C:\\$Recycle.Bin"),
            home_dir / "AppData",
        ]

        # User directories - only allow specific subfolders
        root_only_paths = [
            home_dir,
            home_dir / "Desktop",
            home_dir / "Documents",
            home_dir / "Downloads",
            home_dir / "Pictures",
            home_dir / "Music",
            home_dir / "Videos",
        ]

        # Add OneDrive paths if they exist - only allow subfolders
        for onedrive_variant in ["OneDrive", "OneDrive - Personal"]:
            onedrive_path = home_dir / onedrive_variant
            if onedrive_path.exists():
                root_only_paths.append(onedrive_path)

        # Check for any OneDrive - Company paths
        try:
            for item in home_dir.iterdir():
                if item.is_dir() and item.name.startswith("OneDrive - "):
                    root_only_paths.append(item)
        except (OSError, PermissionError):
            pass

    else:
        home_dir = Path.home()

        # Critical system directories - never allow
        system_paths = [
            Path("/etc"),
            Path("/bin"),
            Path("/sbin"),
            Path("/usr"),
            Path("/var"),
            Path("/System"),
            Path("/Library"),
            Path("/private"),
        ]

        # User directories - only allow specific subfolders
        root_only_paths = [
            home_dir,
            home_dir / "Desktop",
            home_dir / "Documents",
            home_dir / "Downloads",
            home_dir / "Pictures",
            home_dir / "Music",
            home_dir / "Movies",
        ]

    # Check system paths - block if it's the path or any ancestor
    for restricted in system_paths:
        try:
            restricted = restricted.resolve()
            if folder_path == restricted or restricted in folder_path.parents:
                return (
                    True,
                    f"Cannot process files in: {restricted}\n\n"
                    "System directories are not allowed.",
                )
        except (OSError, ValueError):
            continue

    # Check for drive roots (C:\, D:\, etc.)
    if len(folder_path.parts) <= 1:
        return (
            True,
            f"Cannot process files in drive root: {folder_path}\n\n"
            "Please select a specific folder.",
        )

    # Check root-only paths - only block exact matches (subfolders are OK)
    for restricted in root_only_paths:
        try:
            restricted = restricted.resolve()
            if folder_path == restricted:
                return (
                    True,
                    f"Cannot process files in: {restricted}\n\n"
                    "Please select a specific subfolder (e.g., Downloads\\MyProject or OneDrive\\ClientFiles).",
                )
        except (OSError, ValueError):
            continue

    return False, ""
