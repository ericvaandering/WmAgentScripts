from __future__ import division

import json
import pdb
import pprint
import time

from WMCoreService.WMStatsClient import WMStatsClient
from WMCoreService.DataStruct.RequestInfoCollection import RequestInfoCollection

if __name__ == "__main__":

    try:
        with open('report.json', 'r') as reportFile:
            report = json.load(reportFile)
    except IOError:
        print "No existing report. Starting a new one."
        report = {}
    updatedReport = {}

    url = "https://cmsweb.cern.ch/couchdb/wmstats"
    WMStats = WMStatsClient(url)
    print "Getting job information from %s. Please wait." % url

    requests = WMStats.getRequestByStatus(WMStatsClient.ACTIVE_STATUS, jobInfoFlag = True)
    requestCollection = RequestInfoCollection(requests)
    result = requestCollection.getJSONData()

    for wf in result.keys():
        nJobs = requests[wf].get('total_jobs', 0)
        priority = requests[wf]['priority']
        requestType = requests[wf]['request_type']

        successJobs = 0
        totalJobs = 0
        for agent in result[wf]:
            jobs = result[wf][agent]
            successJobs += jobs['sucess']
            totalJobs += jobs['created']

        startTime = None
        endTime = None
        complete90 = None
        finalStatus = None
        for status in requests[wf]['request_status']:
            finalStatus = status['status']
            if status['status'] == 'acquired':
                startTime = status['update_time']
            if status['status']	== 'closed-out':
                endTime = status['update_time']

        if totalJobs > 0:
            percentDone = (successJobs / totalJobs)*100.0
        else:
            percentDone = 0

        newValue = report.setdefault(wf, {})
        if newValue:
            updatedReport[wf] = True

        report[wf].update({'priority':priority, 'percent':percentDone, 'start':startTime,
                           'end':endTime, 'totalJobs':totalJobs, 'status':finalStatus,
                           'type':requestType})
        report[wf].setdefault('percents', {})

        for percentage in [1,10,25, 50, 65, 75, 80, 85, 90, 95, 98, 99]:
            percentReported = report[wf]['percents'].get(str(percentage), None)

            if not percentReported and percentDone >= percentage:
                print "Added %s%% for workflow %s" % (percentage, wf)
                updatedReport[wf] = True
                report[wf]['percents'][percentage] = time.time()

    print "\ntotal %s requests retrieved" % len(result)

    with open('report.json', 'w') as reportFile:
        json.dump(report, reportFile, indent=1)

