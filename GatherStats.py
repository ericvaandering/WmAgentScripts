from __future__ import division

import json
import time

from WMCoreService.WMStatsClient import WMStatsClient
from WMCoreService.DataStruct.RequestInfoCollection import RequestInfoCollection

if __name__ == "__main__":

    report = {}

    url = "https://cmsweb.cern.ch/couchdb/wmstats"
    WMStats = WMStatsClient(url)
    print "start to getting job information from %s" % url
    print "will take a while\n"
#    requests = WMStats.getRequestByStatus(["running-closed", "completed"], jobInfoFlag = True)
    requests = WMStats.getRequestByStatus(WMStatsClient.ACTIVE_STATUS, jobInfoFlag = True)
    requestCollection = RequestInfoCollection(requests)
    result = requestCollection.getJSONData()
    import pdb
    import pprint
    for wf in result.keys():
#        print "Checking", wf
        nJobs = requests[wf].get('total_jobs', 0)
        priority = requests[wf]['priority']
        requestType = requests[wf]['request_type']

        successJobs = 0
        totalJobs = 0
        for agent in result[wf]:
#            pdb.set_trace()
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

        print "%6s %3d%% %12s %12s %8d  %-80.80s %-20s %-12s" % (priority, percentDone, startTime, endTime, totalJobs, wf, finalStatus, requestType)

        report.setdefault(wf, {})   
#	if not wf in report.keys():
#            report[wf] = {}
	report[wf].update({'priority':priority, 'percent':percentDone, 'start':startTime, 'end':endTime, 'totalJobs':totalJobs, 'status':finalStatus, 'type':requestType})
        report[wf].setdefault('percents', {})
 
#       if not 'percents' in report[wf]:
#            report[wf].update({'percents':{}})

#        pdb.set_trace()
        for percentage in (range(50,100,5) + [99]):
            percentReported = report[wf]['percents'].get(percentage, None)
#            pdb.set_trace()
            if not percentReported and percentDone >= percentage:
                report[wf]['percents'][percentReported] = time.time()

        #pdb.set_trace()

#    print result
    print "\ntotal %s requests retrieved" % len(result)

    with open('report.json', 'w') as reportFile:
        json.dump(report, reportFile, indent=1)

