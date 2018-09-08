from django import forms

class ReportOptions(forms.Form):
    view_results = forms.BooleanField(required=False)
    email_results = forms.BooleanField(required=False)

class EmailerOptions(forms.Form):
    email_agents = forms.BooleanField(required=False)
    email_leads = forms.BooleanField(required=False)
