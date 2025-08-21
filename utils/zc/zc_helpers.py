from config.configs import ST_CRED

from database.SQLDBConnector import DatabaseConnector

import json
import requests
import pandas as pd
import streamlit as st

def verify_login(username, password):

    if not username:
        st.warning("Please enter your username")

    elif not password:
        st.warning("Please enter your password")

    elif username == ST_CRED["ST_USER"] and password == ST_CRED["ST_PASS"]:
        st.success("Successfully logged in")
        st.session_state.logged_in = True
        st.rerun()

    else:
        st.warning("Wrong username or password")

def run_pipeline():

    requests.get("http://127.0.0.1:8000/run_pipeline")



query_template = """
SELECT
uu.mobile,
r.psn,
r.id,
r.user_id,
r.hb_baby_url,
r.contraction_url,
r.hb_sound_url,
r.conclusion,
FROM_UNIXTIME(r.start_ts, '%%Y-%%m-%%d %%H:%%i:%%s') AS start_ts,
CASE 
WHEN r.start_test_ts = 0 THEN '0'
ELSE FROM_UNIXTIME(r.start_test_ts, '%%Y-%%m-%%d %%H:%%i:%%s')
END AS start_test_ts,
r.ctime,

r.basic_info

FROM
extant_future_user.user AS uu    -- extant_future_user.user
INNER JOIN
origin_data_record AS r          -- extant_future_data.origin_data_record
ON r.user_id = uu.id
AND uu.mobile IN (
)
AND r.start_ts BETWEEN UNIX_TIMESTAMP({start}) AND UNIX_TIMESTAMP({end})
"""

def get_patient_records(start, end):

    query = query_template.format(start=start, end=end)

    db = DatabaseConnector()

    pandas_df   = db.query_to_dataframe(sql=query)

    new_dict = {
        "user": [],
        "week": []
    }

    for _, row in pandas_df.iterrows():

        basic_info = json.loads(row["basic_info"])

        if basic_info["setPregTime"]:
            new_dict["user"].append(row["user_id"])
            new_dict["week"].append(basic_info["pregTime"][1:3])

        else:
            new_dict["user"].append(row["user_id"])
            new_dict["week"].append("NO GESTATIONAL AGE")

    new_df = pd.DataFrame(new_dict)
    n_unique_patients = len(new_df["user"].unique())

    summary_df = new_df.groupby('week').agg(
        patients=('user', 'nunique'),
        measurements=('user', 'count')
    ).reset_index()

    return summary_df, n_unique_patients
