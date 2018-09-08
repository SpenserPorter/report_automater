from yaml import dump
import os

config_to_dump =    {'max_age_days': 10,
                    'email_domain': '@spencertech.com',
                    'local_timezone': 'US/Eastern',
                    'send_email': False}

with open('config.yaml', 'w') as config_file:
    dump(config_to_dump, config_file)
