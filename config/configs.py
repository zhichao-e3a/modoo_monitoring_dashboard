import os
from dotenv import load_dotenv

load_dotenv("config/.env")

DB_CONFIG = {
    'DB_HOST'   : os.getenv("DB_HOST"),
    'DB_PORT'   : int(os.getenv("DB_PORT")),
    'DB_USER'   : os.getenv("DB_USER"),
    'DB_PASS'   : os.getenv("DB_PASS"),
    'DB_NAME'   : os.getenv("DB_NAME"),
    'SSH_HOST'  : os.getenv("SSH_HOST"),
    'SSH_PORT'  : int(os.getenv("SSH_PORT")),
    'SSH_USER'  : os.getenv("SSH_USER"),
    'SSH_PKEY'  : os.getenv("SSH_PKEY")
}

ST_CRED = {
    'ST_USER' : os.getenv("ST_USER"),
    'ST_PASS' : os.getenv("ST_PASS")
}

DEFAULT_MONGO_CONFIG = {
    "uri"                   : os.getenv("MONGO_URL_E3A"),
    "db_name"               : og.getenv("MONGO_NAME_E3A"),
    "collection_raw"        : "recruited_patients_raw_data",
    "collection_features"   : "recruited_patients_data"
}
