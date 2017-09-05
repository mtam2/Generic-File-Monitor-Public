# Tutorial: How to Setup Generic File Monitor
## Introduction
Generic File Monitor is a project developed to check for file anomalies based on historic metadata of received files. The current implementation monitors files on **REDACTED** to check if files are being received on time from **REDACTED**. Although developed in Python, the anomaly detecting algorithm depends on .CSV files generated from Powershell scripts.
## Prerequisites
*   Have Python 3.6 installed 
    *   Use Anaconda https://www.continuum.io/downloads
*   (**IGNORE THIS IF NOT IN PRODUCTION**) service_jiraapi currently runs the following scheduled tasks: 
    *   CSVGetter.ps1 on **REDACTED** every 5 minutes indefinitely
        *   The service account must have admin access to **REDACTED**
    *   DB_filelist.ps1 on **REDACTED** every 5 minutes indefinitely
        *   The service account must have read access to the **REDACTED** table on **REDACTED**
    *   ![](https://i.imgur.com/RNzW94A.png)
    *   ![](https://i.imgur.com/L69v7vv.png)
        *   -ExecutionPolicy Bypass "\\**REDACTED**\Summary\DB_filelist.ps1"
        *   -ExecutionPolicy Bypass "\\**REDACTED**\Summary\CSVGetter.ps1"

## How to Start the Generic File Monitor Server
1.	Download the attached zip folder/Clone git repository and extract it
1.	Open command prompt and run the following commands in the respective unzipped directories 
    *	python "\Generic-File-Monitor-master\flaskServer.py"
1.	If any dependency errors appear do the following: 
    *	pip install \<package name\>
1.  Access the Flask server at localhost:8080/ or 0.0.0.0:8080/
    *   /?days=30 /counter /date?date=2017-05-21
