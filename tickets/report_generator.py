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
    send_email = cfg['send_email']
    local_tz = cfg['local_timezone']

timezone = pytz.timezone(local_tz)
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
    elif report_name == 'Negative response time':
        ticket.is_negative_response_time = True
    elif report_name == 'Large response time':
        ticket.is_large_response_time = True
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
