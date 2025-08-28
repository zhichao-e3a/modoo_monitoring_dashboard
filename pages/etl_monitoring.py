from utils.monitoring import *

import streamlit as st

import pandas as pd

st.set_page_config(page_title="Data Ops", layout="wide")
st.title("Modoo Monitoring System: Data Ops")

if "sql_rows" not in st.session_state:
    st.session_state.sql_rows = get_sql_count()

collection = st.selectbox(
    label = "Select Collection",
    options = [
        "Recruited",
        "Historical"
    ]
)

collection_mapping = {
    "Recruited": {
        "type"          : "rec",
        "source"        : "MySQL",
        "target"        : "MongoDB",
        "main_coll"     : "rec_processed_data",
        "collections"   : [
            "rec_raw_data",
            "rec_processed_data"
        ]
    },
    "Historical": {
        "type"          : "hist",
        "source"        : "MySQL",
        "target"        : "MongoDB",
        "main_coll"     : "hist_processed_data",
        "collections"   : [
            "hist_raw_data",
            "hist_processed_data"
        ]
    }
}

collection_info = collection_mapping[collection]

coll_runs           = [i for i in get_logs() if i["type"] == collection_info["type"]]
coll_recent_runs    = [i for i in get_recent_logs() if i["type"] == collection_info["type"]]

coll_runs.sort(key=lambda x: x["date"], reverse=True)
coll_recent_runs.sort(key=lambda x: x["date"], reverse=True)

coll_recent_runs_df = pd.DataFrame(coll_recent_runs)

####################################################################################################

st.subheader("1) Health Summary")

coll_counts = [
    get_mongo_count(collection_info["collections"][0]),
    get_mongo_count(collection_info["collections"][1])
]

with st.container(border=True):

    st.subheader("Number of records")
    st.divider()

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(label="Last full run", value=coll_runs[0]["date"][:10])
        st.caption(coll_runs[0]["date"][10:])

    with c2:
        st.metric(label="MySQL", value=st.session_state.sql_rows)
        st.caption("origin_data_record")

    with c3:
        st.metric(label="MongoDB", value=coll_counts[0])
        st.caption(collection_info["collections"][0])

    with c4:
        st.metric(label="MongoDB", value=coll_counts[1])
        st.caption(collection_info["collections"][1])

st.subheader("2) Run Status")

n_errors            = sum([1 for i in coll_recent_runs if i["status"] != "completed"])

with st.container(border=True):

    st.subheader("Past 24 hours")
    st.divider()

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(label="Number of runs", value=len(coll_recent_runs))

    with c2:
        st.metric(label="Number of errors", value=n_errors)

    with c3:
        st.metric(label="Source", value=collection_info["source"])
        st.caption("origin_data_record")

    with c4:
        st.metric(label="Target", value=collection_info["target"])
        st.caption(collection_info["main_coll"])

    if len(coll_recent_runs) > 0:

        st.dataframe(
            {
                "Job ID"        : coll_recent_runs_df["_id"],
                "Status"        : coll_recent_runs_df["status"],
                "Date"          : pd.to_datetime(coll_recent_runs_df["date"]),
                "Duration"      : coll_recent_runs_df["total_time"],
                "Rows queried"  : coll_recent_runs_df["rows_queried"],
                "Rows added"    : coll_recent_runs_df["rows_added"],
            },
            hide_index=True
        )

        job_id = st.selectbox(
            label   = "Select Job ID to view logs",
            options = coll_recent_runs_df["_id"]
        )

        with st.container(border=True):
            st.write(f"**Logs for job {job_id}**")
            job = [i for i in coll_recent_runs if i["_id"] == job_id]
            for idx, step in enumerate(job[0]["logs"]):
                st.divider()
                st.write(f"**{idx+1}) {step}**")
                for detail in job[0]["logs"][step]:
                    st.write(f"{detail}: {job[0]["logs"][step][detail]}")

st.subheader("3) Volume Monitoring")

recent_counts_1 = get_recent_counts(collection_info["collections"][0])
recent_counts_2 = get_recent_counts(collection_info["collections"][1])
x_axis = [
    datetime.now() - timedelta(days=i) for i in range(7)
]

with st.container(border=True):

    st.subheader("Past 7 days")
    st.divider()

    import altair as alt

    series_map = {
        collection_info["collections"][0]: recent_counts_1,
        collection_info["collections"][1]: recent_counts_2,
    }

    df = pd.DataFrame({"x": x_axis, **{k: v for k, v in series_map.items()}})

    long = df.melt(id_vars="x", var_name="series", value_name="value")

    vals = pd.to_numeric(long["value"], errors="coerce")

    ymin = float(vals.min()) - 100
    ymax = float(vals.max()) + 100
    y_scale = alt.Scale(domain=[ymin, ymax], nice=False)
    if ymin == ymax:
        y_scale = alt.Scale()

    chart = (
        alt.Chart(long)
        .mark_line()
        .encode(
            x=alt.X("x:T", title="Date"),
            y=alt.Y("value:Q", title="Count", scale=y_scale),
            color=alt.Color("series:N", title=None),
        )
        .properties(height=260)
    )

    st.altair_chart(chart, use_container_width=True)

