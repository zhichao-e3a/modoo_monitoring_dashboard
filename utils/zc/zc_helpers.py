from config.configs import ST_CRED

import requests
import pandas as pd
import streamlit as st
from datetime import timedelta, datetime

def format_excel_data(main_df, pre_df):

    merged_df = pd.merge(main_df, pre_df, left_on="联系方式", right_on="2.电话号码", how="left")

    formatted_data  = []
    skipped         = 0

    for idx, row in merged_df.iterrows():

        if pd.isna(row["联系方式"]):
            continue

        contact                     = row["联系方式"]
        data_origin                 = row["data_origin"]
        delivery_mode               = row["delivery_mode"]
        last_menstrual_str          = row["7.您的最后一次月经大概是什么时候？"]
        expected_delivery_timestamp = row["预产期"]
        actual_delivery_timestamp   = row["实际出生日期"]
        actual_delivery_time        = row["实际出生时间 (HH:MM:SS)"]

        # last_menstrual_str        %d/%m/%Y            (str)                   Nullable
        # expected_delivery_date    %Y/%m/%d            (timestamps.Timestamp)  Non-nullable
        # actual_delivery_date      %Y/%m/%d            (timestamps.Timestamp)  Nullable
        # actual_delivery_time      HH:MM:SS            (datetime.time)         Nullable
        # onset_time                %Y/%m/%d HH:MM:SS   (timestamps.Timestamp)  Nullable

        last_menstrual_datetime = datetime.strptime(
            last_menstrual_str,
            "%d/%m/%Y"
        ).strftime("%Y-%m-%d %H:%M:%S") if not pd.isna(last_menstrual_str) else None

        expected_delivery_datetime = expected_delivery_timestamp.strftime("%Y-%m-%d %H:%M:%S")

        if not pd.isna(actual_delivery_timestamp) and not pd.isna(actual_delivery_time):
            actual_delivery_datetime = datetime.combine(
                actual_delivery_timestamp.to_pydatetime().date(),
                actual_delivery_time
            )
        elif not pd.isna(actual_delivery_timestamp):
            actual_delivery_datetime = actual_delivery_timestamp
        else:
            actual_delivery_datetime = None

        if not pd.isna(actual_delivery_datetime):
            onset_datetime = get_labor_onset(row, actual_delivery_datetime)
        else:
            onset_datetime = None

        data = {
            "contact"                   : str(int(contact)),
            "data_origin"               : data_origin,
            "delivery_mode"             : delivery_mode,
            "last_menstrual_datetime"   : last_menstrual_datetime,
            "expected_delivery_date"    : expected_delivery_datetime,
            "actual_delivery_datetime"  : actual_delivery_datetime.strftime("%Y-%m-%d %H:%M:%S") if actual_delivery_datetime else None,
            "onset_datetime"            : onset_datetime.strftime("%Y-%m-%d %H:%M:%S") if onset_datetime else None
        }

        formatted_data.append(data)

    return formatted_data

def get_labor_onset(row, actual_delivery_datetime):

    """
    Date of labor onset
    ADD - c1
    ADD - (c2 + c3) if c1 not present
    """

    add = actual_delivery_datetime
    c1  = row.iloc[11]
    c2  = row.iloc[12]
    c3  = row.iloc[13]
    c4  = row.iloc[14]

    onset = None
    if not pd.isna(c4):
        pass
    # Has c1 ; Use c1 first
    elif not pd.isna(c1):
        onset = add - timedelta(minutes=c1)
    # Have both c2 and c3 ; Use both
    elif not pd.isna(c2) and not pd.isna(c3):
        onset = add - timedelta(minutes=c2) - timedelta(minutes=c3)
    # Only has c2 ; Use c2 only (c3 defaults to 0)
    elif not pd.isna(c2):
        onset = add - timedelta(minutes=c2)
    # Only has c3 ; Use c3 only (c2 defaults to 0)
    elif not pd.isna(c3):
        onset = add - timedelta(minutes=c3)

    return onset

def get_query_string(df_excel):

    to_return = ""

    for _, i in enumerate(df_excel["联系方式"]):

        if not pd.isna(i):
            to_return += f"'{int(i)}',"

        else:
            print(f"Patient {_+1} has no number")

    return to_return

def merge_excel_sql(list_excel, df_sql):

    all_merged_data = []

    for patient in list_excel:

        mobile = patient["contact"]

        for _, measurement in df_sql.iterrows():

            if measurement["mobile"] == mobile:

                merged_data = {
                    "id"                    : measurement["id"],
                    "mobile"                : measurement["mobile"],
                    "start_ts"              : datetime\
                        .fromtimestamp(int(measurement["start_ts"]))\
                        .strftime("%Y-%m-%d %H:%M:%S"),
                    "data_origin"           : patient["data_origin"],
                    "delivery_mode"         : patient["delivery_mode"],
                    "contraction_url"       : measurement["contraction_url"],
                    "hb_baby_url"           : measurement["hb_baby_url"],
                    "conclusion"            : measurement["conclusion"],
                    "basic_info"            : measurement["basic_info"],
                    "last_menstrual_date"   : patient["last_menstrual_datetime"],
                    "expected_born_date"    : patient["expected_delivery_date"],
                    "end_born_ts"           : patient["actual_delivery_datetime"],
                    "onset"                 : patient["onset_datetime"]
                }

                all_merged_data.append(merged_data)

    return all_merged_data

def run_rec_pipeline():

    requests.get("http://127.0.0.1:8000/run_rec_pipeline")

def run_hist_pipeline():

    requests.get("http://127.0.0.1:8000/run_hist_pipeline")

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