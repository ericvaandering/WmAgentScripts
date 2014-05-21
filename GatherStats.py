from __future__ import division

import cjson
import copy
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

    url = "https://cmsweb.cern.ch/couchdb/wmstats"
    WMStats = WMStatsClient(url)
    print "Getting job information from %s. Please wait." % url
    requests = WMStats.getRequestByStatus(WMStatsClient.ACTIVE_STATUS, jobInfoFlag = True)

    requestCollection = RequestInfoCollection(requests)
    result = requestCollection.getJSONData()
    requestsDict = requestCollection.getData()
    print "Total %s requests retrieved\n" % len(result)

    report = {}
    for wf in result.keys():
        # Store a copy of the CouchDB document so we can compare later before updating
        if couchdb.documentExists(wf):
            oldCouchDoc = couchdb.document(wf)
            wfExists = True
        else:
            oldCouchDoc = CouchDoc(id=wf)
            wfExists = False

        newCouchDoc = copy.deepcopy(oldCouchDoc)
        ancientCouchDoc = copy.deepcopy(oldCouchDoc)
        report[wf] = oldCouchDoc
        # FIXME: remove report, only have two instances of couchDoc

        # Basic parameters of the workflow
        priority = requests[wf]['priority']
        requestType = requests[wf]['request_type']
        targetLumis = requests[wf].get('input_lumis', 0)
        targetEvents = requests[wf].get('input_events', 0)
        campaign = requests[wf]['campaign']
        prep_id = requests[wf]['prep_id']
        outputdatasets = requests[wf]['outputdatasets']

        # Can be an empty list, full list, empty string, or non-empty string!
        inputdataset = requests[wf]['inputdataset']
        if isinstance(inputdataset, (list,)):
            if inputdataset:
                inputdataset = inputdataset[0]
            else:
                inputdataset = ''

        outputTier = 'GEN-SIM'
        if inputdataset:
            outputTier = 'Unknown'
            inputTier = inputdataset.split('/')[-1]
            if inputTier in ['GEN']:
                outputTier = 'LHE'
            if inputTier in ['RAW', 'RECO']:
                outputTier = 'AOD'
            if inputTier in ['GEN-SIM']:
                outputTier = 'AODSIM'
        if outputTier == 'GEN-SIM':
            if len(outputdatasets) == 1:
                testTier = outputdatasets[0].split('/')[-1]
                if testTier in ['GEN']:
                    outputTier = 'STEP0'

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
        newTime = None
        requestDate = None
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
            if status['status']	== 'new':
                newTime = status['update_time']

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
        if newTime and not report[wf].get('newTime', None):
            report[wf].update({'newTime':newTime})

        try:
            dt = requests[wf]['request_date']
            requestDate = '%4.4d-%2.2d-%2.2d %2.2d:%2.2d:%2.2d' % tuple(dt)
            report[wf].update({'requestDate' : requestDate})
        except:
            pass

        report[wf].update({'priority':priority, 'status':finalStatus, 'type':requestType})
        report[wf].update({'totalLumis':targetLumis, 'totalEvents':targetEvents, })
        report[wf].update({'campaign' : campaign, 'prepID' : prep_id, 'outputTier' : outputTier, })
        report[wf].update({'outputDatasets' : outputdatasets, 'inputDataset' : inputdataset, })

        report[wf].setdefault('lumiPercents', {})
        report[wf].setdefault('eventPercents', {})
        lumiProgress = 0
        eventProgress = 0
        for percentage in [1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 98, 99, 100]:
            percent = str(percentage)
            percentReported = report[wf]['lumiPercents'].get(percent, None)
            if not percentReported and lumiPercent >= percentage:
                report[wf]['lumiPercents'][percent] = int(time.time())
            if lumiPercent >= percentage:
                lumiProgress = percentage

            percentReported = report[wf]['eventPercents'].get(percent, None)
            if not percentReported and eventPercent >= percentage:
                report[wf]['eventPercents'][percent] = int(time.time())
            if eventPercent >= percentage:
                eventProgress = percentage

        report[wf].update({'eventProgress' : eventProgress, 'lumiProgress' : lumiProgress,  })

        newCouchDoc.update(report[wf])

        # Queue the updated document for addition if it's changed.
        if ancientCouchDoc != newCouchDoc:
            if wfExists:
                print "Workflow updated: ", wf
            else:
                print "Workflow created: ", wf

            try:
                newCouchDoc['updateTime'] = int(time.time())
                report[wf]['updateTime'] = int(time.time())
                cjson.encode(newCouchDoc) # Make sure it encodes before trying to queue
                couchdb.queue(newCouchDoc)
            except:
                print "Failed to queue document:\n", pprint.pprint(newCouchDoc)

    # Commit all changes to CouchDB
    couchdb.commit()

