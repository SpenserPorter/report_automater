from django.shortcuts import render
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.template import loader
from django.http import HttpResponse
from . import report_generator as rg
from .forms import ReportOptions
import uuid

def index(request):
    template = loader.get_template('tickets/index.html')
    context = {}
    return HttpResponse(template.render(context, request))

def about(request):
    template = loader.get_template('tickets/about.html')
    context = {}
    return HttpResponse(template.render(context, request))

def process(request, file_uuid):
    if request.method == 'POST':
        form = ReportOptions(request.POST)
        if form.is_valid():
            view_results = form.cleaned_data['view_results']
            email_results = form.cleaned_data['email_results']

        file_name = get_filename_from_uuid(file_uuid)
        validation_results = rg.validate_csv_file(file_name)
        if validation_results['success']:
            report_dict = rg.get_report_dict(validation_results['dataframe'])
            ticket_dict = rg.build_ticket_dict(report_dict)
            agent_totals = rg.agent_totals(ticket_dict)
            if view_results:
                return render(request, 'tickets/process.html', {
                    'agent_report': agent_totals[0]
                })
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
