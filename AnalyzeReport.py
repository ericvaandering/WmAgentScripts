#! /bin/env python

from __future__ import division

import json
import time

import ROOT

from WMCoreService.WMStatsClient import WMStatsClient
from WMCoreService.DataStruct.RequestInfoCollection import RequestInfoCollection

LAST_DAYS = 7
PERCENT_CHECK = '95'


def latency(end, start, midpoint):
    value = (end-midpoint)/(end-start)
#    print start, midpoint-start, end-midpoint, value
    return value

if __name__ == "__main__":

    wfLatencyH = ROOT.TH1F("wfLatency", "Total Latency",   100, 0.0, 1.0)
    wmLatencyH = ROOT.TH1F("wmLatency", "WMAgent Latency", 100, 0.0, 1.0)

    wf2D = ROOT.TH2F("wf2D", "Total Latency",   100, 0.0, 1.0, 100, 0, 2400)
    wm2D = ROOT.TH2F("wm2D", "WMAgent Latency", 100, 0.0, 1.0, 100, 0, 2400)
    wfp2D = ROOT.TH2F("wfp2D", "Total Latency vs. Priority",   100, 0.0, 1.0, 100, 0, 100000)
    wmp2D = ROOT.TH2F("wmp2D", "WMAgent Latency vs. Priority", 100, 0.0, 1.0, 100, 0, 100000)

    currentTime = time.time()
    openWorkflows = 0
    try:
        with open('report.json', 'r') as reportFile:
            report = json.load(reportFile)

        for wf in report:
            record = report[wf]
            priority = record['priority']
            try:
                wfLatency = latency(record['announcedTime'], record['acquireTime'],
                                    record['percents'][PERCENT_CHECK])
                totalTime = (record['announcedTime']-record['acquireTime'])/3600.0
                if wfLatency >= 0 and wfLatency <= 1:
                    wfLatencyH.Fill(wfLatency)
                    wf2D.Fill(wfLatency, totalTime)
                    wfp2D.Fill(wfLatency, priority)
            except:
                #print "Not able to calculate WF latency for ", wf
                pass

            try:
                wmLatency = latency(record['completedTime'], record['acquireTime'],
                                    record['percents'][PERCENT_CHECK])
                totalTime = (record['completedTime']-record['acquireTime'])/3600.0
                #wmLatency = latency(record['completedTime'], record['firstJobTime'],
                                    #record['percents'][PERCENT_CHECK])
                #totalTime = (record['acquireTime'] record['announcedTime'])/3600.0

                if wmLatency >= 0 and wmLatency <= 1:
                    wmLatencyH.Fill(wmLatency)
                    wm2D.Fill(wmLatency, totalTime)
                    wmp2D.Fill(wmLatency, priority)
            except:
                #print "Not able to calculate WM latency for ", wf
                pass

        print "Number of open workflows:", openWorkflows

    except IOError:
        print "No existing report. Exiting."

    wmCanvas = ROOT.TCanvas("wm","test", 600,600);
    wmLatencyH.Draw()
    wmCanvas.SaveAs("WMAgentLatency.pdf");

    wfCanvas = ROOT.TCanvas("wf","test", 600,600);
    wfLatencyH.Draw()
    wfCanvas.SaveAs("TotalLatency.png");

    wmcCanvas = ROOT.TCanvas("wmc","test", 600,600);
    wm2D.Draw('BOX')
    wmcCanvas.SaveAs("WMAgentCorrelation.png");

    wfcCanvas = ROOT.TCanvas("wfc","test", 600,600);
    wf2D.Draw('BOX')
    wfcCanvas.SaveAs("TotalCorrelation.png");

    wmpCanvas = ROOT.TCanvas("wmp","test", 600,600);
    wmp2D.Draw('BOX')
    wmpCanvas.SaveAs("WMAgentPriority.png");

    wfpCanvas = ROOT.TCanvas("wfp","test", 600,600);
    wfp2D.Draw('BOX')
    wfpCanvas.SaveAs("TotalPriority.png");
