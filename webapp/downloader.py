import os
import urllib.request
import zipfile
from tqdm import tqdm


def download_from_github_releases(github_url, extract_to):
    """
    Download PDFs from GitHub releases zip file.

    Args:
        github_url: URL to the pdfs.zip file on GitHub releases
        extract_to: Directory to extract PDFs to

    Returns:
        Number of PDFs extracted
    """
    temp_zip = os.path.join(extract_to, "temp_pdfs.zip")

    try:
        # Create extraction directory if it doesn't exist
        os.makedirs(extract_to, exist_ok=True)

        # Check if PDFs already exist
        existing_pdfs = [f for f in os.listdir(extract_to) if f.endswith('.pdf')] if os.path.exists(extract_to) else []
        if existing_pdfs:
            print(f"ℹ️  Found {len(existing_pdfs)} existing PDFs in {extract_to}")
            print(f"   Skipping download from GitHub releases")
            return len(existing_pdfs)

        print(f"📥 Downloading PDFs from GitHub releases...")
        print(f"   URL: {github_url}")

        # Download with progress
        def progress_hook(block_count, block_size, total_size):
            if total_size > 0:
                downloaded = block_count * block_size
                percent = min(100, (downloaded / total_size) * 100)
                mb_downloaded = downloaded / (1024 * 1024)
                mb_total = total_size / (1024 * 1024)
                print(f"\r   Progress: {percent:.1f}% ({mb_downloaded:.1f} MB / {mb_total:.1f} MB)", end='', flush=True)

        urllib.request.urlretrieve(github_url, temp_zip, reporthook=progress_hook)
        print()  # New line after progress

        # Extract zip
        print(f"📦 Extracting PDFs to {extract_to}...")
        with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
            pdf_files = [f for f in zip_ref.namelist() if f.endswith('.pdf')]
            print(f"   Found {len(pdf_files)} PDF files in archive")

            # Extract with progress bar, flattening directory structure
            with tqdm(total=len(pdf_files), desc="Extracting PDFs", unit="file") as pbar:
                for file in pdf_files:
                    # Get just the filename (without any directory path from zip)
                    filename = os.path.basename(file)
                    target_path = os.path.join(extract_to, filename)
                    
                    # Read from zip and write directly to target
                    with zip_ref.open(file) as source, open(target_path, 'wb') as target:
                        target.write(source.read())
                    pbar.update(1)

        # Clean up temp file
        os.remove(temp_zip)

        print(f"✅ Successfully extracted {len(pdf_files)} PDFs")
        return len(pdf_files)

    except urllib.error.URLError as e:
        print(f"\n❌ Error downloading from GitHub: {e}")
        print(f"   Make sure the URL is correct and you have internet connectivity")
        if os.path.exists(temp_zip):
            os.remove(temp_zip)
        return 0
    except zipfile.BadZipFile:
        print(f"\n❌ Error: Downloaded file is not a valid zip archive")
        if os.path.exists(temp_zip):
            os.remove(temp_zip)
        return 0
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        if os.path.exists(temp_zip):
            os.remove(temp_zip)
        return 0


if __name__ == "__main__":
    import dotenv

    # Load environment variables
    # When run from ./run script, WEBAPP_ENV_FILE will be set
    env_file = os.getenv("WEBAPP_ENV_FILE")
    if env_file and os.path.exists(env_file):
        dotenv.load_dotenv(env_file)
    else:
        dotenv.load_dotenv()

    # Get paths from environment (these are absolute paths set by ./run script)
    project_root = os.getenv("WEBAPP_PROJECT_ROOT", os.path.dirname(os.path.dirname(__file__)))
    pdfs_root = os.getenv("WEBAPP_PDFS_ROOT", os.path.join(project_root, "pdfs"))

    # Check for GitHub releases URL
    github_releases_url = os.getenv("WEBAPP_GITHUB_RELEASES_PDF_URL")

    if not github_releases_url:
        print("❌ Error: WEBAPP_GITHUB_RELEASES_PDF_URL not set in .env file")
        print("   Please set it to your GitHub releases PDF URL, for example:")
        print("   WEBAPP_GITHUB_RELEASES_PDF_URL=https://github.com/user/repo/releases/download/pdfs/pdfs.zip")
        exit(1)

    # Download from GitHub releases
    print(f"Downloading PDFs from GitHub releases")
    print(f"Target directory: {pdfs_root}")
    download_from_github_releases(github_releases_url, pdfs_root)
