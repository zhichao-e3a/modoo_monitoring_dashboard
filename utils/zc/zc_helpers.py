from config.configs import ST_CRED

import requests
import pandas as pd
import streamlit as st
from datetime import timedelta

def get_labor_onset_list(df_excel):

    """
    Date of labor onset
    ADD - c1
    ADD - (c2 + c3) if c1 not present
    """

    onset_list = []

    for _, row in df_excel.iterrows():

        add = row["实际出生日期"]
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

        onset_list.append(onset)

    return onset_list

def format_excel_data(df_excel):

    onset_list      = get_labor_onset_list(df_excel)
    formatted_data  = []

    for idx, row in df_excel.iterrows():

        if pd.isna(row["联系方式"]):
            continue

        data = {
            "name"                  : row["用户"],
            "mobile"                : str(int(row["联系方式"])),
            "pre_survey"            : row["产前问卷填写"],
            "post_survey"           : row["产后问卷填写"],
            "asked"                 : row["Asked onset of labor?"],
            "replied"               : row["Replied?"],
            "reply"                 : row["Reply"],
            "expected_born_date"    : row["预产期"],
            "end_born_ts"           : row["实际出生日期"],
            "onset"                 : onset_list[idx]
        }

        formatted_data.append(data)

    return formatted_data

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

        mobile = patient["mobile"]

        for _, measurement in df_sql.iterrows():

            if measurement["mobile"] == mobile:

                merged_data = {
                    "mobile"                : measurement["mobile"],
                    "id"                    : measurement["id"],
                    "user_id"               : measurement["user_id"],
                    "start_ts"              : measurement["start_ts"],
                    "contraction_url"       : measurement["contraction_url"],
                    "hb_baby_url"           : measurement["hb_baby_url"],
                    "conclusion"            : measurement["conclusion"],
                    "basic_info"            : measurement["basic_info"],
                    "gest_age"              : None,
                    "expected_born_date"    : patient["expected_born_date"] if not pd.isna(patient["expected_born_date"]) else None,
                    "end_born_ts"           : patient["end_born_ts"] if not pd.isna(patient["end_born_ts"]) else None,
                    "onset"                 : patient["onset"] if not pd.isna(patient["onset"]) else None
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