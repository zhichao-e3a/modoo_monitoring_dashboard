from database.DatabaseConnector import DatabaseConnector

import json
import pandas as pd

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
'17301389209',
'18337956926',
'15069301215',
'18629401601',
'17709422618',
'18248211164',
'13602426524',
'15202835896',
'17600526199',
'18989125035',
'13286855587',
'18677933834',
'18043928892',
'18851001927',
'18310057300',
'18711857821',
'15288286223',
'18550807290',
'15652151599',
'15261897383',
'13755619181',
'15022090627',
'17898805632',
'13718500355',
'13466334784',
'13531735227',
'15959171173',
'18733239144',
'15088068036',
'13828353366',
'18420023897',
'13765322064',
'13760308579',
'17326961963',
'17392045528',
'18555218558',
'15601726670',
'13164622273',
'18610926757',
'15101601909',
'18205254928',
'18511762583',
'18513517631',
'18606931203',
'18066288005',
'18801250804',
'18516282171',
'13671697848',
'13851994410',
'15629060979',
'18274898881',
'13066851756',
'17573141019',
'18801901850'
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
