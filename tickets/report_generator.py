from tickets import emailer
from tickets import report_parser as rp
import datetime as dt
import yaml
import os
import pandas as pd
from .models import Agent, Ticket
from django.db import transaction
import pytz

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

timezone = pytz.timezone('US/Eastern')
from_account = os.getenv('REPORT_EMAIL_USERNAME')
password = os.getenv('REPORT_EMAIL_PASSWORD')
dttm_format = r'%m/%d/%Y %I:%M %p'

def validate_csv_file(csv_file_path):
    """Validates file is csv, and has the expected columns for Helpdesk_ActionDetail.csv report,
    returns the dataframe if valid, or the error message if not valid"""
    try:
        df = pd.read_csv(csv_file_path)
        test = df[['Request_ID', 'Request_Status', 'Request_Created_By', 'Request_Dttm', 'Request_Source',
                'Task_Severity','Close_Notes']]
        if df.shape == df.loc[df['Request_Type'] == 'Help Desk'].shape:
            return {'success': True, 'dataframe': df}
    except IOError as error_message:
        return {'success': False, 'error_text': 'Unable to open file at location {}'.format(csv_file_path),
                'error': error_message
                }
    except KeyError as error_message:
        return {
        'success': False,
        'error_text': "The report submitted doesn't appear to be a Helpdesk_ActionDetail report,\
                        please upload the correct report",
        'error': error_message
        }

def get_report_dict(dataframe):
    return rp.split_df_into_reports(dataframe, max_age_days)

def build_agent_model(agent_name):
    email = get_email_address(agent_name)
    return Agent.create(agent_name, email)

def get_email_address(agent_name):
    '''Builds email address from First Last string using standard email
     format of first initial + last name @email_domain.com'''
    first, last = agent_name.split(' ')
    email_components = [first[0], last, email_domain]
    return "".join(email_components)

def add_reports_dict_to_db(report_dict):
    ticket_dict = {}
    for report in report_dict['report_list']:
        dttm_updated = report_dict['end_dttm']
        add_report_to_db(report, ticket_dict, dttm_updated)

def set_ticket_report_status(ticket, report_name):
    if report_name == 'All tickets':
        return
    elif report_name == 'Request source incorrect':
        ticket.is_incorrect_request_source = True
    elif report_name == 'Severity missing':
        ticket.is_missing_severity = True
    elif report_name == 'Missing closeout':
        ticket.is_missing_closeout = True
    elif report_name == 'Open tickets':
        ticket.is_open = True

@transaction.atomic
def add_report_to_db(report, ticket_dict, report_pulled_dttm):
    '''Add tickets to DB based on owner and report they show up in'''
    df = report.df
    report_name = report.name
    for index, row in df.iterrows():
        agent_name = row['Request_Created_By']
        ticket_id = row['Request_ID']
        ticket_created_dttm = timezone.localize(dt.datetime.strptime(row['Request_Dttm'], dttm_format))

        if Agent.objects.filter(name=agent_name).exists():
            agent = Agent.objects.filter(name=agent_name).get()
        else:
            agent = build_agent_model(agent_name)
            agent.save()
        if Ticket.objects.filter(id=ticket_id).exists():
            ticket = Ticket.objects.filter(id=ticket_id).get()
            if ticket.dttm_updated < report_pulled_dttm:
                ticket.clear_all_status()
                ticket.last_updated = report_pulled_dttm
        else:
            ticket = Ticket.create(ticket_id, agent, ticket_created_dttm, report_pulled_dttm)
        set_ticket_report_status(ticket, report_name)
        ticket.save()

def construct_email_body():
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
