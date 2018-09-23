from tickets import report_parser as rp
import datetime as dt
import pytz
import yaml
import os
import pandas as pd
from math import floor
from .models import Agent, Ticket
from django.db import transaction
from django.db.models import Count, Q
from django.template import loader

from . import email_sender
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
send_email = True

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

def build_agent_model(agent_name):
    email = get_email_address(agent_name)
    return Agent.create(agent_name, email)

def get_email_address(agent_name):
    '''Builds email address from First Last string using standard email
     format of first initial + last name @email_domain.com'''
    first, last = agent_name.replace("'",'').split(' ')
    email_components = [first[0], last, email_domain]
    return "".join(email_components)

def add_reports_dict_to_db(report_dict):
    ticket_dict = {}
    for report in report_dict['report_list']:
        dttm_updated = report_dict['end_dttm']
        add_report_to_db(report, ticket_dict, dttm_updated)

def set_ticket_report_status(ticket, report_name):
    '''Set ticket values based on report it's in'''

    if report_name == 'All tickets':
        ticket.clear_all_status()
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
                ticket.dttm_updated = report_pulled_dttm
        else:
            ticket = Ticket.create(ticket_id, agent, ticket_created_dttm, report_pulled_dttm)
        set_ticket_report_status(ticket, report_name)
        ticket.save()

def get_report_data_context(days=None):
    totals_list = build_agent_report(days)
    context = {
        'totals_list': totals_list
    }
    return context

def email_totals_report():
    '''Emails leads a report of total malformed tickets by category and agent'''
    auth = (from_account, password)
    to_address = list(Agent.objects.filter(is_lead=True).all().values_list('email', flat=True)) if send_email else 'Sporter@spencertech.com'
    context = get_report_data_context() #TODO Change days to form param
    email_body = loader.render_to_string('tickets/totals_email.html', context)
    email_subject = "Ticket error report, all agents"
    email = email_sender.O365Email(auth, to_address, email_subject, email_body)
    if send_email:
        email.send()

def get_all_tickets_with_errors(agents_tickets):
    result = agents_tickets.filter(
                    Q(is_missing_closeout=True) |
                    Q(is_incorrect_request_source=True) |
                    Q(is_missing_severity=True)
                    )
    return result

def get_agents_with_nonzero_tickets():
    return Agent.objects.annotate(ticket_count=Count('tickets')).filter(ticket_count__gt=0).all()

def build_agent_report(days=None):
    agents = get_agents_with_nonzero_tickets()
    totals_list = []
    for agent in agents:
        dttm_now = timezone.localize(dt.datetime.now())
        if days is not None:
            agents_tickets = agent.tickets.filter(
                                dttm_created__gt=(dttm_now - dt.timedelta(days=days))
                                ).all()
        else:
            agents_tickets = agent.tickets.all()

        total_tickets = agents_tickets.count()
        total_open_tickets = agents_tickets.filter(is_open=True).count()
        total_missing_sev = agents_tickets.filter(is_missing_severity=True).count()
        total_incorrect_request_source = agents_tickets.filter(is_incorrect_request_source=True).count()
        total_missing_closeout = agents_tickets.filter(is_missing_closeout=True).count()
        total_with_errors = get_all_tickets_with_errors(agents_tickets).count()
        error_percent = floor((total_with_errors / total_tickets) * 100) if total_tickets > 0 else 0
        totals_list.append({
            'agent': agent, 'total_open_tickets': total_open_tickets, 'total_missing_sev': total_missing_sev,
            'total_incorrect_request_source':total_incorrect_request_source, 'total_missing_closeout': total_missing_closeout,
            'total_with_errors': total_with_errors, 'total_tickets': total_tickets, 'error_percent': error_percent
            }
        )
        sorted_totals = sorted(totals_list, key=lambda totals: totals['total_tickets'], reverse=True)
    return sorted_totals

def email_agents_reports():
    '''Emails agents a report of their malformed tickets'''
    auth = (from_account, password)
    agents = get_agents_with_nonzero_tickets()
    for agent in agents:
        tickets = get_all_tickets_with_errors(agent.tickets.all())
        total_tickets_with_errors = tickets.count()
        if total_tickets_with_errors > 0:
            context = {
                'agent': agent,
                'tickets': tickets,
                }
            email_body = loader.render_to_string('tickets/agent_emails.html', context)
            email_subject = '{} tickets require action'.format(total_tickets_with_errors)
        else:
            email_body = "Good job!"
            email_subject = "All your tickets are correct"
        to_address = agent.email
        email = email_sender.O365Email(auth, to_address, email_subject, email_body)
        if send_email:
            email.send()
        else:
            if agent.name == 'Spenser Porter':
                email.send()
