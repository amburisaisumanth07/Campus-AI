import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import time
from backend.app.core.config import settings
from google import genai
from google.genai import types

def test_embed():
    c = genai.Client(api_key=settings.GEMINI_API_KEY)
    try:
        res = c.models.embed_content(
            model='gemini-embedding-2',
            contents='task: search result | query: Who is the HOD of Civil Engineering?',
            config=types.EmbedContentConfig(output_dimensionality=768)
        )
        print('SUCCESS! Vector length:', len(res.embedding.values))
    except Exception as e:
        print('ERROR:', e)

if __name__ == '__main__':
    test_embed()
