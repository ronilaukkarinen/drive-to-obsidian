import os
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import subprocess
from dotenv import load_dotenv
import re

# Load environment variables (API keys, paths)
load_dotenv()

# Define directories
OUTPUT_DIR = "./downloads"
VAULT_DIR = os.getenv("OBSIDIAN_VAULT_DIR", "/Users/rolle/Documents/Brain Dump/timeOS")  # Path to Obsidian vault

# Titles to sync
TARGET_FILES = ["Transcript:", "AI Notes"]

# Authenticate with Google Drive
def authenticate_drive():
    gauth = GoogleAuth()
    # Add specific scope for private files
    gauth.settings['scope'] = ['https://www.googleapis.com/auth/drive']
    gauth.LocalWebserverAuth()  # Authenticate via browser
    return GoogleDrive(gauth)

# Fetch files from Google Drive
def fetch_files(drive, titles):
    # Print current authentication status
    about = drive.GetAbout()
    print(f"Authenticated as: {about['user']['emailAddress']}")
    print(f"Name: {about['user']['displayName']}")

    # Include both Google Docs and DOCX files
    query = ("(mimeType='application/vnd.google-apps.document' or "
             "mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document') and "
            "(sharedWithMe=true or 'me' in owners)")
    file_list = drive.ListFile({'q': query}).GetList()

    # Debug: print all files with more details
    print("\nFound files:")
    for f in file_list:
        print(f"Title: {f['title']}")
        print(f"Owner: {f.get('owners', [{'displayName': 'Unknown'}])[0]['displayName']}")
        print(f"Shared: {f.get('shared', False)}")
        print(f"MimeType: {f.get('mimeType', 'Unknown')}")
        print("---")

    # Filter files based on titles
    matching_files = [f for f in file_list if any(f['title'].startswith(title) for title in titles)]
    return matching_files

# Download files as DOCX
def sanitize_filename(filename):
    # Remove or replace invalid characters
    # Replace colons and registered trademark symbol
    filename = filename.replace(':', '-').replace('®', '')
    # Remove or replace any other invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '-', filename)
    return filename.strip()

def download_files(drive, files, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    for file in files:
        safe_filename = sanitize_filename(file['title'])
        file_path = os.path.join(output_dir, f"{safe_filename}.docx")
        print(f"Downloading: {file['title']} -> {file_path}")
        file.GetContentFile(file_path, mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')

# Convert DOCX to Markdown
def convert_to_md(input_dir, output_dir):
    for filename in os.listdir(input_dir):
        if filename.endswith(".docx"):
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, f"{os.path.splitext(filename)[0]}.md")
            print(f"Converting: {input_path} -> {output_path}")
            subprocess.run(["pandoc", input_path, "-o", output_path], check=True)

# Sync files to Obsidian vault
def sync_to_obsidian(output_dir, vault_dir):
    for filename in os.listdir(output_dir):
        if filename.endswith(".md"):
            source_path = os.path.join(output_dir, filename)
            target_path = os.path.join(vault_dir, filename)
            print(f"Syncing: {source_path} -> {target_path}")
            os.replace(source_path, target_path)

# Main execution
if __name__ == "__main__":
    drive = authenticate_drive()
    print("Fetching files...")
    files = fetch_files(drive, TARGET_FILES)

    if files:
        download_files(drive, files, OUTPUT_DIR)
        convert_to_md(OUTPUT_DIR, OUTPUT_DIR)
        sync_to_obsidian(OUTPUT_DIR, VAULT_DIR)
        print("Sync completed successfully!")
    else:
        print("No matching files found.")