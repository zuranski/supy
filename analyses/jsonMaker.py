#!/usr/bin/env python

import os,analysis,utils,calculables,steps,samples

class jsonMaker(analysis.analysis) :
    def listOfSteps(self,params) :
        return [ steps.Print.progressPrinter(2,300),
                 steps.Other.jsonMaker(),
                 ]

    def listOfCalculables(self,params) :
        return calculables.zeroArgs()

    def listOfSamples(self,params) :
        from samples import specify
        jw = calculables.Other.jsonWeight("/home/hep/elaird1/supy/Cert_160404-163757_7TeV_PromptReco_Collisions11_JSON.txt", acceptFutureRuns = False) #153/pb
        
        out = []
        out += specify(names = "Photon.Run2011A-PromptReco-v1.AOD.Henning1", weights = jw)
        out += specify(names = "Photon.Run2011A-PromptReco-v1.AOD.Henning2", weights = jw)
        out += specify(names = "Photon.Run2011A-PromptReco-v2.AOD.Ted1",     weights = jw)
        out += specify(names = "Photon.Run2011A-PromptReco-v2.AOD.Ted2",     weights = jw)
        return out

    def listOfSampleDictionaries(self) :
        return [samples.jetmet, samples.muon, samples.photon, samples.electron]

    def mainTree(self) :
        return ("lumiTree","tree")

    def otherTreesToKeepWhenSkimming(self) :
        return []
