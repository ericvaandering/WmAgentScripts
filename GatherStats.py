from __future__ import division

import copy
import json
import pdb
import pprint
import time

from optparse import OptionParser

from WMCoreService.CouchClient import CouchServer
from WMCoreService.CouchClient import Document as CouchDoc
from WMCoreService.WMStatsClient import WMStatsClient
from WMCoreService.DataStruct.RequestInfoCollection import RequestInfoCollection


if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-s", "--server", dest="server",
                    help="CouchDB server to write results to", )
    parser.add_option("-d", "--database", dest="database", default='latency_analytics',
                    help="CouchDB database for results")

    (options, args) = parser.parse_args()

    analyticsServer = CouchServer(options.server)
    couchdb = analyticsServer.connectDatabase(options.database)

    try:
        with open('report.json', 'r') as reportFile:
            report = json.load(reportFile)
    except IOError:
        print "No existing report. Starting a new one."
        report = {}

    url = "https://cmsweb.cern.ch/couchdb/wmstats"
    WMStats = WMStatsClient(url)
    print "Getting job information from %s. Please wait." % url
    requests = WMStats.getRequestByStatus(WMStatsClient.ACTIVE_STATUS, jobInfoFlag = True)

    requestCollection = RequestInfoCollection(requests)
    result = requestCollection.getJSONData()
    requestsDict = requestCollection.getData()

    for wf in result.keys():
        # Store a copy of the CouchDB document so we can compare later before updating
        if couchdb.documentExists(wf):
            oldCouchDoc = couchdb.document(wf)
            wfExists = True
        else:
            oldCouchDoc = CouchDoc(id=wf)
            wfExists = False

        # Basic parameters of the workflow
        priority = requests[wf]['priority']
        requestType = requests[wf]['request_type']
        targetLumis = requests[wf].get('input_lumis', 0)
        targetEvents = requests[wf].get('input_events', 0)

        # Calculate completion ratios for events and lumi sections, take minimum for all datasets
        eventPercent = 200
        lumiPercent = 200
        datasetReports = requestsDict[wf].getProgressSummaryByOutputDataset()
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

        # Sum up all jobs across agents to see if we've run the first, last
        successJobs = 0
        totalJobs = 0
        for agent in result[wf]:
            jobs = result[wf][agent]
            successJobs += jobs['sucess']
            totalJobs += jobs['created']
        try:
            if totalJobs and not report[wf].get('firstJobTime', None):
                report[wf].update({'firstJobTime' : int(time.time())})
            if totalJobs and successJobs == totalJobs and not report[wf].get('lastJobTime', None):
                report[wf].update({'lastJobTime' : int(time.time())})
        except:
            pass

        # Figure out current status of workflow and transition times
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
                acquireTime = status['update_time']
            if status['status']	== 'closed-out':
                closeoutTime = status['update_time']
            if status['status']	== 'announced':
                announcedTime = status['update_time']

        # Build or modify the report dictionary for the WF
        report.setdefault(wf, {})

        if acquireTime and not report[wf].get('acquireTime', None):
            report[wf].update({'acquireTime':acquireTime})
        if closeoutTime and not report[wf].get('closeoutTime', None):
            report[wf].update({'closeoutTime':closeoutTime})
        if announcedTime and not report[wf].get('announcedTime', None):
            report[wf].update({'announcedTime':announcedTime})
        if completedTime and not report[wf].get('completedTime', None):
            report[wf].update({'completedTime':completedTime})

        report[wf].update({'priority':priority, 'status':finalStatus, 'type':requestType})
        report[wf].update({'totalLumis':targetLumis, 'totalEvents':targetEvents, })
        report[wf].setdefault('lumiPercents', {})
        report[wf].setdefault('eventPercents', {})

        for percentage in [1,10,25, 50, 65, 75, 80, 85, 90, 95, 98, 99]:
            percentReported = report[wf]['lumiPercents'].get(str(percentage), None)
            if not percentReported and lumiPercent >= percentage:
                report[wf]['lumiPercents'][percentage] = int(time.time())

            percentReported = report[wf]['eventPercents'].get(str(percentage), None)
            if not percentReported and eventPercent >= percentage:
                report[wf]['eventPercents'][percentage] = int(time.time())

        newCouchDoc = copy.deepcopy(oldCouchDoc)
        newCouchDoc.update(report[wf])

        # Fix up existing JSON. Can eventually remove
        for key in ['lumiPercents', 'eventPercents', 'jobPercents']:
            if newCouchDoc.get(key, None):
                for percentage in [1,10,25, 50, 65, 75, 80, 85, 90, 95, 98, 99]:
                    if newCouchDoc[key].get(percentage, None):
                        newCouchDoc[key][str(percentage)] = int(newCouchDoc[key][percentage])
                        del newCouchDoc[key][percentage]
                    if newCouchDoc[key].get(str(percentage), None):
                        newCouchDoc[key][str(percentage)] = int(newCouchDoc[key][str(percentage)])

        for key in ['acquireTime', 'closeoutTime', 'completedTime', 'firstJobTime', 'lastJobTime', 'announcedTime']:
            if newCouchDoc.get(key, None):
                newCouchDoc[key] = int(newCouchDoc[key])

        for key in ['jobPercent', 'lumiPercent', 'eventPercent']:
            if newCouchDoc.get(key, None):
                del newCouchDoc[key]

        # Queue the updated document for addition if it's changed.
        if oldCouchDoc != newCouchDoc:
            if wfExists:
                print "Workflow updated: ", wf
            else:
                print "Workflow created: ", wf

            try:
                couchdb.queue(newCouchDoc)
            except:
                print "Failed to queue ", newCouchDoc

    print "\ntotal %s requests retrieved" % len(result)

    # Commit all changes to CouchDB
    couchdb.commit()

    # Write all changes to Report file
    with open('report.json', 'w') as reportFile:
        json.dump(report, reportFile, indent=1)
