import pandas as pd
import numpy as np
import datetime as dt
import os
import emailer

max_age_days = 10
df_initial = pd.read_csv("Helpdesk_ActionDetail.csv")
email_domain = "@spencertech.com"
from_account = os.getenv('REPORT_EMAIL_USERNAME')
password = os.getenv('REPORT_EMAIL_PASSWORD')
lead_list = ['Mfrade@spencertech.com', 'MBradley@spencertech.com', 'CAndrade@spencertech.com',
             'MYurrita@spencertech.com', 'Sporter@spencertech.com']

reports_to_process = []
#Exclude cancelled tickets
df = df_initial.loc[df_initial['Request_Status'] != 'Cancelled']

#Get date range for tickets in report
date_range = "{} to {}".format(df.loc[0]['Request_Dttm'], df.iloc[-1]['Request_Dttm'])

#Get actions with Request Source set to manual that are not STS processes
request_source_correction = df.loc[(~df['Request_Source'].isin(['Phone','E-mail'])) &
                                   (df['Model'] != 'STS Process')]
reports_to_process.append((request_source_correction, "Request source incorrect"))

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
reports_to_process.append((aging_actions, "Open tickets older than {} days".format(max_age_days)))

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

def construct_email_body(agent_dict):
    '''Builds email body with a list of tickets under each
    report header'''
    output = []
    for report_name, list_of_tickets in agent_dict.items():
        output.append("{}<br>{}".format(report_name, "<br>".join(map(str, list_of_tickets))))
        output.append("<br>")
    disclaimer = "<br>This report was auto-generated, please reply with any errors and include the ticket number.<br>"
    output.append(disclaimer)
    return '<br>'.join(output)

def construct_email_address_from_name(name_string):
    '''Builds email address from First Last string using standard email format of
    first initial + last name @email_domain.com'''
    first, last = name_string.replace("'", "").split(" ")
    email_list = [first[0], last, email_domain]
    return "".join(email_list)

def email_agents_results(full_dict):
    '''Emails agents a report of their malformed tickets'''
    auth = emailer.O365Auth(from_account, password)
    for agent_name, reports in full_dict.items():
        email_body = construct_email_body(reports)
        email_subject = "Tickets needing action for {}".format(date_range)
        to_address_actual = construct_email_address_from_name(agent_name)
        email = emailer.O365Email(auth.auth, to_address_actual, email_subject, email_body)
        email.send()

def email_totals_report(full_dict):
    '''Emails leads a report of total malformed tickets by category and agent'''
    auth = emailer.O365Auth(from_account, password)
    to_address = lead_list
    email_body, total = agent_totals(full_dict)
    email_subject = "{} tickets require corrections for {}".format(total, date_range)
    email = emailer.O365Email(auth.auth, to_address, email_subject, email_body)
    email.send()

def agent_totals(dict):
    '''Generates total malformed ticket reports'''
    report_list = []
    total = 0
    for agent_name, reports in dict.items():
        report_list.append(agent_name)
        agent_total = 0
        for report_name, list_of_tickets in dict[agent_name].items():
            line_total = len(list_of_tickets)
            agent_total += line_total
            total += line_total
            report_line = "&nbsp &nbsp &nbsp &nbsp{} {}".format(line_total, report_name)
            report_list.append(report_line)
        report_list.append("&nbsp &nbsp &nbsp &nbsp{} total".format(agent_total))
    report_list.append("<br>")
    return '<br>'.join(report_list), total

email_totals_report(ticket_dict)
email_agents_results(ticket_dict)
