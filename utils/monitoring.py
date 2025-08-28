from database.MongoDBConnector import MongoDBConnector
from database.SQLDBConnector import SQLDBConnector

from datetime import datetime, timedelta
import asyncio

mysql = SQLDBConnector()
mongo = MongoDBConnector()

def get_sql_count():

    query = """
        SELECT COUNT(*) AS count FROM extant_future_data.origin_data_record
    """

    count = mysql.query_to_dataframe(query)

    return count["count"][0]

def get_mongo_count(coll_name):

    all_docs = asyncio.run(mongo.get_all_documents(
        coll_name=coll_name
    ))

    return len(all_docs)

def get_logs():

    runs = asyncio.run(
        mongo.get_all_documents(
            coll_name="logs"
        )
    )

    return runs

def get_recent_logs():

    end_time    = datetime.now()
    start_time  = end_time - timedelta(hours=24)

    recent_runs = asyncio.run(mongo.get_all_documents(
        coll_name   = "logs",
        query       = {
            "date" : {
                "$gte" : start_time.isoformat(timespec="microseconds"),
                "$lte" : end_time.isoformat(timespec="microseconds")
            }
        }
    ))

    return recent_runs

def get_recent_counts(coll_name):

    recent_counts = []
    end_time = datetime.now()

    for i in range(7):

        records = asyncio.run(
            mongo.get_all_documents(
                coll_name   = coll_name,
                query       = {
                    "created_at" : {
                        "$lte" : end_time.isoformat(timespec="microseconds")
                    }
                }
            )
        )

        end_time -= timedelta(hours=24)

        recent_counts.append(len(records))

    return recent_counts