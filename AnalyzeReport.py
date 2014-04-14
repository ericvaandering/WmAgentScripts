from __future__ import division

import json
import time

from WMCoreService.WMStatsClient import WMStatsClient
from WMCoreService.DataStruct.RequestInfoCollection import RequestInfoCollection

LAST_DAYS = 7
PERCENT_CHECK = '95'

if __name__ == "__main__":

    currentTime = time.time()
    openWorkflows = 0
    try:
        with open('report.json', 'r') as reportFile:
            report = json.load(reportFile)

        for wf in report:
            record = report[wf]
            if not record['end']:
                openWorkflows += 1
            else:
                try:
                    latency = (record['end']-record['percents'][PERCENT_CHECK])/(record['end']-record['start'])
                    daysOld = (currentTime-record['end'])/(24*3600)
                    if latency >=0 and latency<=1:
                        print "L",latency,"D",daysOld, wf
                    if latency > 15:
                        pass
                except:
                    pass
        print "Number of open workflows:", openWorkflows

    except IOError:
        print "No existing report. Exiting."
