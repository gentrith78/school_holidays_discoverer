from app.engine import entrypoint
from app.utils import configure_logging
from dotenv import load_dotenv

load_dotenv()

if __name__ == '__main__':
    entrypoint()