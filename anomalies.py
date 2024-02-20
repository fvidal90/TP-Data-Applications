import io
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from sklearn.ensemble import IsolationForest


def get_anomalous_airport(
    df, airport, model=IsolationForest, random_state=42, contamination=0.05
):
    clf = model(random_state=random_state, contamination=contamination)
    df_airport = df[df.ORIGIN == airport].copy()
    X = [[x] for x in df_airport.DEP_DELAY.values]
    clf.fit(X)
    df_airport.loc[:, "prediction"] = clf.predict(X)
    df_airport.loc[:, "prediction_2"] = 1
    df_airport["anomaly"] = df_airport.prediction.apply(
        lambda x: False if x == 1 else True
    )
    return df_airport


def plot_anomalous_airport(df, airport, year):
    X_outliers = df[df.prediction == -1]
    # plt.style.context(("seaborn", "ggplot")):
    plt.scatter(
        X_outliers["FL_DATE"],
        X_outliers["DEP_DELAY"],
        c="tab:red",
        label="Anomaly",
    )
    plt.plot(df["FL_DATE"], df["DEP_DELAY"], c="tab:green", label="Number of flights")
    plt.legend(loc="upper right", bbox_to_anchor=(0.35, 1.15))
    plt.title(f"{airport} {year}")
    plt.xlim([datetime(year - 1, 12, 16), datetime(year + 1, 1, 15)])

    load_data_and_charts(plt, year, airport)
    plt.clf()


def get_delay_average(year):
    df = pd.read_csv(f"files/{year}.csv")
    # df = pd.read_csv('files/2014.csv', usecols=['FL_DATE', 'ORIGIN', 'DEP_DELAY'])
    df = df[df.DEP_DELAY > 0]
    return (
        df.groupby(["FL_DATE", "ORIGIN"])
        .DEP_DELAY.mean()
        .reset_index()
        .sort_values(["ORIGIN", "FL_DATE"])
    )


def get_delay_count(year):
    df = pd.read_csv(f"files/{year}.csv")
    # df = pd.read_csv('files/2014.csv', usecols=['FL_DATE', 'ORIGIN', 'DEP_DELAY'])
    df = df[df.DEP_DELAY > 0]
    return (
        df.groupby(["FL_DATE", "ORIGIN"])
        .DEP_DELAY.count()
        .reset_index()
        .sort_values(["ORIGIN", "FL_DATE"])
    )


def get_anomalous_days(year):
    df_delay = get_delay_average(year)
    df_delay["FL_DATE"] = pd.to_datetime(df_delay.FL_DATE)
    df_anomalies = pd.DataFrame()
    for airport in set(df_delay.ORIGIN.values):
        clf = IsolationForest(random_state=42, contamination=0.05)
        df_airport = df_delay[df_delay.ORIGIN == airport].copy()
        X = [[x] for x in df_airport.DEP_DELAY.values]
        clf.fit(X)
        df_airport["prediction"] = clf.predict(X)
        df_anomalies = df_anomalies.append(df_airport)
    return df_anomalies


def get_anomalous_days_count(year):
    df_delay = get_delay_count(year)
    df_delay["FL_DATE"] = pd.to_datetime(df_delay.FL_DATE)
    df_airports_dict = dict()
    for airport in set(df_delay.ORIGIN.values):
        df_airports_dict[airport] = get_anomalous_airport(df_delay, airport)
    return df_airports_dict


def plot_anomalous_days(df_anomalous_dict, year):
    Path(f"./{year}").mkdir(parents=True, exist_ok=True)
    for airport in df_anomalous_dict.keys():
        plot_anomalous_airport(df_anomalous_dict[airport], airport, year)


def load_data_and_charts(plt, year, airport):
    plt.savefig(f"{year}/fig-{airport}.png", format="png", bbox_inches="tight")
    img_data = io.BytesIO()
    plt.savefig(img_data, format="png", bbox_inches="tight")
    img_data.seek(0)
    img_data.getbuffer()


"""
from anomalies import get_anomalous_days_count
from sklearn.ensemble import IsolationForest
clf = IsolationForest(random_state=42,contamination=0.05)
df =get_anomalous_days_count(2009)
from anomalies import plot_anomalous_days
plot_anomalous_days(df,2009)
#from anomalies import load_data_and_charts
#load_data_and_charts(plt,2015,"BUF")
"""

"""
from anomalies import get_anomalous_days_count
df_dict = get_anomalous_days_count(2015)
from anomalies import plot_anomalous_days
plot_anomalous_days(df_dict,2015)
"""
