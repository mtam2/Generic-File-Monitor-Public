import cloudpickle
import numpy as np
import pandas as pd
import random
import re
import copy
import os
from outlier import Outlier
from datetime import date, datetime, timedelta
from flask import Flask, render_template, request
from sklearn.ensemble import IsolationForest

# Generates a Outlier object if none exists in current directory
if not os.path.isfile("outlier.pickle"):
    a = Outlier()
    outlier_file = open('outlier.pickle', 'wb')
    cloudpickle.dump(a, outlier_file)
    outlier_file.close()

app = Flask(__name__)


@app.route('/')
def home(chart_id='chart_ID', chart_type='line'):
    """
    Purpose:
        Displays Highcharts Outlier data to localhost:8080/
    Args:
        /?days=### (Optional): How many days in the past to display
        /?filter= (Optional): all, lower, item_header for specific interfaces
    Returns:
        Renders all.html template with Outlier JSON data
    @TODO:
        UNCOMMENT OUT IF STATEMENTS IF DEPLOYED TO PRODUCTION
    """

    outlier_file = open('outlier.pickle', 'rb')
    a = cloudpickle.load(outlier_file)
    # if a.last_updated_hour != datetime.today().hour:
    #     from outlier import Outlier
    #     a = Outlier()
    #     a.last_updated_hour = datetime.today().hour
    #     outlier_file = open('outlier.pickle', 'wb')
    #     cloudpickle.dump(a, outlier_file)
    #     outlier_file.close()

    trainingdf = a.get_df()

    dates = [d.strftime('%Y-%m-%d') for d in
             pd.date_range(trainingdf['date'][0], trainingdf['date'][len(trainingdf) - 1])]

    # localhost:8080/?days=###, defaults to maximum days
    days = request.args.get('days', str(len(dates)))
    # localhost:8080/?filter={all, lower, item_header}, defaults to first interface
    filter_flag = request.args.get('filter', 'all')

    if days.isdigit():
        days = int(days)
        if days > len(dates) or days <= 0:
            days = len(dates)
    else:
        days = len(dates)
    dates = dates[len(dates) - days:]

    outliers_dictionary = copy.deepcopy(a.outliers_dictionary)

    for series in range(0, len(outliers_dictionary)):

        min_index = len(outliers_dictionary[series]['data']) - days

        outliers_dictionary[series]['data'] = outliers_dictionary[series]['data'][-days:]

        for outlier in range(0, len(outliers_dictionary[series]['number_of_outliers'])):
            outliers_dictionary[series]['number_of_outliers'][outlier] -= min_index
        outliers_dictionary[series]['number_of_outliers'] = [
            x for x in outliers_dictionary[series]['number_of_outliers'] if x >= 0]

    series_list = [{'name': outliers_dictionary[i]['interface'] + outliers_dictionary[i]
                    ['file_name'], 'data': outliers_dictionary[i]['data']} for i in range(len(outliers_dictionary))]
    outliers_list = [outliers_dictionary[i]['number_of_outliers']
                     for i in range(len(outliers_dictionary))]

    series = series_list
    title = {"text": 'All SST Feeds'}
    xAxis = {"categories": dates}
    yAxis = {"title": {"text": 'File Count'}}
    chart = {"type": chart_type,
             "series": series_list, "xAxis": xAxis,
             "yAxis": yAxis, "title": title}

    outlier_file.close()
    return render_template('all.html', chart_id=chart_id, chart=chart,
                           series=series, title=title, xAxis=xAxis,
                           yAxis=yAxis, outliers=outliers_list,
                           filter_flag="\"" + filter_flag + "\"")


@app.route('/date')
def date_page():
    """
    Purpose:
        Displays Highcharts outliers for a specific day per hour
    Args:
        /date?date=YYYY-MM-DD: If invalid date format, defaults to today
    Returns: 
        Renders hourly.html template with Outlier JSON data
    """

    outlier_file = open('outlier.pickle', 'rb')
    a = cloudpickle.load(outlier_file)

    # if (a.last_updated_hour != datetime.today().hour) | (a.full_hour_traindata == ''):
    #     a = Outlier()
    #     a.last_updated_hour = datetime.today().hour
    #     a.full_hour_traindata = a.create_full_hour_traindata(a.trainingdf)
    #     outlier_file = open('outlier.pickle', 'wb')
    #     cloudpickle.dump(a, outlier_file)
    #     outlier_file.close()

    raw_data = a.trainingdf

    date = a.validate_date(request.args.get('date'))
    calculated_day_data = a.hourly_to_json(
        a.hourly_df(date, raw_data), raw_data, date)

    outlier_dic_list = a.get_hourly_outliers(
        date, outliers_fraction=.06, n_estimate=24)

    outliers_list = [i['number_of_outliers'] for i in outlier_dic_list]

    xAxis = {"categories": ['00:00', '01:00', '02:00', '03:00', '04:00',
                            '05:00', '06:00', '07:00', '08:00', '09:00',
                            '10:00', '11:00', '12:00', '13:00', '14:00',
                            '15:00', '16:00', '17:00', '18:00', '19:00',
                            '20:00', '21:00', '22:00', '23:00']}

    yAxis = {"title": {"text": 'File count'}}
    title = str(date)

    chart = {"type": 'lines',
             "series": calculated_day_data['series_list'], "xAxis": xAxis,
             "yAxis": yAxis, "title": title}

    return render_template('hourly.html',
                           calculated_day_date=calculated_day_data,
                           series=calculated_day_data['series_list'],
                           date=[str(date)],
                           chart=chart,
                           outliers=outliers_list
                           )


@app.route('/counter')
def counter():
    """
    Purpose:
        Displays numbers of days since last outlier and if any files are missing from the DB.
    """

    outlier_file = open('outlier.pickle', 'rb')
    a = cloudpickle.load(outlier_file)

    # if (a.last_updated_hour != datetime.today().hour) | (a.full_hour_traindata == ''):
    #     a = Outlier()
    #     a.last_updated_hour = datetime.today().hour
    #     a.full_hour_traindata = a.create_full_hour_traindata(a.trainingdf)
    #     outlier_file = open('outlier.pickle', 'wb')
    #     cloudpickle.dump(a, outlier_file)
    #     outlier_file.close()

    df = a.get_df()
    outliers_dictionary = copy.deepcopy(a.outliers_dictionary)

    outliers_list = [outliers_dictionary[i]['number_of_outliers']
                     for i in range(len(outliers_dictionary))]
    combined_outlier_list = sum(outliers_list, [])
    is_outlier_day_list = []
    temp_percents = []
    count = 0

    # days_length = max(combined_outlier_list)
    days_length = (df['date'][len(df['date']) - 1] - df['date'][0]).days
    for e in range(0, days_length):
        temp = combined_outlier_list.count(e) / len(outliers_list)
        temp_percents.append(temp)
        if temp >= .2:
            is_outlier_day_list.append(1)
        else:
            is_outlier_day_list.append(0)
    for w in reversed(is_outlier_day_list):
        if w == 0:
            count += 1
        else:
            break

    date = datetime.today().strftime('%Y-%m-%d')

    outlier_dic_list = a.get_hourly_outliers(
        date, outliers_fraction=.06, n_estimate=24)

    outliers_list = [i['number_of_outliers'] for i in outlier_dic_list]

    hour_now = datetime.now().hour - 1

    db_filelist = a.check_DB()
    if len(db_filelist) == 0:
        files = 0
    else:
        files = str(db_filelist)

    if datetime.now().hour == 0:
        date = datetime.today().strftime('%Y-%m-%d') - datetime.timedelta(days=1)
        hour_now = 23

    counter = 0
    for i in outliers_list:
        for x in i:
            if x == hour_now:
                counter += 1

    percent = counter / len(outliers_list)

    if percent >= 0.35:
        # print("Current hour " + str(hour_now) + " is an anomaly")
        anomaly = "Interface anomaly between " + str(hour_now) + ":00 - " + str(
            hour_now + 1) + ":00 detected, please check the files."
        anomaly_flag = 1
    else:
        # print("Current hour " + str(hour_now) + " is okay")
        anomaly = "Between " + \
            str(hour_now) + ":00 - " + str(hour_now + 1) + \
            ":00 interface status is normal."
        anomaly_flag = 0

    outlier_file.close()

    return render_template('counter.html', count=count,
                           anomaly="\"" + anomaly + "\"",
                           anomaly_flag=anomaly_flag, files=files)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
