import pandas as pd
import numpy as np
import datetime as dt
import os
import emailer

max_age_days = 10
df_initial = pd.read_csv('Helpdesk_ActionDetail.csv')


class Report:

    d

#Exclude cancelled tickets
def remove_cancelled_tickets_from_df(df):
    return df_initial.loc[df_initial['Request_Status'] != 'Cancelled']

#Get date range for tickets in report
def get_date_range_for_df(df):
    return "{} to {}".format(df.loc[0]['Request_Dttm'], df.iloc[-1]['Request_Dttm'])

#Get actions with Request Source set to manual that are not STS processes
def get_request_source_errors(df):
    return request_source_correction = df.loc[(~df['Request_Source'].isin(['Phone','E-mail'])) &
                                              (df['Model'] != 'STS PROCESS-FM')]

def get



#Get actions with missing severity
missing_severity = df.loc[df['Task_Severity'].isnull()]
reports_to_process.append((missing_severity, "Severity missing"))

#Get actions with missing closeout notes
missing_closeout = df.loc[df['Close_Notes'].isnull()]
reports_to_process.append((missing_closeout, "Closeout notes missing"))

#Get actions which have been open for more than max_age_days
date_format = r'%m/%d/%Y %I:%M %p'
aging_actions = df[(df['Request_Status'] == 'Open') &
                   ((dt.datetime.now() - pd.to_datetime(df['Request_Dttm'], format=date_format)).astype('timedelta64[D]') >= max_age_days)]
reports_to_process.append((aging_actions, 'Open tickets older than {} days'.format(max_age_days)))

ticket_dict = {}

def add_df_to_dict(df, report_name):
    '''Create dictionary of {Agent_name:{Report:[Ticket_list]}}'''
    for index, row in df.iterrows():
        if row['Request_Created_By'] not in ticket_dict:
            ticket_dict[row['Request_Created_By']] = {report_name: [row['Request_ID']]}
        else:
            if report_name not in ticket_dict[row['Request_Created_By']]:
                ticket_dict[row['Request_Created_By']][report_name] = [row['Request_ID']]
            else:
                if row['Request_ID'] not in ticket_dict[row['Request_Created_By']][report_name]:
                    ticket_dict[row['Request_Created_By']][report_name].append(row['Request_ID'])



#Add all dataframes to ticket dictionary
for df, report_name in reports_to_process:
    add_df_to_dict(df, report_name)
