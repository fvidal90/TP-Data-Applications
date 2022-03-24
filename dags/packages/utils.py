"""Functions to be used in airflow DAG."""
import io
from datetime import datetime

import matplotlib.pyplot as plt
import s3fs
from sklearn.ensemble import IsolationForest


def extract_year(ds):
    """Returns year from airflow ds macro.

    Parameters
    ----------
        ds: str
            Date in str Y-m-d format.
    Returns
    -------
        year: int
            Year from str date format.
    """
    year = datetime.strptime(ds, "%Y-%m-%d").year
    return year


def get_anomaly_days_airport(
    df, airport, model=IsolationForest, random_state=42, contamination=0.05
):
    """Returns a pandas.DataFrame reporting anomalies.

    Parameters
    ----------
        df: pandas.DataFrame
            Data in pandas.DataFrame format.
        airport: str
            Airport to examine anomaly days.
        model: sklearn.Ensemble
            Model to classify days between regular and anomaly.
        random_state: int
            Random state used in model fitting.
        contamination: float
            Ratio of anomaly days.
    Returns
    -------
        df_airport: pandas.DataFrame
            Data with anomaly days per airport in pandas.DataFrame format.
    """
    print(f"Getting anomaly days for airport: {airport}")
    clf = model(random_state=random_state, contamination=contamination)
    df_airport = df[df.origin == airport].copy()
    delay_count_median = df_airport.dep_delay_count.median()
    x_fit = [
        [x]
        for x in df_airport[
            df_airport.dep_delay_count >= delay_count_median
        ].dep_delay_mean.values
    ]
    clf.fit(x_fit)
    predictions = clf.predict(x_fit)
    df_airport.loc[:, "prediction"] = 1
    df_airport.loc[
        df_airport.dep_delay_count >= delay_count_median, "prediction"
    ] = predictions
    df_airport["anomaly"] = df_airport.prediction.apply(
        lambda x: False if x == 1 else True
    )
    return df_airport


def get_chart_airport(df, airport, year, bucket):
    """Generates and saves charts with anomalies into s3.

    Parameters
    ----------
        df: pandas.DataFrame
            Data to generate chart.
        airport: str
            Airport related to chart.
        year: int
            Year related to chart.
        bucket: str
            Bucket where chart is saved.
    """
    print(f"Generating and saving chart for airport: {airport}")
    df_complete_airport = df[df.origin == airport].copy()
    df_complete_airport.sort_values("fl_date", inplace=True)
    df_anomalies = df_complete_airport[df_complete_airport.anomaly].copy()
    plt.plot(
        df_complete_airport["fl_date"],
        df_complete_airport["dep_delay_count"],
        c="tab:green",
        label="Number of flights",
    )
    plt.scatter(
        df_anomalies["fl_date"],
        df_anomalies["dep_delay_count"],
        c="tab:red",
        label="Anomaly",
    )
    plt.legend(loc="upper right", bbox_to_anchor=(0.35, 1.15))
    plt.title(f"{airport} {year}")
    plt.xlim([datetime(year - 1, 12, 16), datetime(year + 1, 1, 15)])

    save_chart_to_s3(plt, airport, year, bucket)
    plt.clf()


def save_chart_to_s3(plot, airport, year, bucket):
    """Saves chart into S3.

    Parameters
    ----------
        plot: matplotlib.pyplot
            Chart to be saved into s3.
        airport: str
            Airport related to chart.
        year: int
            Year related to chart.
        bucket: str
            Bucket where chart is saved.
    """
    img_data = io.BytesIO()
    plot.savefig(img_data, format="png", bbox_inches="tight")
    img_data.seek(0)

    s3 = s3fs.S3FileSystem(anon=False)
    with s3.open(
        f"s3://{bucket}/reports/{year}/{airport}/fig-{airport}-{year}.png", "wb"
    ) as f:
        f.write(img_data.getbuffer())
