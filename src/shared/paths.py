from pathlib import Path

# src/shared/paths.py -> parents[0]=src/shared, [1]=src, [2]=repo root.
ROOT = Path(__file__).resolve().parents[2]
