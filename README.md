# Google Drive docs to Obsidian

Sync Google Drive docs to Obsidian.

## Install and run

### macOS 

1. Enable Google Drive API
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a project and enable the Google Drive API
   - Create OAuth 2.0 credentials for Desktop application
   - Download the credentials and save as `client_secrets.json` in the project root directory

2. Set up Python environment
```bash
python3 -m venv venv
source venv/bin/activate
python3 -m pip install pydrive2 python-dotenv
```

3. Install Pandoc
```bash
brew install pandoc
```

4. Create `.env` file with your Obsidian vault path:
```bash
OBSIDIAN_VAULT_DIR="/path/to/your/obsidian/vault"
```

5. Run the script:
```bash
python3 sync-drive-to-obsidian.py
```

### Linux

1. Follow step 1 from macOS instructions to set up Google Drive API

2. Install dependencies:
```bash
pip install pydrive2 python-dotenv
sudo apt install pandoc
```

3. Follow steps 4-5 from macOS instructions
