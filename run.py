from app.engine import entrypoint
from app.utils import ensure_output_dir
from dotenv import load_dotenv

load_dotenv()

if __name__ == '__main__':
    entrypoint()
