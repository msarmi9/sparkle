"""
Module for monitoring patient medication adherence.
"""
import io
import pickle
from collections import defaultdict
from datetime import timedelta

import numpy as np

from modeling.preprocessing import preprocess


# TODO: add more options
DOSAGE_TO_FREQ = {
    "QD - 1x per day": {"freq": 1, "freq_repeat": 1, "freq_repeat_unit": "day"},
    "BID - 2x per day": {"freq": 2, "freq_repeat": 1, "freq_repeat_unit": "day"},
    "TID - 3x per day": {"freq": 3, "freq_repeat": 1, "freq_repeat_unit": "day"},
    "QID - 4x per day": {"freq": 4, "freq_repeat": 1, "freq_repeat_unit": "day"},
}

DAY_STD = {"day": 1, "week": 7, "month": 30}


def adherence_model(data):
    """Predict the number of pills remaining given a string of sensor data."""
    classifier_path = "modeling/models/classifier.pkl"
    regressor_path = "modeling/models/regressor.pkl"

    # run the pill classifier process
    X = preprocess(io.StringIO(data), regression=False)
    classifier = pickle.load(open(classifier_path, "rb"))
    classifier_pred = classifier.predict(X).item()

    if classifier_pred == 0:
        pred_string = "It does not appear you took any medication."
        return {
            "pred_string": pred_string,
            "pred_type": "classification",
            "pred": classifier_pred,
        }
    else:
        # run the regression process
        X = preprocess(io.StringIO(data), regression=True)

        regressor = pickle.load(open(regressor_path, "rb"))
        predicted_pills = regressor.predict(X).round().item()
        predicted_pills = max(min(predicted_pills, 30), 1)

        pred_string = f"It looks like you have {predicted_pills - 1} pills remaining."
        return {
            "pred_string": pred_string,
            "pred_type": "regression",
            "pred": predicted_pills,
        }


# TODO: Refactor such that the functions below can go in Prescription class.
def get_next_refill_date(
    last_refill_date, duration, duration_unit, refills, refill_num
):
    """
    Return next refill date based on most recent (last) refill date
    and dosage information.

    last_refill_date: datetime
    duration: int
    duration_unit: string - either 'day', 'week', or 'month'
    refills: int - number of refills for entire treatment
    refill_num: int - the refill the patient is currently on
    """

    if refill_num == refills or refills == 0:
        return None
    days_per_cycle = np.floor(duration * DAY_STD[duration_unit] / (refills + 1))
    return last_refill_date + timedelta(days=days_per_cycle)


def get_days_until_refill(curr_date, next_refill_date):
    """
    Return number of days until next refill.
    If curr_date > next_refill_date, for instance, if refill was not fulfilled
        in time, then days until refill is still 0.

    curr_date: datetime - the date against which next refill date is compared
    next_refill_date: datetime
    """
    if next_refill_date is None:
        return None
    return max([(next_refill_date - curr_date).days, 0])


def adherence_by_drug_name(prescriptions, measure="general"):
    """
    Return average adherence rates by drug name.
    e.g. {'Acetominophen: 0.89', 'Ibuprofen: 0.73'}
    prescriptions: list - list of Prescription objects
    measure: string - measure of adherence, either 'general'
                      (taking the right number of pills expected)
                      or 'ontime' (taking pills at the right time)
    """
    if measure not in ["general", "ontime"]:
        raise ValueError('`measure` must be "general" or "ontime"')
    med_adh = defaultdict(list)
    for rx in prescriptions:
        if measure == "general":
            med_adh[rx.drug].append(rx.frac_required_intakes())
        else:
            med_adh[rx.drug].append(rx.frac_on_time())
    for name in med_adh.keys():
        rates = med_adh[name]
        med_adh[name] = np.mean(rates)
    return med_adh


def least_adhered_by_drug_name(prescriptions, n=5, measure="general"):
    """
    Get least adhered to medications by drug name.
    prescriptions: list - list of Prescription objects
    n: int - how many to return
    measure: string - measure of adherence, either 'general'
                      (taking the right number of pills expected)
                      or 'ontime' (taking pills at the right time)
    """
    med_adh = adherence_by_drug_name(prescriptions, measure=measure)
    sorted_adh = [
        (name, frac)
        for name, frac in sorted(med_adh.items(), key=lambda x: x[1], reverse=True)
    ]
    return sorted_adh[:n]


def most_adhered_by_drug_name(prescriptions, n=5, measure="general"):
    """
    Get most adhered to medications by drug name.
    prescriptions: list - list of Prescription objects
    n: int - how many to return
    measure: string - measure of adherence, either 'general'
                      (taking the right number of pills expected)
                      or 'ontime' (taking pills at the right time)
    """
    med_adh = adherence_by_drug_name(prescriptions, measure=measure)
    sorted_adh = [
        (name, frac)
        for name, frac in sorted(med_adh.items(), key=lambda x: x[1], reverse=True)
    ]
    return sorted_adh[:n]
