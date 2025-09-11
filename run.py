from app.engine import entrypoint
from app.utils import ensure_output_dir
from dotenv import load_dotenv

load_dotenv()

if __name__ == '__main__':
    entrypoint()

"""
https://login.xero.com/identity/connect/authorize?response_type=code&client_id=83F7838F841841978F1F2BFDD2E4DEC5&redirect_uri=https://buildpartner.com/&scope=openid profile offline_access email accounting.transactions&state=123&code_challenge=XXXXXXXXX&code_challenge_method=S256
"""