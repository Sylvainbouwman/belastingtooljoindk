import sys
from pathlib import Path

# Projectroot op sys.path, zodat de tests dezelfde imports kunnen doen als de
# Streamlit-pagina's (die de root automatisch van Streamlit meekrijgen).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
