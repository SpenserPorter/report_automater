from yaml import dump
import os

config_to_dump =    {'max_age_days': 10,
                    'email_domain': '@spencertech.com',
                    'lead_list': ['Mfrade@spencertech.com', 'MBradley@spencertech.com', 'CAndrade@spencertech.com',
                             'MYurrita@spencertech.com', 'Sporter@spencertech.com'],
                    'send_email': False}

with open('config.yaml', 'w') as config_file:
    dump(config_to_dump, config_file)
