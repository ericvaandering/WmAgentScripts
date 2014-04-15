from __future__ import division

import copy
import json
import pdb
import pprint
import time

from WMCoreService.WMStatsClient import WMStatsClient
from WMCoreService.DataStruct.RequestInfoCollection import RequestInfoCollection




#def conditionalUpdate(theDict, updateDict, theKey, theValue, updateKey):
    #if not theDict.get(theKey, None):
        #theDict.update(theKey, theValue)
        #updateDict[updateKey] = True

    #return

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
    requestsDict = requestCollection.getData()

    for wf in result.keys():

        oldRecord = copy.deepcopy(report.get(wf, None))

        nJobs = requests[wf].get('total_jobs', 0)
        priority = requests[wf]['priority']
        requestType = requests[wf]['request_type']
        datasetReports = requestsDict[wf].getProgressSummaryByOutputDataset()#[0].getReport()
        targetLumis = requests[wf].get('input_lumis', 0)
        targetEvents = requests[wf].get('input_events', 0)

        eventPercent = 200
        lumiPercent = 200
        for dataset in datasetReports:
            dsr = datasetReports[dataset].getReport()
            events = dsr.get('events', 0)
            lumis = dsr.get('totalLumis', 0)
            if targetLumis:
                lumiPercent = min(lumiPercent, lumis/targetLumis*100)
            if targetEvents:
                eventPercent = min(eventPercent, events/targetEvents*100)
        if eventPercent > 100:
            eventPercent = 0
        if lumiPercent > 100:
            lumiPercent = 0


        successJobs = 0
        totalJobs = 0
        for agent in result[wf]:
            jobs = result[wf][agent]
            successJobs += jobs['sucess']
            totalJobs += jobs['created']

        if totalJobs and not report[wf].get('firstJobTime', None):
            firstJobTime = time.time()
            report[wf].update({'firstJobTime':firstJobTime,})
        if totalJobs and successJobs == totalJobs and not report[wf].get('lastJobTime', None):
            report[wf].update({'lastJobTime' : time.time()})


        startTime = None
        endTime = None
        complete90 = None
        finalStatus = None
        acquireTime = None
        closeoutTime = None
        completedTime = None
        announcedTime = None
        for status in requests[wf]['request_status']:
            finalStatus = status['status']
            if status['status'] == 'completed':
                completedTime = status['update_time']
            if status['status'] == 'acquired':
                startTime = status['update_time']
                acquireTime = status['update_time']
            if status['status']	== 'closed-out':
                endTime = status['update_time']
                closeoutTime = status['update_time']
            if status['status']	== 'announced':
                announcedTime = status['update_time']



        if totalJobs > 0:
            percentDone = (successJobs / totalJobs)*100.0
        else:
            percentDone = 0

        newValue = report.setdefault(wf, {})
        if newValue:
            updatedReport[wf] = True

        if acquireTime and not report[wf].get('acquireTime', None):
            report[wf].update({'acquireTime':acquireTime})
        if closeoutTime and not report[wf].get('closeoutTime', None):
            report[wf].update({'closeoutTime':closeoutTime})
        if announcedTime and not report[wf].get('announcedTime', None):
            report[wf].update({'announcedTime':announcedTime})
        if completedTime and not report[wf].get('completedTime', None):
            report[wf].update({'completedTime':completedTime})

        report[wf].update({'priority':priority, 'percent':percentDone, 'start':startTime,
                           'end':endTime, 'totalJobs':totalJobs, 'status':finalStatus,
                           'type':requestType})
        report[wf].update({'lumiPercent' : lumiPercent, 'eventPercent' : eventPercent}) # Consider not keeping, may blow up couch

        report[wf].setdefault('percents', {})
        report[wf].setdefault('lumiPercents', {})
        report[wf].setdefault('eventPercents', {})

        for percentage in [1,10,25, 50, 65, 75, 80, 85, 90, 95, 98, 99]:
            percentReported = report[wf]['percents'].get(str(percentage), None)
            if not percentReported and percentDone >= percentage:
                print "Added job %s%% for workflow %s" % (percentage, wf)
                report[wf]['percents'][percentage] = int(time.time())

            percentReported = report[wf]['lumiPercents'].get(str(percentage), None)
            if not percentReported and lumiPercent >= percentage:
                print "Added lumi %s%% for workflow %s" % (percentage, wf)
                report[wf]['lumiPercents'][percentage] = int(time.time())

            percentReported = report[wf]['eventPercents'].get(str(percentage), None)
            if not percentReported and eventPercent >= percentage:
                print "Added event %s%% for workflow %s" % (percentage, wf)
                report[wf]['eventPercents'][percentage] = int(time.time())


        newRecord = report[wf]
        if oldRecord != newRecord:
            print "Workflow updated: ", wf

    print "\ntotal %s requests retrieved" % len(result)

    with open('report.json', 'w') as reportFile:
        json.dump(report, reportFile, indent=1)

