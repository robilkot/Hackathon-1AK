from os import getenv
from dotenv import load_dotenv

load_dotenv()

API_PORT = int(getenv("API_PORT"))
TEST_PRINT_EN=bool(getenv("TEST_PRINT_EN"))
OS_TYPE = getenv("OS_TYPE", "").upper()