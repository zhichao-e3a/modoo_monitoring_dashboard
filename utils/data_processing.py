import pandas as pd
from datetime import timedelta, datetime

def get_labor_onset(row, actual_delivery_str):

    """
    Date of labor onset
    ADD - c1
    ADD - (c2 + c3) if c1 not present
    """

    add = datetime.strptime(actual_delivery_str, "%Y-%m-%d %H:%M:%S")
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

    if onset:
        return onset.strftime("%Y-%m-%d %H:%M:%S")

    return onset

def format_excel_data(main_df, pre_df):

    merged_df = pd.merge(main_df, pre_df, left_on="联系方式", right_on="2.电话号码", how="left")

    formatted_data  = []

    for idx, row in merged_df.iterrows():

        if pd.isna(row["联系方式"]):
            continue

        # last_menstrual_str        %d/%m/%Y            (str)                   Nullable (None)
        # expected_delivery_date    %Y-%m-%d            (timestamps.Timestamp)  Non-nullable
        # actual_delivery_date      %Y-%m-%d            (timestamps.Timestamp)  Nullable (NaT)
        # actual_delivery_time      HH:MM:SS            (datetime.time)         Nullable (Float)
        # onset_time (obtained)     %Y-%m-%d HH:MM:SS   (timestamps.Timestamp)  Nullable (NaT)
        # onset_date                %Y-%m-%d            (timestamps.Timestamp)  Nullable (NaT)
        # onset_time                %Y-%m-%d            (datetime.time)         Nullable (Float)

        contact                     = row["联系方式"]
        data_origin                 = row["data_origin"]
        delivery_mode               = row["delivery_mode"] if not pd.isna(row["delivery_mode"]) else None

        # Last Menstrual Time
        last_menstrual_str          = row["7.您的最后一次月经大概是什么时候？"]
        last_menstrual              = datetime.strptime(
            last_menstrual_str,
            "%d/%m/%Y"
        ).strftime("%Y-%m-%d %H:%M:%S") if not pd.isna(last_menstrual_str) else None
        # last_menstrual : %Y-%m-%d %H:%M:%S or None

        # Expected Delivery Time
        expected_delivery_date = row["预产期"]
        expected_delivery  = expected_delivery_date.strftime("%Y-%m-%d %H:%M:%S")
        # expected_delivery : %Y-%m-%d %H:%M:%S

        # Actual Delivery Time
        actual_delivery_date    = row["实际出生日期"]
        actual_delivery_time    = row["实际出生时间 (HH:MM:SS)"]
        actual_delivery         = None
        if not pd.isna(actual_delivery_date) and not pd.isna(actual_delivery_time):
            actual_delivery = datetime.combine(
                actual_delivery_date.to_pydatetime().date(),
                actual_delivery_time
            ).strftime("%Y-%m-%d %H:%M:%S")
        elif not pd.isna(actual_delivery_date):
            actual_delivery = actual_delivery_date.strftime("%Y-%m-%d %H:%M:%S")
        # actual_delivery : %Y-%m-%d %H:%M:%S or None

        # Onset Time
        onset = None
        if row["delivery_mode"] != "c-section": # If C-section delivery, onset not used

            if data_origin == "recruited": # If Recruited use actual delivery (if exists) to calculate

                if not pd.isna(actual_delivery):
                    onset = get_labor_onset(row, actual_delivery)

            elif data_origin == "historical": # If historical derive from Excel field directly

                onset_date = row["onset_date"]
                onset_time = row["onset_time (HH:MM)"]
                if not pd.isna(onset_date) and not pd.isna(onset_time):
                    onset = datetime.combine(
                        onset_date.to_pydatetime().date(),
                        onset_time
                    ).strftime("%Y-%m-%d %H:%M:%S")
                elif not pd.isna(onset_date):
                    onset = onset_date.strftime("%Y-%m-%d %H:%M:%S")

        data = {
            "contact"                   : str(int(contact)),
            "data_origin"               : data_origin,
            "delivery_mode"             : delivery_mode,
            "last_menstrual"            : last_menstrual,
            "expected_delivery"         : expected_delivery,
            "actual_delivery"           : actual_delivery,
            "onset"                     : onset
        }

        formatted_data.append(data)

    return formatted_data

def consolidate_data(patients, measurements, data_origin):

    patients_df     = pd.DataFrame(patients)
    measurements_df = pd.DataFrame(measurements)

    merged          = pd.merge(
        measurements_df,
        patients_df,
        left_on     = "mobile",
        right_on    = "_id",
        how         = "left"
    )

    consolidated_data = []

    for idx, row in merged.iterrows():

        data = {
            "row_id"            : row["_id_x"],
            "mobile"            : row["mobile"],
            "measurement_date"  : row["measurement_date"],
            "uc"                : row["uc"],
            "fhr"               : row["fhr"],
            "gest_age"          : row["gest_age"],
            "onset"             : row["onset"]
        }

        if data_origin == "recruited":
            data["edd"] = row["expected_delivery"]
            data["add"] = row["actual_delivery"]
        elif data_origin == "historical":
            data["edd"] = row["expected_delivery_x"]
            data["add"] = row["actual_delivery_x"]

        if not row["gest_age"] and not row["last_menstrual_datetime"]:

            diff = datetime.strptime(row["measurement_date"], "%Y-%m-%d %H:%M:%S") - datetime.strptime(row["last_menstrual_datetime"], "%Y-%m-%d %H:%M:%S")
            data["gest_age"] = diff.days

        consolidated_data.append(data)

    return consolidated_data

