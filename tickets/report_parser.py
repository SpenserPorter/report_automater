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
send_email = False

reports_to_process = []
#Exclude cancelled tickets
df = df_initial.loc[df_initial['Request_Status'] != 'Cancelled']

#Get date range for tickets in report
date_range = "{} to {}".format(df.loc[0]['Request_Dttm'], df.iloc[-1]['Request_Dttm'])

#Get actions with Request Source set to manual that are not STS processes
request_source_correction = df.loc[(~df['Request_Source'].isin(['Phone','E-mail'])) &
                                   (df['Model'] != 'STS PROCESS-FM')]
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
    output = ["Tickets with a * have multiple issues <br>"]
    agent_ticket_list = []
    for report_name, list_of_tickets in agent_dict.items():
        for i in range(len(list_of_tickets)):
            if list_of_tickets[i] not in agent_ticket_list:
                agent_ticket_list.append(list_of_tickets[i])
            else:
                list_of_tickets[i] = str(list_of_tickets[i]) + '*'
        output.append("{}<br>{}".format(report_name, "<br>".join(map(str, list_of_tickets))))
        output.append("<br>")
    disclaimer = "This report was auto-generated, please reply with any errors and include the ticket number. <br><br>"
    output.append(disclaimer)
    return '<br>'.join(output), len(agent_ticket_list)

def construct_email_address_from_name(name_string):
    '''Builds email address from First Last string using standard email format of
    first initial + last name @email_domain.com'''
    first, last = name_string.replace("'", "").split(" ")
    email_list = [first[0], last, email_domain]
    return "".join(email_list)

def email_agents_results(full_dict):
    '''Emails agents a report of their malformed tickets'''
    auth = (from_account, password)
    for agent_name, reports in full_dict.items():
        email_body, total = construct_email_body(reports)
        email_subject = "{} tickets require action for {}".format(total, date_range)
        to_address = construct_email_address_from_name(agent_name)
        email = emailer.O365Email(auth, to_address, email_subject, email_body)
        if send_email:
            email.send()
        else:
            if agent_name == 'Spenser Porter':
                email.send()

def email_totals_report(full_dict):
    '''Emails leads a report of total malformed tickets by category and agent'''
    auth = (from_account, password)
    to_address = lead_list if send_email else 'SPorter@spencertech.com'
    email_body, total = agent_totals(full_dict)
    email_subject = "{} tickets require corrections for {}".format(total, date_range)
    email = emailer.O365Email(auth, to_address, email_subject, email_body)
    if send_email:
        email.send()
    else:
        email.send()

def agent_totals(dict):
    '''Generates total malformed ticket reports'''
    report_list = []
    total_tickets = 0
    for agent_name, reports in dict.items():
        report_list.append(agent_name)
        agent_ticket_list = []
        agent_total = 0
        for report_name, list_of_tickets in dict[agent_name].items():
            report_total = 0
            for ticket in list_of_tickets:
                if ticket not in agent_ticket_list:
                    agent_ticket_list.append(ticket)
            report_total = len(list_of_tickets)
            report_line = "&nbsp &nbsp &nbsp &nbsp{} {}".format(report_total, report_name)
            report_list.append(report_line)
        total_tickets += len(agent_ticket_list)
        agent_total = len(agent_ticket_list)
        report_list.append("&nbsp &nbsp &nbsp &nbsp{} total tickets".format(agent_total))
    report_list.append("<br>")
    return '<br>'.join(report_list), total_tickets

email_totals_report(ticket_dict)
email_agents_results(ticket_dict)
