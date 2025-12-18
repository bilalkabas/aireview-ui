#!/usr/bin/env python3
"""
Download PDFs from GitHub releases.

Downloads the pdfs.zip file from GitHub releases and extracts it to the pdfs/ directory.
"""

import os
import sys
import urllib.request
import zipfile
from pathlib import Path


# GitHub release URL for PDFs
GITHUB_RELEASE_URL = "https://github.com/bilalkabas/aireview-ui/releases/download/pdfs/pdfs.zip"

# Get project root (parent of util directory)
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
PDFS_DIR = PROJECT_ROOT / "pdfs"
TEMP_ZIP = PROJECT_ROOT / "pdfs.zip"


def download_file(url: str, dest: Path) -> bool:
    """
    Download a file from URL to destination with progress indicator.

    Args:
        url: The URL to download from
        dest: Destination file path

    Returns:
        True if successful, False otherwise
    """
    try:
        print(f"📥 Downloading PDFs from GitHub releases...")
        print(f"   URL: {url}")

        # Download with progress
        def progress_hook(block_count, block_size, total_size):
            if total_size > 0:
                downloaded = block_count * block_size
                percent = min(100, (downloaded / total_size) * 100)
                mb_downloaded = downloaded / (1024 * 1024)
                mb_total = total_size / (1024 * 1024)
                print(f"\r   Progress: {percent:.1f}% ({mb_downloaded:.1f} MB / {mb_total:.1f} MB)", end='')

        urllib.request.urlretrieve(url, dest, reporthook=progress_hook)
        print()  # New line after progress
        print(f"✅ Download complete: {dest}")
        return True

    except urllib.error.URLError as e:
        print(f"\n❌ Error downloading file: {e}")
        print(f"   Make sure the URL is correct and you have internet connectivity.")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False


def extract_zip(zip_path: Path, extract_to: Path) -> bool:
    """
    Extract a zip file to a directory.

    Args:
        zip_path: Path to the zip file
        extract_to: Directory to extract to

    Returns:
        True if successful, False otherwise
    """
    try:
        print(f"\n📦 Extracting PDFs...")
        print(f"   Destination: {extract_to}")

        # Create destination directory if it doesn't exist
        extract_to.mkdir(parents=True, exist_ok=True)

        # Extract zip
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Get list of files
            file_list = zip_ref.namelist()
            pdf_files = [f for f in file_list if f.endswith('.pdf')]

            print(f"   Found {len(pdf_files)} PDF files in archive")

            # Extract all files
            zip_ref.extractall(extract_to)

        print(f"✅ Extraction complete")
        print(f"   Extracted {len(pdf_files)} PDF files to {extract_to}")
        return True

    except zipfile.BadZipFile:
        print(f"❌ Error: Invalid zip file: {zip_path}")
        return False
    except Exception as e:
        print(f"❌ Error extracting zip: {e}")
        return False


def cleanup_temp_file(file_path: Path):
    """Remove temporary file."""
    try:
        if file_path.exists():
            file_path.unlink()
            print(f"🗑️  Cleaned up temporary file: {file_path}")
    except Exception as e:
        print(f"⚠️  Warning: Could not remove temporary file {file_path}: {e}")


def count_existing_pdfs(directory: Path) -> int:
    """Count existing PDF files in directory."""
    if not directory.exists():
        return 0
    return len(list(directory.glob("*.pdf")))


def main():
    """Main entry point."""
    print("\n" + "=" * 80)
    print("PDF DOWNLOADER - GitHub Releases")
    print("=" * 80)

    # Check if pdfs directory already has files
    existing_count = count_existing_pdfs(PDFS_DIR)
    if existing_count > 0:
        print(f"\n⚠️  Warning: {existing_count} PDF files already exist in {PDFS_DIR}")
        response = input("   Do you want to re-download and overwrite? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("❌ Operation cancelled by user")
            sys.exit(0)

    # Download the zip file
    success = download_file(GITHUB_RELEASE_URL, TEMP_ZIP)
    if not success:
        sys.exit(1)

    # Extract the zip file
    success = extract_zip(TEMP_ZIP, PDFS_DIR)
    if not success:
        cleanup_temp_file(TEMP_ZIP)
        sys.exit(1)

    # Clean up temporary zip file
    cleanup_temp_file(TEMP_ZIP)

    # Show final summary
    final_count = count_existing_pdfs(PDFS_DIR)
    print("\n" + "=" * 80)
    print("DOWNLOAD COMPLETE")
    print("=" * 80)
    print(f"Total PDF files in {PDFS_DIR}: {final_count}")
    print("=" * 80)
    print("\n✅ PDFs are ready to use!")
    print(f"   You can now start the webapp server to view papers.")


if __name__ == "__main__":
    main()
