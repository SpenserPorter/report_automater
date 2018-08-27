from tickets import emailer
from tickets import report_parser as rp
import yaml
import os
import pandas as pd

#Set config file path
file_path = os.path.dirname(__file__)
config_file_rel_path = "config/config.yaml"
abs_config_path = os.path.join(file_path, config_file_rel_path)

#set config variables
with open(abs_config_path, 'r') as ymlfile:
    cfg = yaml.load(ymlfile)
    max_age_days = cfg['max_age_days']
    email_domain = cfg['email_domain']
    lead_list = cfg['lead_list']
    send_email = cfg['send_email']

from_account = os.getenv('REPORT_EMAIL_USERNAME')
password = os.getenv('REPORT_EMAIL_PASSWORD')

def validate_csv_file(csv_file_path):
    """Validates file is csv, and has the expected columns for Helpdesk_ActionDetail.csv report,
    returns the dataframe if valid, or the error message if not valid"""
    try:
        df = pd.read_csv(csv_file_path)
        test = df[['Request_ID', 'Request_Status', 'Request_Created_By', 'Request_Dttm', 'Request_Source',
                'Task_Severity','Close_Notes']]
        return {'success': True, 'dataframe': df}
    except IOError as error_message:
        return {'success': False, 'error_text': 'Unable to open file at location {}'.format(csv_file_path),
                'error': error_message
                }
    except KeyError as error_message:
        return {'success': False, 'error_text': "The report submitted doesn't appear to be a Helpdesk_ActionDetail report,\
                please upload the correct report", 'error': error_message
                }

def get_report_dict(dataframe):
    return rp.split_df_into_reports(dataframe, max_age_days)

def build_ticket_dict(report_dict):
    ticket_dict = {}
    for report in report_dict['report_list']:
        add_report_to_dict(report, ticket_dict)
    return ticket_dict

def add_report_to_dict(report, ticket_dict):
    '''Create dictionary of {Agent_name:{Report:[Ticket_list]}}'''
    df = report.df
    report_name = report.name
    for index, row in df.iterrows():
        agent = row['Request_Created_By']
        if agent not in ticket_dict:
            ticket_dict[agent] = {report_name: [row['Request_ID']]}
        else:
            if report_name not in ticket_dict[agent]:
                ticket_dict[agent][report_name] = [row['Request_ID']]
            else:
                if row['Request_ID'] not in ticket_dict[agent][report_name]:
                    ticket_dict[agent][report_name].append(row['Request_ID'])
    return ticket_dict

def construct_email_body(agent_dict):
    '''Builds email body with a list of tickets under each
    report header'''
    output = []
    agent_ticket_list = []
    for report_name, list_of_tickets in agent_dict.items():
        for i in range(len(list_of_tickets)):
            if list_of_tickets[i] not in agent_ticket_list:
                agent_ticket_list.append(list_of_tickets[i])
            else:
                list_of_tickets[i] = str(list_of_tickets[i]) + '*'
        output.append('{}<br>{}'.format(report_name, "<br>".join(map(str, list_of_tickets))))
        output.append('<br>')
    disclaimer = 'This report was auto-generated, please reply with any errors and include the ticket number. <br><br>'
    output.append(disclaimer)
    return '<br>'.join(output), len(agent_ticket_list)

def email_agents_results(full_dict):
    '''Emails agents a report of their malformed tickets'''
    auth = (from_account, password)
    for agent_name, reports in full_dict.items():
        email_body, total = construct_email_body(reports)
        email_subject = '{} tickets require action for {}'.format(total, date_range)
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
    email_subject = '{} tickets require corrections for {}'.format(total, date_range)
    email = emailer.O365Email(auth, to_address, email_subject, email_body)
    if send_email:
        email.send()
    else:
        return email_body

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
            report_line = '&nbsp &nbsp &nbsp &nbsp{} {}'.format(report_total, report_name)
            report_list.append(report_line)
        total_tickets += len(agent_ticket_list)
        agent_total = len(agent_ticket_list)
        report_list.append('&nbsp &nbsp &nbsp &nbsp{} total tickets'.format(agent_total))
    report_list.append('<br>')
    return '<br>'.join(report_list), total_tickets

#email_totals_report(ticket_dict)
#email_agents_results(ticket_dict)
