import io
from datetime import datetime

import matplotlib.pyplot as plt
from sklearn.ensemble import IsolationForest
import s3fs


def extract_year(ds):
    return datetime.strptime(ds, '%Y-%m-%d').year


def get_anomalous_days_airport(df, airport, model=IsolationForest, random_state=42, contamination=0.05):
    print(f"Getting anomaly days for airport: {airport}")
    clf = model(random_state=random_state, contamination=contamination)
    df_airport = df[df.origin == airport].copy()
    delay_count_median = df_airport.dep_delay_count.median()
    x_fit = [[x] for x in df_airport[df_airport.dep_delay_count >= delay_count_median].dep_delay_mean.values]
    clf.fit(x_fit)
    preds = clf.predict(x_fit)
    df_airport.loc[:, "prediction"] = 1
    df_airport.loc[df_airport.dep_delay_count >= delay_count_median, 'prediction'] = preds
    df_airport["anomaly"] = df_airport.prediction.apply(lambda x: False if x == 1 else True)
    return df_airport


def save_plot_to_s3(plot, airport, year):
    img_data = io.BytesIO()
    plot.savefig(img_data, format='png', bbox_inches='tight')
    img_data.seek(0)

    s3 = s3fs.S3FileSystem(anon=False)
    with s3.open(f's3://flights-fer/reports/{year}/{airport}/fig-{airport}-{year}.png', 'wb') as f:
        f.write(img_data.getbuffer())


def plot_chart_airport(df, airport, year):
    print(f"Plotting chart for airport: {airport}")
    df_complete_airport = df[df.origin == airport].copy()
    df_complete_airport.sort_values('fl_date', inplace=True)
    df_anomalies = df_complete_airport[df_complete_airport.anomaly].copy()
    plt.plot(df_complete_airport["fl_date"], df_complete_airport["dep_delay_count"], c="tab:green",
             label="Number of flights")
    plt.scatter(df_anomalies["fl_date"], df_anomalies["dep_delay_count"], c="tab:red", label="Anomaly days")
    plt.legend(loc="upper right", bbox_to_anchor=(0.35, 1.15))
    plt.title(f'{airport} {year}')
    plt.xlim([datetime(year - 1, 12, 16), datetime(year + 1, 1, 15)])

    save_plot_to_s3(plt, airport, year)
    plt.clf()
