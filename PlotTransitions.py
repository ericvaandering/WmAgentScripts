#! /bin/env python

from __future__ import division
from __future__ import print_function

import json
import time
import pdb

import ROOT

from WMCoreService.WMStatsClient import WMStatsClient
from WMCoreService.DataStruct.RequestInfoCollection import RequestInfoCollection

LAST_DAYS = 30 # Only things after 14:00 on April 15 might be correct

if __name__ == "__main__":

    close_ann_H = ROOT.TH1F("close-announce", "Announce - closeout (hrs)",   100, 0.0, 200.0)
    close_comp_H = ROOT.TH1F("close-complete", "Closeout - complete (hrs)",   100, 0.0, 200.0)
    acq_new_H = ROOT.TH1F("acquire-new", "Acquire - new (hrs)",   100, 0.0, 300.0)
    ass_app_H = ROOT.TH1F("assigned-approved", "Assigned - approved-assigned (hrs)",   100, 0.0, 500.0)
    acq_ass_H = ROOT.TH1F("acquire-ass", "Acquire - assigned (hrs)",   40, 0.0, 10.0)

    currentTime = int(time.time())
    try:
        with open('times.json', 'r') as timeFile:
            times = json.load(timeFile)

        for wf in times['rows']:
            campaign, tier, status, priority, newTime, approvedTime, assignedTime, \
                acquireTime, firstJobTime, lastJobTime, completedTime, closeoutTime, \
                announcedTime, updateTime = wf['value']

            priority = int(priority)
            if not updateTime:
                updateTime = 0
            if abs(currentTime-updateTime) > LAST_DAYS*24*3600:
                continue
            if priority < 100:
                continue

            if closeoutTime and announcedTime:
                hrs = (announcedTime - closeoutTime)/3600
                close_ann_H.Fill(hrs)
                if hrs > 96:
                    print('LongAnnounce %6.1f %8d %s' % (hrs, priority, wf['id']))

            if closeoutTime and completedTime:
                hrs = (closeoutTime - completedTime)/3600
                close_comp_H.Fill(hrs)
                if hrs > 96:
                    print('LongCloseout %6.1f %8d %s' % (hrs, priority, wf['id']))

            if acquireTime and newTime:
                hrs = (acquireTime - newTime)/3600
                acq_new_H.Fill(hrs)
                if hrs > 240:
                    print('LongAcquireN %6.1f %8d %s' % (hrs, priority, wf['id']))

            if acquireTime and assignedTime:
                hrs = (acquireTime - assignedTime)/3600
                acq_ass_H.Fill(hrs)
                if hrs > 240:
                    print('LongAcquireA %6.1f %8d %s' % (hrs, priority, wf['id']))

            if assignedTime and approvedTime:
                hrs = (assignedTime - approvedTime)/3600
                ass_app_H.Fill(hrs)
                if hrs > 240:
                    print('LongAssign   %6.1f %8d %s' % (hrs, priority, wf['id']))


        #print("Number of open workflows:", openOpsWorkflows, "agent:", openWMAgentWorkflows)
        #print("Number of  workflows:", totalWf)

    except IOError:
        print("times.json does not exist. Exiting.")

    caCanvas = ROOT.TCanvas("ca","test", 600,600)
    close_ann_H.Draw()
    caCanvas.SaveAs("Announce_closeout.png")

    ccCanvas = ROOT.TCanvas("cc","test", 600,600)
    close_comp_H.Draw()
    ccCanvas.SaveAs("Closeout_complete.png")

    anCanvas = ROOT.TCanvas("an","test", 600,600)
    acq_new_H.Draw()
    anCanvas.SaveAs("Acquire_new.png")

    aaCanvas = ROOT.TCanvas("aa","test", 600,600)
    ass_app_H.Draw()
    aaCanvas.SaveAs("Assign_approve.png")

    a2Canvas = ROOT.TCanvas("a2","test", 600,600)
    acq_ass_H.Draw()
    a2Canvas.SaveAs("Acquire_assign.png")


    raw_input("Press a key to exit.")
