from config.configs import REMOTE_MONGO_CONFIG
from pymongo import MongoClient

import streamlit as st

@st.cache_data(show_spinner=True, ttl=60)
def get_data(coll_name: str, projection: dict=None, limit: int=None):

    uri     = REMOTE_MONGO_CONFIG['DB_HOST']
    db_name = REMOTE_MONGO_CONFIG["DB_NAME"]
    client  = MongoClient(uri)
    coll    = client[db_name][coll_name]

    docs = coll.find({}, projection or {"_id": 0})

    if limit:
        docs = docs.limit(limit)

    docs_list = list(docs)

    client.close()

    return docs_list
