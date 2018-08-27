from django import forms

class ReportOptions(forms.Form):
    view_results = forms.BooleanField(required=False)
    email_results = forms.BooleanField(required=False)
