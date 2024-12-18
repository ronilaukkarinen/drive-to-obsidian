import os
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import subprocess
from dotenv import load_dotenv
import re
import openai
from openai import OpenAI

# Load environment variables (API keys, paths)
load_dotenv()

# Define directories
OUTPUT_DIR = "./downloads"
VAULT_DIR = os.getenv("OBSIDIAN_VAULT_DIR", "/Users/rolle/Documents/Brain Dump/timeOS")  # Path to Obsidian vault

# Make filtering optional through env variables
FILTER_BY_PREFIX = os.getenv("FILTER_BY_PREFIX", "false").lower() == "true"
TARGET_FILES = os.getenv("TARGET_FILES", "Transcript:,AI Notes").split(",") if FILTER_BY_PREFIX else []

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

    # Filter files based on titles only if FILTER_BY_PREFIX is true
    if FILTER_BY_PREFIX and titles:
        matching_files = [f for f in file_list if any(f['title'].startswith(title) for title in titles)]
        return matching_files

    return file_list

# Download files as DOCX
def sanitize_filename(filename):
    # Handle special prefixes
    for prefix in ["Transcript:", "AI Notes", "Muistiinpanot:"]:  # Added Muistiinpanot: to prefixes
        if filename.startswith(prefix):
            # Remove the prefix and any leading/trailing whitespace
            base_name = filename[len(prefix):].strip()
            # Format as "Name (Type)"
            type_name = "Transcript" if prefix == "Transcript:" else "AI Notes" if prefix == "AI Notes" else "Notes"
            filename = f"{base_name} ({type_name})"

    # Remove .docx extension if it appears in the middle of the filename
    filename = filename.replace('.docx', '')

    # Remove leading hyphens and spaces
    filename = re.sub(r'^[\s-]+', '', filename)

    # Add spaces around dashes that don't have them
    filename = re.sub(r'(?<!\s)-(?!\s)', ' - ', filename)

    # Remove or replace any other invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '-', filename)
    # Remove registered trademark symbol
    filename = filename.replace('®', '')

    return filename.strip()

def download_files(drive, files, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    downloaded_files = []
    for file in files:
        try:
            safe_filename = sanitize_filename(file['title'])
            file_path = os.path.join(output_dir, f"{safe_filename}.docx")

            # Skip if file already exists and has content
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                print(f"Skipping existing file: {file['title']}")
                downloaded_files.append(file_path)
                continue

            print(f"Downloading: {file['title']} -> {file_path}")
            file.GetContentFile(file_path, mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')

            # Verify file size
            if os.path.getsize(file_path) > 0:
                downloaded_files.append(file_path)
            else:
                print(f"Warning: Downloaded file {file_path} is empty")
                os.remove(file_path)
        except Exception as e:
            print(f"Error downloading {file['title']}: {str(e)}")
    return downloaded_files

# Improve markdown formatting
def improve_markdown_formatting(markdown_content):
    try:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

        prompt = """Please improve this markdown formatting. Make sure to:
        1. Use proper headers (# for main title, ## for sections, etc.), do not capitalize each word, only capitalize the first letter of each sentence
        2. Format lists correctly
        3. Properly format code blocks if any
        4. Keep tables well-formatted
        Here's the content to improve:

        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a markdown formatting expert. Return only the formatted markdown without any explanations."},
                {"role": "user", "content": prompt + markdown_content}
            ],
            temperature=0,
            max_tokens=13000
        )

        return response.choices[0].message.content
    except Exception as e:
        print(f"Error improving markdown: {str(e)}")
        return markdown_content

# Convert DOCX to Markdown
def convert_to_md(input_dir, vault_dir):
    converted_files = []
    for filename in os.listdir(input_dir):
        if filename.endswith(".docx"):
            try:
                input_path = os.path.join(input_dir, filename)
                # Clean up the filename before creating md version
                clean_name = sanitize_filename(os.path.splitext(filename)[0])
                md_filename = f"{clean_name}.md"
                final_output_path = os.path.join(vault_dir, md_filename)

                # Check if file already exists in vault
                if os.path.exists(final_output_path):
                    print(f"Skipping existing file in vault: {md_filename}")
                    os.remove(input_path)  # Remove the docx file
                    continue

                print(f"Converting: {filename} -> {md_filename}")
                temp_output_path = os.path.join(input_dir, md_filename)

                result = subprocess.run(
                    ["pandoc",
                     input_path,
                     "-f", "docx",
                     "-t", "markdown_strict+pipe_tables+yaml_metadata_block",
                     "--wrap=none",
                     "--standalone",
                     "-o", temp_output_path],
                    check=False,
                    capture_output=True,
                    text=True
                )

                if result.returncode == 0:
                    with open(temp_output_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    print(f"Improving markdown formatting for: {md_filename}")
                    improved_content = improve_markdown_formatting(content)

                    # Write directly to Obsidian vault
                    with open(final_output_path, 'w', encoding='utf-8') as f:
                        f.write(improved_content)

                    # Clean up temporary and source files
                    os.remove(temp_output_path)  # Remove temporary md file
                    os.remove(input_path)        # Remove original docx file

                    converted_files.append(final_output_path)
                    print(f"Moved to Obsidian vault: {md_filename}")
                else:
                    print(f"Error converting {filename}: {result.stderr}")
            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")
    return converted_files

# Main execution
if __name__ == "__main__":
    drive = authenticate_drive()
    print("Fetching files...")
    files = fetch_files(drive, TARGET_FILES)

    if files:
        downloaded_files = download_files(drive, files, OUTPUT_DIR)
        if downloaded_files:
            converted_files = convert_to_md(OUTPUT_DIR, VAULT_DIR)
            if converted_files:
                print("Sync completed successfully!")
            else:
                print("No files were successfully converted to markdown.")
        else:
            print("No files were successfully downloaded.")
    else:
        print("No matching files found.")
