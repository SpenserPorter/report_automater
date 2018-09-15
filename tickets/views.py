from os import getenv
import uuid

from django.shortcuts import render
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.template import loader
from django.http import HttpResponse
from django.db.models import Count, Q

from . import report_generator as rg
from . import report_parser as rp
from . import email_sender
from .forms import ReportOptions, EmailerOptions
from .models import Agent, Ticket

send_email = True

def index(request):
    template = loader.get_template('tickets/index.html')
    context = {}
    return HttpResponse(template.render(context, request))

def about(request):
    template = loader.get_template('tickets/about.html')
    context = {}
    return HttpResponse(template.render(context, request))

def agent_detail(request, pk):
    if request.method == 'GET':
        agent = Agent.objects.filter(id=pk).get()
        tickets = rg.get_all_tickets_with_errors(agent.tickets.all())
        context = {
            'agent': agent,
            'tickets': tickets,
            }
        return render(request, 'tickets/agent_detail.html', context)

def view(request, file_uuid=None, pk=None):
    if request.method == 'GET':
        context = rg.get_report_data_context(None)
        return render(request, 'tickets/view.html', context)

    if request.method == 'POST' and file_uuid is not None:
        form = ReportOptions(request.POST)
        if form.is_valid():
            view_results = form.cleaned_data['view_results']
            email_results = form.cleaned_data['email_results']
        file_name = get_filename_from_uuid(file_uuid)
        validation_results = rg.validate_csv_file(file_name)
        if validation_results['success']:
            report_dict = rp.split_df_into_reports(validation_results['dataframe'])
            rg.add_reports_dict_to_db(report_dict)
            context = {}
            if view_results:
                totals_list = rg.build_agent_report()
                context['totals_list'] = totals_list
                context['start_dttm'] = report_dict['start_dttm']
                context['end_dttm'] = report_dict['end_dttm']
            if email_results:
                pass

            return render(request, 'tickets/view.html', context)
        else:
            return render(request, 'tickets/upload.html', {
                'file_upload_error_message': validation_results['error_text']
            })

def emailer(request):
    if request.method == 'POST':
        form = EmailerOptions(request.POST)
        if form.is_valid():
            email_agents = form.cleaned_data['email_agents']
            email_leads = form.cleaned_data['email_leads']
        if email_agents:
            rg.email_agents_reports()
        if email_leads:
            rg.email_totals_report()
    form = EmailerOptions()
    context = {
        'form': form
    }
    return render(request, 'tickets/emailer.html', context)

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

def get_filename_from_uuid(uuid):
    return "{}/{}.csv".format(settings.MEDIA_ROOT, uuid)
