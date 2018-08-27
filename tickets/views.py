from django.shortcuts import render
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.template import loader
from django.http import HttpResponse
import tickets.report_generator as rg

# def index(request):
#     template = loader.get_template('tickets/index.html')
#     context = {}
#     return HttpResponse(template.render(context, request))

def index(request):
    if request.method == 'POST' and request.FILES['myfile']:
        myfile = request.FILES['myfile']
        if myfile.name.split('.')[-1] != 'csv':
            return render(request, 'tickets/index.html', {
                'file_upload_error_message': 'Error: File must be .csv'
            })
        fs = FileSystemStorage()
        filename = fs.save(myfile.name, myfile)
        uploaded_file_url = fs.url(filename)
        validation_results = rg.validate_csv_file("{}/{}".format(settings.MEDIA_ROOT, filename))
        if validation_results['success']:
            report_dict = rg.get_report_dict(validation_results['dataframe'])
            ticket_dict = rg.build_ticket_dict(report_dict)
            agent_totals = rg.agent_totals(ticket_dict)
            return render(request, 'tickets/index.html', {
                'agent_report': agent_totals[0]
            })
        else:
            return render(request, 'tickets/index.html', {
                'file_upload_error_message': validation_results['error_text']
            })

    template = loader.get_template('tickets/index.html')
    context = {}
    return HttpResponse(template.render(context, request))
    #return render(request, 'tickets')
