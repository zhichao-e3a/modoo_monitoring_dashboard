from database.MongoDBConnector import MongoDBConnector

import asyncio
import pandas as pd
import streamlit as st

from datetime import date
from collections import Counter

mongo = MongoDBConnector(mode="remote")

st.set_page_config(
    page_title="Patient Analytics Dashboard",
    layout="wide"
)

st.title("Patient Analytics Dashboard")
st.divider()

@st.cache_data(show_spinner=True, ttl=60)
def load_data():
    return asyncio.run(mongo.get_all_documents(coll_name="patients_unified"))

def pct(old, new):
    return ((new-old)/old)*100

with st.container():
    past = st.date_input("`Statistics relative to data till`", date.today(), max_value="today")

# Calculate statistics for patient count
patients        = load_data()
past_patients   = [i for i in patients if i['date_joined'] <= past.strftime("%Y-%m-%d")]

rec         = [i for i in patients if i['recruitment_type'] == 'recruited']
past_rec    = [i for i in past_patients if i['recruitment_type'] == 'recruited']

hist        = [i for i in patients if i['recruitment_type'] == 'historical']
past_hist   = [i for i in past_patients if i['recruitment_type'] == 'historical']

with st.container():
    st.subheader("Patient Overview")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total Patients", len(patients), border=True, delta=len(patients)-len(past_patients))
    with c2:
        st.metric("Recruited", len(rec), border=True, delta=len(rec)-len(past_rec))
    with c3:
        st.metric("Historical", len(hist), border=True, delta=len(hist)-len(past_hist))

# Calculate statistics for patient delivery
delivered       = [i for i in patients if not pd.isna(i["delivery_type"])]
past_delivered  = [i for i in delivered if i['delivery_datetime'] <= past.strftime("%Y-%m-%d")]

natural         = [i for i in delivered if i['delivery_type'] == 'natural']
past_natural    = [i for i in past_delivered if i['delivery_type'] == 'natural']

csection        = [i for i in delivered if i['delivery_type'] == 'c-section']
past_csection   = [i for i in past_delivered if i['delivery_type'] == 'c-section']

ecsection       = [i for i in delivered if i['delivery_type'] == 'emergency c-section']
past_ecsection  = [i for i in past_delivered if i['delivery_type'] == 'emergency c-section']

with st.container():
    st.subheader("Delivery Status")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Delivered", len(delivered), border=True, delta=len(delivered)-len(past_delivered))
    with c2:
        st.metric("Natural", len(natural), border=True, delta=len(natural)-len(past_natural))
    with c3:
        st.metric("Emergency C-section", len(ecsection), border=True, delta=len(ecsection)-len(past_ecsection))
    with c4:
        st.metric("C-section", len(csection), border=True, delta=len(csection)-len(past_csection))

# Calculate statistics for onset/ADD
valid       = natural + ecsection
past_valid  = [i for i in valid if i['delivery_datetime'] <= past.strftime("%Y-%m-%d")]

add         = [i for i in valid if not pd.isna(i['delivery_datetime']) and i['delivery_datetime']]
past_add    = [i for i in past_valid if not pd.isna(i['delivery_datetime']) and i['delivery_datetime']]

onset       = [i for i in valid if not pd.isna(i['onset_datetime']) and i['onset_datetime']]
past_onset  = [i for i in past_valid if not pd.isna(i['onset_datetime']) and i['onset_datetime']]

with st.container():
    st.subheader("Endpoints Captured (for Natural, C-section)")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total Valid", len(valid), border=True, delta=len(valid)-len(past_valid))
    with c2:
        st.metric("With Onset Datetime", len(onset), border=True, delta=len(onset)-len(past_onset))
    with c3:
        st.metric("With Delivery Datetime", len(add), border=True, delta=len(add)-len(past_add))

st.divider()

ga_entry                = [f"{int(i['ga_entry_weeks'])} weeks" for i in patients if not pd.isna(i['ga_entry_weeks'])]
ga_entry_dict           = dict(Counter(ga_entry))
sorted_ga_entry_dict    = dict(sorted(ga_entry_dict.items()))

ga_exit                = [f"{int(i['ga_exit_weeks'])} weeks" for i in patients if not pd.isna(i['ga_exit_weeks'])]
ga_exit_dict           = dict(Counter(ga_exit))
sorted_ga_exit_dict    = dict(sorted(ga_exit_dict.items()))

with st.container():

    st.subheader("Report by Gestational Age")

    st.write("Gestational Age Weeks at Entry")
    st.bar_chart(
        sorted_ga_entry_dict,
        x_label = "Gestational Age Weeks (Entry)",
        y_label = "Patient Count"
    )

    st.write("Gestational Age Weeks at Exit")
    st.bar_chart(
        sorted_ga_exit_dict,
        x_label="Gestational Age Weeks (Exit)",
        y_label="Patient Count"
    )

