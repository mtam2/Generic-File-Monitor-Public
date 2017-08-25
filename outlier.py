"""
Generic File Monitor Main Class
Authors: Maxim Tam, Daniel Tremer
---
This class holds all methods to proccess a CSV of regularly scheduled files
and output any anomolies incosistent with the time or day. The CSV this class
uses is generated by a PowerShell script to retrieve filename and timestamps
of a directory. This was developed for Porsche Cars North America to detect
inconsistent file transfers.
"""
import re
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


class Outlier(object):

    def __init__(self):
        # Replace hostname with servername where the files are located and generated

        # date_string = str(datetime.today().strftime('%m_%d_%Y'))
        # self.raw_path = '\\\\hostname\Summary\DirList_' + date_string + '.csv'
        # self.raw_db = pd.read_csv("\\\\hostname\\Summary\\list.txt")
        self.raw_path = "./data/DirList_06_26_2017.csv"
        self.raw_db = pd.read_csv("./data/list.txt")
        self.last_updated_hour = ''
        self.last_updated_day = ''
        self.trainingdf = self.get_df()
        self.outliers_dictionary = self.get_daily_outliers(self.trainingdf,
                                                           self.trainingdf, outliers_fraction=.3,
                                                           n_estimate=8)
        self.full_hour_traindata = ''
        # Due to performance issues, hourly outlier calculations will only be done ad hoc
        # self.full_hour_traindata = self.create_full_hour_traindata(self.trainingdf)

    def accumulate_sum_per_day_per_name(self, df):
        """
        Purpose:
            Generates a DataFrame that counts the amount of a particular file
            per day.
        Args:
            df (Pandas DataFrame): A very specifically formatted DataFrame
                dataframe from csv with columns: date, time, hour, size, name
        Returns:
            DataFrame with rows of each day and columns of file count for each
            file category.
        """
        unique_names = df['name'].unique()
        # Calculates true date range regardless of missing or zero file days
        dates = pd.date_range(df['date'][0], df['date'][len(df) - 1])
        # Establish base dataframe with dates and day of week
        daily = pd.DataFrame(index=dates)
        daily.insert(0, "date", dates)
        days = []
        unique_dates = daily['date'].unique()

        for val in range(len(daily)):
            days.append(daily['date'][val].dayofweek)
        daily.insert(1, "day", days)

        # Populates dataframe with count of filename per day
        for name in unique_names:
            temp = []
            for date in unique_dates:
                temp.append(df[(df['name'] == name) & (
                    df['date'] == date)].date.count())
            daily.insert(len(daily.columns), name, temp)

        return daily

    def calculate_outliers(self, full_training_array, val_data, outliers_fraction=0.3, n_estimators=4):
        """
        Purpose:
            Using training data to detect outliers with Isolation Forest from Scikit-learn.
        Args:
            full_training_array: array of training data
                Format: [[x] for x in accumulate_sum_per_day_per_name(get_df())[name].tolist()]
            val_data: array of target data
                Format: Same as above
            outliers_fraction: estimated outlier percentage
            n_estimators (int): estimated number of outlier groups
        Returns:
            y_pred_test: array of [1 for not outliers and -1 for outliers]
            number_of_outlier: array of outlier positions in the array
        """
        rng = np.random.RandomState(42)
        # Generate train data
        x_train = full_training_array
        x_test = val_data
        # fit the model
        clf = IsolationForest(n_estimators=n_estimators,
                              random_state=rng,
                              contamination=outliers_fraction)
        clf.fit(x_train)
        y_pred_train = clf.predict(x_train)
        y_pred_test = clf.predict(x_test)
        # y_pred_outliers = clf.predict(X_outliers)
        count = 0
        number_of_outlier = []
        for i in y_pred_test:
            if i == -1:
                number_of_outlier.append(count)
            count += 1
        return y_pred_test, number_of_outlier

    def get_daily_outliers(self, trainingdf, df, outliers_fraction=.3, n_estimate=8):
        """
        Purpose:
            Uses training data to detect outliers of an unknown set of file count per
            filename per day.
        Args:
            trainingdf (DataFrame): Pre-classified normal data, get_df()
            df (DataFrame): unclassified data, get_df()
            outliers_fraction (float): estimated outlier percentage
            n_estimate (int): estimated number of outlier groups
        Returns:
            Dictionary with interface name, file name, file count, and outlier sequence number
        """
        training_df = self.accumulate_sum_per_day_per_name(trainingdf)
        target_df = self.accumulate_sum_per_day_per_name(df)
        unique_names = df['name'].unique()
        outlier_list = []
        for name in unique_names:
            training_array = [[x] for x in training_df[name].tolist()]
            target_array = [[x] for x in target_df[name].tolist()]

            y_pred_test, number_of_outlier = (
                self.calculate_outliers(training_array, target_array, outliers_fraction, n_estimate))
            # If the model determines all the values as outliers, noise will be added to the data and retrained
            if (len(np.unique(y_pred_test)) == 1) & (np.unique(y_pred_test)[0] == -1):
                mean = np.median(training_array)
                for noise in range(35):
                    training_array.append([int(mean)])
                y_pred_test, number_of_outlier = self.calculate_outliers(
                    training_array, target_array, .1, 4)
                number_of_outlier = [
                    i for i in number_of_outlier if i < len(target_array)]
                # If the model still determines all the values as outliers, all values beyond the median will be labeled as outliers
                if (len(np.unique(y_pred_test)) == 1) & (np.unique(y_pred_test)[0] == -1):
                    y_pred_test = []
                    for x in target_array:
                        if x[0] != mean:
                            y_pred_test.append(-1)
                        else:
                            y_pred_test.append(1)
                    count = 0
                    number_of_outlier = []
                    for i in y_pred_test:
                        if i == -1:
                            number_of_outlier.append(count)
                        count += 1

                    # Failed attempt at tupling day of week and filecount
                    # train_arr = [tuple(x) for x in training_df[[name,'day']].values]
                    # real_arr = [tuple(x) for x in data[[name,'day']].values]
                    # y_pred_test, number_of_outlier = self.calculate_outliers(train_arr, real_arr, .05, 8)

            interface = re.search(r'([A-Z]{3}[0-9]{4})', name).group(1)
            file_name = re.sub(r'([A-Z]{3}[0-9]{4})', '', name)
            outlier_list.append({"interface": interface, "file_name": file_name, 'data': target_df[name].tolist(),
                                 "number_of_outliers": number_of_outlier})

        return outlier_list

    def get_hourly_outliers(self, date, outliers_fraction=.3, n_estimate=8):
        """
        Purpose:
            Uses training data to detect outliers of an unknown set of file count per
            filename per day per hour.
        Args:
            date (str): target date in YYYY-MM-DD format
            outliers_fraction (float): estimated outlier percentage
            n_estimate (int): estimated number of outlier groups
        Returns:
            Dictionary with interface name, file name, file count, and outlier sequence number
        """
        raw_data = self.trainingdf
        unique_names = self.trainingdf['name'].unique()
        outlier_list = []

        for name in unique_names:
            validation_data = []
            calculated_day_data = self.hourly_to_json(self.hourly_df(
                str(date)[:10], raw_data), raw_data, str(date)[:10])
            validation_data.append(calculated_day_data)

            tmp = []
            for element in validation_data:
                for series in element['series_list']:
                    if series['name'] == name:
                        for i in range(24):
                            tmp.append([element['day'], i, series['data'][i]])

            test_data = tmp

            training_tmp = []
            for i in self.full_hour_traindata:
                if i['name'] == name:
                    training_tmp.append(i['data'])

            y_pred_test, number_of_outlier = (
                self.calculate_outliers(training_tmp, test_data, outliers_fraction, n_estimate))

            interface = re.search(r'([A-Z]{3}[0-9]{4})', name).group(1)
            file_name = re.sub(r'([A-Z]{3}[0-9]{4})', '', name)

            data = []
            for i in calculated_day_data['series_list']:
                if i['name'] == name:
                    data = i['data']

            outlier_list.append({"interface": interface, "file_name": file_name, 'data': data,
                                 "number_of_outliers": number_of_outlier})

        return outlier_list

    def get_df(self):
        """
        Purpose:
            Generates a Pandas DataFrame from parsing the CSV specified in the
            class constructor.
            CSV Format: date(dd.mm.yyyy), time(hh:mm), size(bytes), file name
        Args:
            None.
        Returns:
            DataFrame with columns: date, time, hour, size, name
        """
        # Reads CSV file to local
        raw_df = pd.read_csv(self.raw_path)
        # Removes all unique ID tails from filenames and converts date string to datetime datatype
        raw_df = raw_df[raw_df.name.str.match(
            '.*SST.*')].reset_index(drop=True)
        raw_df['name'] = raw_df['name'].str.replace(r"_20[0-9]*.*$", "")
        raw_df['date'] = raw_df['date'].str.replace(".", "")
        raw_df['date'] = pd.to_datetime(raw_df['date'], format='%m%d%Y')
        # Inserts raw hour column
        temp_hours = []

        for x in range(len(raw_df)):
            temp_hours.append(
                raw_df['time'][x][0:raw_df['time'][x].index(":")])
        raw_df.insert(2, "hour", temp_hours)
        raw_df = raw_df.sort_values('date').reset_index(drop=True)

        return raw_df

    def hourly_df(self, date, raw_data):
        """
        Purpose:
            Generate DataFrame for a specific date for outlier preproccessing
        Args:
            date (str): target date in YYYY-MM-DD format
            raw_data (DataFrame): self.trainingdf
        Returns:
            DataFrame with day, hours 00-23, file count, interface name
        """
        parsed_date = datetime.strptime(date, '%Y-%m-%d')
        #   Isolate dataframe to user input day
        raw_data = raw_data[raw_data['date'] == parsed_date]
        raw_data = raw_data.groupby(
            ['date', 'hour', 'name']).count().reset_index()
        unique_names = raw_data['name'].unique()

        #   Generate dataframe with zeroes
        labels = ['Date', 'Day', 'Name', 'Count']
        all_df = pd.DataFrame(columns=labels)
        hours = []
        names = []
        for hour in range(0, 24):
            for name in unique_names:
                hours.append(hour)
                names.append(name)
        all_df.insert(2, 'Hour', hours)
        all_df['Date'] = parsed_date
        all_df['Day'] = parsed_date.weekday()
        all_df['Name'] = names
        all_df['Count'] = 0

        for i in range(0, len(raw_data)):
            all_df_row = all_df.loc[
                (all_df['Name'] == raw_data['name'][i]) & (all_df['Hour'] == int(raw_data['hour'][i]))]
            all_df.set_value(
                all_df_row.index[0], 'Count', raw_data.loc[i].time)

        return all_df

    def hourly_to_json(self, full_hour_data, raw_data, date_get):
        """
        Purpose:
            Outputs a JSON String for Highcharts to read
        Args:
            Input: create_full_hour_traindata(trainingdf), trainingdf, a date in YYYY-MM-DD format
            full_hour_data (DataFrame): create_full_hour_traindata(trainingdf)
            raw_data (DataFrame): trainingdf
            date_get (str): target date in YYYY-MM-DD format from GET request
        Returns:
            Dictionary with day, hours 00-23, file count, interface name
        """
        date_get = datetime.strptime(date_get, '%Y-%m-%d')
        names = raw_data['name'].unique()
        hours = []
        series_list = []
        result = {}
        for hour in range(0, 24):
            hours.append(str(hour) + ':00')

        if full_hour_data.empty:

            for name in names:
                temp = {'name': name, 'data': [0] * 24}
                series_list.append(temp)

        else:
            for name in names:

                if not full_hour_data[full_hour_data['Name'] == name]['Count'].tolist():
                    temp = {'name': name, 'data': [0] * 24}
                    series_list.append(temp)
                else:
                    temp = {
                        'name': name, 'data': full_hour_data[full_hour_data['Name'] == name]['Count'].tolist()}
                    series_list.append(temp)

        result['day'] = date_get.weekday()
        result['hours'] = hours
        result['series_list'] = series_list
        return result

    def create_full_hour_traindata(self, raw_data):
        """
        Purpose:
            Creates a dictionary of file count per filename per day per hour
        Args:
            raw_data (DataFrame): Trainingdf
        Returns:
            Dictionary with interface name, [day of week, hour, file count]
        WARNING:
            TAKES A LONG TIME TO CALCULATE
        """
        dates = [d.strftime('%Y-%m-%d') for d in
                 pd.date_range(raw_data['date'][0], raw_data['date'][len(raw_data) - 1])]
        full_hour_traindata = []

        for date in dates:
            calculated_day_data = self.hourly_to_json(self.hourly_df(str(date)[:10], raw_data), raw_data,
                                                      str(date)[:10])
            full_hour_traindata.append(calculated_day_data)

        tmp_training = []
        for element in full_hour_traindata:
            for series in element['series_list']:
                for i in range(24):
                    tmp_training.append({'name': series['name'], 'data': [
                                        element['day'], i, series['data'][i]]})

        return tmp_training

    def check_DB(self):
        """
        Purpose:
            There exists a database table that has the filenames of the
            files that SHOULD be in the directory. This method finds the
            missing files.
        Args:
            None.
        Returns:
            List of files that are in the database but not in the CSV.
        """
        result = []
        for line in range(len(self.raw_db)):
            result += (self.raw_db.loc[line][0] + ';').split(';')
        result = [x.strip(' ') for x in result]
        result = [x for x in result if "SST" in x]
        dirlist = pd.read_csv(self.raw_path)
        dirlist['date'] = dirlist['date'].str.replace(".", "")
        dirlist['date'] = pd.to_datetime(dirlist['date'], format='%m%d%Y')
        namelist = dirlist[(dirlist['date'] > datetime.today(
        ) - timedelta(days=2))]['name'].tolist()
        return list(set(result) - (set(result) & set(namelist)))

    def validate_date(self, date):
        """
        Purpose:
            Validates a string to be in YYYY-MM-DD format.
        Args:
            date (str): Any string
        Returns:
            Date String in YYYY-MM-DD if input is in that format or today's date if invalid format
        """
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            return datetime.today().strftime('%Y-%m-%d')
        return date