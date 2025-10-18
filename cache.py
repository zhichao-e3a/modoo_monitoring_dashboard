from database.MongoDBConnector import MongoDBConnector

import streamlit as st
import asyncio

@st.cache_resource
def get_mongo_connector():
    return MongoDBConnector(mode="remote")

@st.cache_data(show_spinner=True, ttl=60)
def get_data(coll_name: str):

    mongo = get_mongo_connector()

    return asyncio.run(mongo.get_all_documents(coll_name=coll_name))
