#!/usr/bin/env python

import os,topAsymmShell,steps,calculables,samples,organizer,plotter,utils
import ROOT as r

class topAsymmKinfit(topAsymmShell.topAsymmShell) :
    def parameters(self) :
        pars = super(topAsymmKinfit,self).parameters()
        pars["effectiveLumi"] = 1000
        return pars

    def listOfCalculables(self,pars) :
        calcs = super(topAsymmKinfit,self).listOfCalculables(pars)
        calcs.append( calculables.Top.genTopSemiLeptonicWithinAcceptance( jetPtMin = 20, jetAbsEtaMax=3.5, lepPtMin=21, lepAbsEtaMax = 2.6))
        calcs.append( calculables.Top.genTopSemiLeptonicAccepted( pars['objects']['jet']))
        calcs.append( calculables.Top.genTopRecoIndex())
        calcs += [calculables.Jet.TagProbability(pars['objects']['jet'], pars['bVar'], letter) for letter in ['b','q','n']]
        calcs.append( calculables.Top.TopComboLikelihood(pars['objects']['jet'], pars['bVar']))
        return calcs

    def listOfSteps(self, pars) :
        obj = pars["objects"]
        lepton = obj[pars["lepton"]["name"]]
        lPtMin = pars["lepton"]["ptMin"]
        bVar = ("%s"+pars["bVar"]+"%s")%calculables.Jet.xcStrip(obj["jet"])
        
        return ([
            steps.Print.progressPrinter(),
            steps.Filter.pt("%sP4%s"%lepton, min = lPtMin, indices = "%sIndicesAnyIso%s"%lepton, index = 0),
            ]+topAsymmShell.topAsymmShell.cleanupSteps(pars)+[
            ]+topAsymmShell.topAsymmShell.selectionSteps(pars, withPlots = False) +[
            #steps.Filter.label('kinfit'),  steps.Top.kinFitLook("fitTopRecoIndex"),
            steps.Filter.value("genTopSemiLeptonicWithinAcceptance", min = True),
            steps.Filter.value("genTopSemiLeptonicAccepted", min = True),
            #]+sum([[steps.Filter.label(tag),steps.Top.jetProbability(obj['jet'], tag,bins,min,max)] \
            #       for tag,bins,min,max in [("JetProbabilityBJetTags",100,-0.2,3),
            #                                ("JetBProbabilityBJetTags",100,-1,12),
            #                                ("CombinedSecondaryVertexBJetTags",100,-0.1,1),
            #                                ("CombinedSecondaryVertexMVABJetTags",100,-0.1,1),
            #                       ("TrkCountingHighEffBJetTags",100,-1,15)
            #                                ]],[]) + [
            steps.Top.topProbLook(obj['jet']),
            steps.Other.assertNotYetCalculated("TopReconstruction"),
            steps.Filter.value("genTopRecoIndex", min = 0),
            steps.Filter.label('kinfit selected combo'),  steps.Top.kinFitLook("fitTopRecoIndex"),
            steps.Filter.label('kinfit true combo'),  steps.Top.kinFitLook("genTopRecoIndex"),
            steps.Filter.label('deltaR true combo'), steps.Top.combinatoricsLook("genTopRecoIndex", jets = obj['jet']),
            steps.Filter.label('deltaR selected combo'), steps.Top.combinatoricsLook("fitTopRecoIndex"),
            steps.Filter.multiplicity("%sIndices%s"%obj["jet"], min=4, max=6),
            steps.Filter.label('deltaR true combo'), steps.Top.combinatoricsLook("genTopRecoIndex", jets = obj['jet']),
            steps.Filter.label('deltaR selected combo'), steps.Top.combinatoricsLook("fitTopRecoIndex"),
            ])
    
    def listOfSamples(self,pars) :
        from samples import specify
        return (specify(names = "tt_tauola_mg", effectiveLumi = pars["effectiveLumi"], color = r.kRed) +
                #specify(names = "tt_tauola_pythia", effectiveLumi = pars["effectiveLumi"], color = r.kBlue) +
                [])

    def conclude(self) :
        for tag in self.sideBySideAnalysisTags() :
            #organize
            org=organizer.organizer( self.sampleSpecs(tag) )
            org.scale(toPdf=True)
            
            #plot
            pl = plotter.plotter(org,
                                 psFileName = self.psFileName(tag),
                                 doLog = False,
                                 #noSci = True,
                                 #pegMinimum = 0.1,
                                 blackList = ["lumiHisto","xsHisto","nJobsHisto"],
                                 )
            pl.plotAll()

