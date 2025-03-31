#!/bin/bash

# Update pip to latest version
python -m pip install --upgrade pip

# Install core dependencies explicitly (in case requirements.txt fails)
pip install tqdm --no-cache-dir
pip install sqlalchemy --no-cache-dir
pip install streamlit --no-cache-dir
pip install openai --no-cache-dir
pip install pandas --no-cache-dir
pip install matplotlib --no-cache-dir
pip install plotly --no-cache-dir
pip install openpyxl --no-cache-dir
pip install xlsxwriter --no-cache-dir
pip install python-dotenv --no-cache-dir
pip install watchdog --no-cache-dir

# Now install from requirements
pip install -r requirements.txt --no-cache-dir

echo "All dependencies installed. Ready to run the app." 