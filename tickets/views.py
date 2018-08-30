from django.shortcuts import render
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.template import loader
from django.http import HttpResponse
from . import report_generator as rg
from .forms import ReportOptions
from .models import Agent, Ticket
import datetime as dt
from math import floor
import uuid
from django.db.models import Q
import pytz

timezone = pytz.timezone('US/Eastern')

def index(request):
    template = loader.get_template('tickets/index.html')
    context = {}
    return HttpResponse(template.render(context, request))

def about(request):
    template = loader.get_template('tickets/about.html')
    context = {}
    return HttpResponse(template.render(context, request))

def get_all_tickets_with_errors(agents_tickets):
    result = agents_tickets.filter(
                    Q(is_missing_closeout=True)|
                    Q(is_incorrect_request_source=True) |
                    Q(is_missing_severity=True)
                    )
    return result


def build_agent_report(days):
    agents = Agent.objects.all()
    totals_list = []
    for agent in agents:
        dttm_now = timezone.localize(dt.datetime.now())
        agents_tickets = agent.tickets.filter(
            dttm_created__gt=(dttm_now - dt.timedelta(days=days))
            ).all()
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

def get_report_data_context(days):
    totals_list = build_agent_report(days)
    context = {
        'totals_list': totals_list
    }
    return context

def agent_detail(request, pk):
    if request.method == 'GET':
        agent = Agent.objects.filter(id=pk).get()
        tickets = get_all_tickets_with_errors(agent.tickets.all())
        context = {
            'agent': agent,
            'tickets': tickets,
            }
        return render(request, 'tickets/agent_detail.html', context)

def view(request, file_uuid=None, pk=None):
    if request.method == 'GET':
        context = get_report_data_context(days=30)
        return render(request, 'tickets/view.html', context)

    if request.method == 'POST' and file_uuid is not None:
        form = ReportOptions(request.POST)
        if form.is_valid():
            view_results = form.cleaned_data['view_results']
            email_results = form.cleaned_data['email_results']
        file_name = get_filename_from_uuid(file_uuid)
        validation_results = rg.validate_csv_file(file_name)
        if validation_results['success']:
            report_dict = rg.get_report_dict(validation_results['dataframe'])
            rg.add_reports_dict_to_db(report_dict)
            context = {}
            if view_results:
                totals_list = build_agent_report(days=30)
                context['totals_list'] = totals_list
                context['start_dttm'] = report_dict['start_dttm']
                context['end_dttm'] = report_dict['end_dttm']
            if email_results:
                #send email with rg
                context['email_results'] = 'Emails sent'

            return render(request, 'tickets/view.html', context)
        else:
            return render(request, 'tickets/upload.html', {
                'file_upload_error_message': validation_results['error_text']
            })

def get_filename_from_uuid(uuid):
    return "{}/{}.csv".format(settings.MEDIA_ROOT, uuid)

def upload(request):
    if request.method == 'POST' and request.FILES.get('myfile'):
        myfile = request.FILES['myfile']
        if myfile.name.split('.')[-1] != 'csv':
            return render(request, 'tickets/upload.html', {
                'file_upload_error_message': 'Error: File must be .csv'
            })
        validation_results = rg.validate_csv_file(myfile)
        if validation_results['success']:
            fs = FileSystemStorage()
            ext = myfile.name.split('.')[-1]
            file_uuid = uuid.uuid4()
            file_name = get_filename_from_uuid(file_uuid)
            filename = fs.save(file_name, myfile)
            uploaded_file_url = fs.url(filename)
            form = ReportOptions()
            return render(request, 'tickets/upload.html', {
                'form': form,
                'uploaded_file_uuid': file_uuid
                })
        else:
            return render(request, 'tickets/upload.html', {
                'file_upload_error_message': validation_results['error_text']
            })
    template = loader.get_template('tickets/upload.html')
    context = {}
    return HttpResponse(template.render(context, request))
    #return render(request, 'tickets')
