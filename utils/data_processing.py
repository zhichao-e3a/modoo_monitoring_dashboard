import pandas as pd

def consolidate_data(measurements, patients):

    skipped = {
        "no_onset"  : 0,
        "c_section" : 0
    }

    measurements_df = pd.DataFrame(measurements)
    patients_df     = pd.DataFrame(patients)

    merged          = pd.merge(
        measurements_df,
        patients_df,
        left_on     = "mobile",
        right_on    = "patient_id",
        how         = "left"
    )

    consolidated_data = []

    for idx, row in merged.iterrows():

        if not row["onset_datetime"]:
            skipped["no_onset"] += 1
            continue

        if row["delivery_type"] == "c-section":
            skipped["c_section"] += 1
            continue

        data = {
            "row_id"            : row["_id_x"],
            "mobile"            : row["mobile"],
            "measurement_date"  : row["measurement_date"],
            "start_test_ts"     : row["start_test_ts"],
            "uc"                : row["uc"],
            "fhr"               : row["fhr"],
            "gest_age"          : row["gest_age"],

            # Use expected and actual delivery from the measurements (not from Excel)
            "expected_delivery" : row["expected_delivery"],
            "actual_delivery"   : row["actual_delivery"],

            "onset"             : row["onset_datetime"]
        }

        consolidated_data.append(data)

    return consolidated_data, skipped
