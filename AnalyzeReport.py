#! /bin/env python

from __future__ import division
from __future__ import print_function

import json
import time

import ROOT

from WMCoreService.WMStatsClient import WMStatsClient
from WMCoreService.DataStruct.RequestInfoCollection import RequestInfoCollection

LAST_DAYS = 1.5 # Only things after 14:00 on April 15 might be correct
PERCENT_CHECK = '90'
PERCENT_TYPE = 'eventPercents'

def latency(end, start, midpoint):
    value = (end-midpoint)/(end-start)
#    print start, midpoint-start, end-midpoint, value
    return value

if __name__ == "__main__":

    wfLatencyH = ROOT.TH1F("wfLatency", "Total Latency",   100, 0.0, 1.0)
    wmLatencyH = ROOT.TH1F("wmLatency", "WMAgent Latency", 100, 0.0, 1.0)
    eventJobH = ROOT.TH1F("eventJobH", "Event-Job time",    100, -240, 240)
    lumiJobH = ROOT.TH1F("lumiJobH", "Lumi-Job time",      100, -240, 240)
    eventLumiH = ROOT.TH1F("eventLumiH", "Event-Lumi time", 100, -240, 240)

    wf2D = ROOT.TH2F("wf2D", "Total Latency vs. Walltime",   60, 0.0, 1.2, 50, 0, 2400)
    wm2D = ROOT.TH2F("wm2D", "WMAgent Latency vs. Walltime", 60, 0.0, 1.2, 50, 0, 2400)
    wf2Dt = ROOT.TH2F("wf2Dt", "Total Latency Time vs. Walltime",   50, 0, 400, 50, 0, 2400)
    wm2Dt = ROOT.TH2F("wm2Dt", "WMAgent Latency Time vs. Walltime", 50, 0, 400, 50, 0, 2400)
    wfp2D = ROOT.TH2F("wfp2D", "Total Latency vs. Priority",   60, 0.0, 1.2, 50, 0, 100000)
    wmp2D = ROOT.TH2F("wmp2D", "WMAgent Latency vs. Priority", 60, 0.0, 1.2, 50, 0, 100000)

    currentTime = int(time.time())
    openWMAgentWorkflows = 0
    openOpsWorkflows = 0
    try:
        with open('report.json', 'r') as reportFile:
            report = json.load(reportFile)

        for wf in report:
            record = report[wf]
            priority = record['priority']

            endTime = max(record.get('announcedTime', 0), record.get('completedTime', 0))
            if abs(currentTime-endTime) > LAST_DAYS*24*3600:
                continue

            try:
                wfLatency = latency(record['announcedTime'], record['acquireTime'],
                                    record[PERCENT_TYPE][PERCENT_CHECK])
                totalTime = (record['announcedTime']-record['acquireTime'])/3600.0
                if wfLatency >= 0 and wfLatency <= 1:
                    wfLatencyH.Fill(wfLatency)
                    wf2D.Fill(wfLatency, totalTime)
                    wf2Dt.Fill(wfLatency*totalTime, totalTime)
                    wfp2D.Fill(wfLatency, priority)
            except:
                #print "Not able to calculate WF latency for ", wf
                openOpsWorkflows += 1
                pass

            try:
                wmLatency = latency(record['completedTime'], record['acquireTime'],
                                    record[PERCENT_TYPE][PERCENT_CHECK])
                totalTime = (record['completedTime']-record['acquireTime'])/3600.0
                #wmLatency = latency(record['completedTime'], record['firstJobTime'],
                                    #record['percents'][PERCENT_CHECK])
                #totalTime = (record['acquireTime'] record['announcedTime'])/3600.0

                if wmLatency >= 0 and wmLatency <= 1:
                    wmLatencyH.Fill(wmLatency)
                    wm2D.Fill(wmLatency, totalTime)
                    wm2Dt.Fill(wmLatency*totalTime, totalTime)
                    wmp2D.Fill(wmLatency, priority)
            except:
                #print "Not able to calculate WM latency for ", wf
                openWMAgentWorkflows += 1
                pass


            try:
                eventLumiH.Fill((record['eventPercents'][PERCENT_CHECK] - record['lumiPercents'][PERCENT_CHECK])/3600)
                eventJobH.Fill((record['eventPercents'][PERCENT_CHECK] - record['jobPercents'][PERCENT_CHECK])/3600)
                lumiJobH.Fill((record['lumiPercents'][PERCENT_CHECK] - record['jobPercents'][PERCENT_CHECK])/3600)
            except:
                print("Not all types of percent done available for", wf)
                pass
        print("Number of open workflows:", openOpsWorkflows, "agent:", openWMAgentWorkflows)

    except IOError:
        print("No existing report. Exiting.")

    wmCanvas = ROOT.TCanvas("wm","test", 600,600)
    wmLatencyH.Draw()
    wmCanvas.SaveAs("WMAgentLatency.png")

    wfCanvas = ROOT.TCanvas("wf","test", 600,600)
    wfLatencyH.Draw()
    wfCanvas.SaveAs("TotalLatency.png")

    wmcCanvas = ROOT.TCanvas("wmc","test", 600,600)
    wm2D.Draw('BOX')
    wmcCanvas.SaveAs("WMAgentVsWalltime.png")

    wfcCanvas = ROOT.TCanvas("wfc","test", 600,600)
    wf2D.Draw('BOX')
    wfcCanvas.SaveAs("TotalVsWalltime.png")

    wmctCanvas = ROOT.TCanvas("wmct","test", 600,600)
    wm2Dt.Draw('BOX')
    wmctCanvas.SaveAs("WMAgentTimeVsWalltime.png")

    wfctCanvas = ROOT.TCanvas("wfct","test", 600,600)
    wf2Dt.Draw('BOX')
    wfctCanvas.SaveAs("TotalTimeVsWalltime.png")

    wmpCanvas = ROOT.TCanvas("wmp","test", 600,600)
    wmp2D.Draw('BOX')
    wmpCanvas.SaveAs("WMAgentVsPriority.png")

    wfpCanvas = ROOT.TCanvas("wfp","test", 600,600)
    wfp2D.Draw('BOX')
    wfpCanvas.SaveAs("TotalVsPriority.png")

    elCanvas = ROOT.TCanvas("eventLumi","test", 600,600)
    eventLumiH.Draw()
    elCanvas.SaveAs("Event-Lumi.png")

    ejCanvas = ROOT.TCanvas("eventJob","test", 600,600)
    eventJobH.Draw()
    ejCanvas.SaveAs("Event-Job.png")

    ljCanvas = ROOT.TCanvas("lumiJob","test", 600,600)
    lumiJobH.Draw()
    ljCanvas.SaveAs("Lumi-Job.png")

    raw_input("Press a key to exit.")
