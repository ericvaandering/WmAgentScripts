from WMCoreService.WMStatsClient import WMStatsClient
from WMCoreService.DataStruct.RequestInfoCollection import RequestInfoCollection

if __name__ == "__main__":
    url = "https://cmsweb-testbed.cern.ch/couchdb/wmstats"
    testbedWMStats = WMStatsClient(url)
    print "start to getting job information from %s" % url
    print "will take a while\n"
    requests = testbedWMStats.getRequestByStatus(["running-closed", "completed"], jobInfoFlag = True)
    requestCollection = RequestInfoCollection(requests)
    result = requestCollection.getJSONData()
    print result
    print "\ntotal %s requests retrieved" % len(result)