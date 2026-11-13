## Setup

```bash
python -m venv .venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

**CLI:**
```bash
python main_cli.py
```



New-Item -ItemType Directory -Force D:\venvs

py -3.12 -m venv D:\venvs\Crew_venv

D:\venvs\Crew_venv\Scripts\Activate.ps1

python -m pip install --upgrade pip

# Core
pip install crewai crewai-tools python-dotenv

# Common extras for full projects
pip install requests beautifulsoup4 pandas

# Save the installed versions
pip freeze > D:\venvs\Crew_venv\requirements.txt


D:\venvs\Crew_venv\Scripts\Activate.ps1
pip install -r D:\venvs\Crew_venv\requirements.txt