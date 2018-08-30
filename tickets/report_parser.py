import pandas as pd
import numpy as np
import datetime as dt
import os
import pytz

timezone = pytz.timezone('US/Eastern')

class ReportDataframe:

    def __init__(self, dataframe, name):
        self.df = dataframe
        self.name = name

def split_df_into_reports(df_initial, max_age_days):
    """Takes raw datafrome and splits into Report objects"""

    dttm_format = r'%m/%d/%Y %I:%M %p'
    #Exclude cancelled tickets
    df = df_initial.loc[df_initial['Request_Status'] != 'Cancelled']

    #Get date range for tickets in report
    start_dttm = timezone.localize(dt.datetime.strptime(df.iloc[0]['Request_Dttm'], dttm_format))
    end_dttm = timezone.localize(dt.datetime.strptime(df.iloc[-1]['Request_Dttm'], dttm_format))
    report_dict = {'start_dttm': start_dttm, 'end_dttm':end_dttm, 'report_list':[]}
    #Get actions with Request Source set to manual that are not STS processes
    report_dict['report_list'].append(ReportDataframe(
                                dataframe = df,
                                name = 'All tickets'
                                )
    )
    report_dict['report_list'].append(ReportDataframe(
                                        dataframe=df.loc[
                                                    (~df['Request_Source'].isin(['Phone','E-mail'])) &
                                                    (df['Model'] != 'STS Process')
                                                    ],
                                        name='Request source incorrect'
                                        )
    )
    #Get actions with missing severity
    report_dict['report_list'].append(ReportDataframe(
                                        dataframe=df.loc[df['Task_Severity'].isnull()],
                                        name='Severity missing'
                                        )
    )

    #Get actions with missing closeout notes
    report_dict['report_list'].append(ReportDataframe(
                                        dataframe=df.loc[df['Close_Notes'].isnull()],
                                        name='Missing closeout'
                                        )
    )

    #Get actions which have been open for more than max_age_days
    report_dict['report_list'].append(ReportDataframe(
                dataframe=df[
                    (df['Request_Status'] == 'Open')
                    ],
                name='Open tickets'
                )
)
    return report_dict
