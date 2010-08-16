#!/usr/bin/env python
import os,sys,copy,cPickle,collections
sys.argv.append("-b")#set batch mode before importing ROOT
import utils,steps,samples
from analysisLooper import analysisLooper
import ROOT as r
#####################################
def globalSetup(listOfSourceFiles=[]) :
    for sourceFile in listOfSourceFiles :
        r.gROOT.LoadMacro(sourceFile+"+")
    r.gROOT.SetStyle("Plain")
    r.gStyle.SetPalette(1)
    #r.TH1.SetDefaultSumw2(True)#comment until ROOT 5.24, which has a needed bug-fix
    r.gErrorIgnoreLevel=2000
    r.gROOT.SetBatch(True)
#####################################
globalSetup(listOfSourceFiles=["pragmas.h","helpers.C"])
#####################################
class analysis :
    """base class for an analysis"""
    
    def __init__(self,name="name",outputDir="/tmp/",
                 listOfSteps=[],listOfCalculables=[],listOfSamples=None,listOfSampleDictionaries=[],
                 mainTree=("susyTree","tree"),otherTreesToKeepWhenSkimming=[("lumiTree","tree")],
                 printNodesUsed=False) :

        for arg in ["name","outputDir","listOfSteps",
                    "listOfCalculables","listOfSamples",
                    "otherTreesToKeepWhenSkimming","printNodesUsed"] :
            setattr(self,arg,eval(arg))

        self.fileDirectory=mainTree[0]
        self.treeName=mainTree[1]
        
        self.listOfLoopers=[]
        self.listOfOutputPlotFileNames=[]

        self.hasLooped=False

        self.addSamples(listOfSamples,listOfSampleDictionaries)

        #make output directory
        os.system("mkdir -p "+self.outputDir)
        
    def loop(self, profile = False, nCores = 1, splitJobsByInputFile = None, onlyMerge = False) :
        nCores = max(1,nCores)

        #restrict list of loopers to samples in self.listOfSamples
        self.pruneListOfLoopers()
        
        #execute in parallel commands to make file lists
        def inputFilesEvalWorker(q):
            while True:
                item = q.get()
                #write file list to disk
                outFile=open(os.path.expanduser(item.inputFileListFileName),"w")
                cPickle.dump(eval(item.fileListCommand),outFile)
                outFile.close()
                #notify queue
                q.task_done()
        utils.operateOnListUsingQueue(nCores,inputFilesEvalWorker,self.listOfLoopers)

        #associate file list to each looper
        for looper in self.listOfLoopers :
            someFile=open(looper.inputFileListFileName)
            looper.inputFiles=cPickle.load(someFile)
            someFile.close()
            os.remove(looper.inputFileListFileName)

        ##execute in series commands to make file lists        
        #for looper in self.listOfLoopers :
        #    looper.inputFiles=eval(looper.fileListCommand)

        if splitJobsByInputFile!=False and (splitJobsByInputFile or nCores>1) :
            self.splitLoopers()

        #prepare loopers
        self.makeParentDict(self.listOfLoopers)

        #loop over samples and make TFiles containing histograms
        if not profile :
            self.loopOverSamples(nCores,onlyMerge)
        else :
            self.profile(nCores,onlyMerge) #profile the code while doing so
        self.hasLooped=True            

    def pruneListOfLoopers(self) :
        if self.listOfSamples==None : return #None (default) means use all samples
        self.listOfLoopers = filter(lambda looper: looper.name in [x.name for x in self.listOfSamples], self.listOfLoopers)

    def sampleSpecs(self) :
        #prune list of loopers if self.loop has not been called
        if not self.hasLooped : self.pruneListOfLoopers()
        
        outList=[]
        if (not hasattr(self,"parentDict")) or len(self.parentDict)==0 :
            for looper in self.listOfLoopers :
                someDict={}
                someDict["name"]               = looper.name
                someDict["outputPlotFileName"] = looper.outputPlotFileName
                someDict["color"]              = looper.color
                someDict["markerStyle"]        = looper.markerStyle
                outList.append(someDict)
        else :
            for parent in self.parentDict :
                iSomeLooper=self.parentDict[parent][0]
                someLooper=self.listOfLoopers[iSomeLooper]
                someDict={}
                someDict["name"] = parent
                someDict["outputPlotFileName"]=someLooper.outputPlotFileName.replace(someLooper.name,someLooper.parentName)
                someDict["color"]=someLooper.color
                someDict["markerStyle"]=someLooper.markerStyle
                outList.append(someDict)
        return outList

    def makeOutputPlotFileName(self,sampleName,isChild=False) :
        answer=self.outputDir+"/"+self.name+"_"+sampleName+"_plots.root"
        if not isChild :
            self.listOfOutputPlotFileNames.append(answer)
        return answer

    def addSamples(self, listOfSamples, listOfSampleDictionaries, computeEntriesForReport = False) :
        mergedDict = samples.SampleHolder()
        map(mergedDict.update,listOfSampleDictionaries)

        #print mergedDict
        ptHatMinDict={}
        for sampleSpec in listOfSamples :
            sampleName = sampleSpec.name
            sampleTuple = mergedDict[sampleName]
            isMc = sampleTuple.lumi==None
            fileListCommand=sampleTuple.filesCommand
            nFilesMax=sampleSpec.nFilesMax
            nEventsMax=sampleSpec.nEventsMax

            lumiWarn = False
            if (not isMc) and (nEventsMax!=-1 or nFilesMax!=-1) :
                print "Warning, not running over full data sample: wrong lumi?"
                lumiWarn = True
                
            if nFilesMax >= 0 :
                fileListCommand = "(%s)[:%d]"%(fileListCommand,nFilesMax)
                
            listOfSteps = []
            if isMc : listOfSteps = steps.adjustStepsForMc(self.listOfSteps)
            else :    listOfSteps = steps.adjustStepsForData(self.listOfSteps)

            if sampleTuple.ptHatMin :
                ptHatMinDict[sampleName]=sampleTuple.ptHatMin

            self.listOfLoopers.append(analysisLooper(self.fileDirectory,
                                                     self.treeName,
                                                     self.otherTreesToKeepWhenSkimming,
                                                     self.outputDir,
                                                     self.makeOutputPlotFileName(sampleName),
                                                     listOfSteps,
                                                     self.listOfCalculables,
                                                     sampleSpec,
                                                     fileListCommand,
                                                     sampleTuple.xs,
                                                     sampleTuple.lumi,
                                                     lumiWarn,
                                                     computeEntriesForReport,
                                                     self.printNodesUsed,
                                                     )
                                      )
        for thing in mergedDict.overlappingSamples :
            minPtHatsAndNames=[]
            for sampleName in thing.samples :
                if sampleName not in ptHatMinDict : continue
                minPtHatsAndNames.append( (ptHatMinDict[sampleName],sampleName) )
            self.manageNonBinnedSamples(minPtHatsAndNames,thing.useRejectionMethod)
        return

    def manageNonBinnedSamples(self,ptHatLowerThresholdsAndSampleNames=[],useRejectionMethod=True) :
        if not useRejectionMethod :
            raise Exception("the other method of combining non-binned samples is not yet implemented")
        looperIndexDict={}
        for item in ptHatLowerThresholdsAndSampleNames :
            ptHatLowerThreshold=item[0]
            sampleName=item[1]

            #find the associated looper
            for iLooper in range(len(self.listOfLoopers)) :
                looper=self.listOfLoopers[iLooper]
                if sampleName==looper.name :
                    looperIndexDict[ptHatLowerThreshold]=iLooper
                for step in looper.steps :
                    if step.__doc__==step.skimmerStepName :
                        raise Exception("do not manage non-binned samples when skimming")


        ptHatLowerThresholdsAndSampleNames.sort()
        for iItem in range(len(ptHatLowerThresholdsAndSampleNames)) :

            thisPtHatLowerThreshold=ptHatLowerThresholdsAndSampleNames[iItem][0]
            thisLooperIndex=looperIndexDict[thisPtHatLowerThreshold]

            #adjust cross sections
            if iItem<len(ptHatLowerThresholdsAndSampleNames)-1 :
                nextPtHatLowerThreshold=ptHatLowerThresholdsAndSampleNames[iItem+1][0]
                nextLooperIndex=looperIndexDict[nextPtHatLowerThreshold]
                self.listOfLoopers[thisLooperIndex].xs-=self.listOfLoopers[nextLooperIndex].xs

                if useRejectionMethod :
                    self.listOfLoopers[thisLooperIndex].needToConsiderPtHatThresholds=False
                    steps.insertPtHatFilter(self.listOfLoopers[thisLooperIndex].steps,nextPtHatLowerThreshold)

            #inform relevant loopers of the ptHat thresholds
            for index in looperIndexDict.values() :
                self.listOfLoopers[index].ptHatThresholds.append(float(thisPtHatLowerThreshold))
                if not useRejectionMethod :
                    self.listOfLoopers[index].needToConsiderPtHatThresholds=True
        return
    
    def splitLoopers(self) :
        outListOfLoopers=[]
        for looper in self.listOfLoopers :
            for iFileName in range(len(looper.inputFiles)) :
                sampleName=looper.name+"_"+str(iFileName)
                outListOfLoopers.append(copy.deepcopy(looper))
                outListOfLoopers[-1].name=sampleName
                outListOfLoopers[-1].outputPlotFileName=self.makeOutputPlotFileName(sampleName,isChild=True)
                outListOfLoopers[-1].setOutputFileNames()
                outListOfLoopers[-1].inputFiles=[looper.inputFiles[iFileName]]
                outListOfLoopers[-1].doSplitMode(looper.name)
        self.listOfLoopers=outListOfLoopers

    def makeParentDict(self,listOfLoopers) :
        self.parentDict={}
        for iLooper in range(len(listOfLoopers)) :
            looper=listOfLoopers[iLooper]
            if looper.splitMode :
                if looper.parentName in self.parentDict :
                    self.parentDict[looper.parentName].append(iLooper)
                else :
                    self.parentDict[looper.parentName]=[iLooper]

    def looperPrint(self,parent,looper) :
        print utils.hyphens
        print parent
        looper.quietMode=False
        looper.printStats()
        print utils.hyphens

    def mergeSplitOutput(self,cleanUp) :
        #combine output
        for parent in self.parentDict :
            #print parent,parentDict[parent]
            iSomeLooper=self.parentDict[parent][0]
            someLooper=self.listOfLoopers[iSomeLooper]
            outputPlotFileName=someLooper.outputPlotFileName.replace(someLooper.name,parent)
            inFileList=[]
            displayFileDict=collections.defaultdict(list)
            skimmerFileDict=collections.defaultdict(list)
            runLsDict=collections.defaultdict(list)
            jsonFileDict=collections.defaultdict(list)
            
            isFirstLooper=True
            for iLooper in self.parentDict[parent] :
                #add the root file to hadd command
                inFileList.append(self.listOfLoopers[iLooper].outputPlotFileName)

                #read in the step and calculable data
                stepAndCalculableDataFileName=os.path.expanduser(self.listOfLoopers[iLooper].outputStepAndCalculableDataFileName)
                stepAndCalculableDataFile=open(stepAndCalculableDataFileName)
                stepDataList,calculableConfigDict,listOfLeavesUsed=cPickle.load(stepAndCalculableDataFile)
                stepAndCalculableDataFile.close()

                #clean up
                if cleanUp : os.remove(stepAndCalculableDataFileName)

                #add stats to those of someLooper
                for i in range(len(someLooper.steps)) :
                    #need to zero in case sample is split but not run in multi mode
                    if isFirstLooper :
                        someLooper.steps[i].nTotal=0
                        someLooper.steps[i].nPass =0
                        someLooper.steps[i].nFail =0
                    someLooper.steps[i].nTotal+=stepDataList[i]["nTotal"]
                    someLooper.steps[i].nPass +=stepDataList[i]["nPass" ]
                    someLooper.steps[i].nFail +=stepDataList[i]["nFail" ]

                    if someLooper.steps[i].__doc__==someLooper.steps[i].displayerStepName :
                        displayFileDict[i].append(stepDataList[i]["outputFileName"])
                    if someLooper.steps[i].__doc__==someLooper.steps[i].skimmerStepName :
                        skimmerFileDict[i].append(stepDataList[i]["outputFileName"])
                    if someLooper.steps[i].__doc__==someLooper.steps[i].jsonMakerStepName :
                        runLsDict[i].append(stepDataList[i]["runLsDict"])
                        jsonFileDict[i].append(stepDataList[i]["outputFileName"])

                if isFirstLooper :
                    someLooper.calculableConfigDict={}
                    someLooper.listOfLeavesUsed=[]
                for item in calculableConfigDict :
                    someLooper.calculableConfigDict[item]=calculableConfigDict[item]
                someLooper.listOfLeavesUsed.extend(listOfLeavesUsed)
                isFirstLooper=False

            self.looperPrint(parent,someLooper)
            inFiles=" ".join(inFileList)
            cmd="hadd -f "+outputPlotFileName+" "+inFiles+" | grep -v 'Source file' | grep -v 'Target path' | grep -v 'Found subdirectory'"
            #print cmd
            hAddOut=utils.getCommandOutput2(cmd)
            #clean up
            if cleanUp :
                for fileName in inFileList : os.remove(fileName)
            
            print hAddOut[:-1].replace("Target","The output")+" has been written."
            print utils.hyphens

            self.mergeDisplays(displayFileDict,someLooper)
            self.reportEffectiveXs(skimmerFileDict,someLooper)

            if len(jsonFileDict.values())>0 and len(jsonFileDict.values()[0])>0 :
                utils.mergeRunLsDicts(runLsDict,jsonFileDict.values()[0][0],printHyphens=True)
            
    def reportEffectiveXs(self,skimmerFileDict,someLooper) :
        if len(skimmerFileDict)>0 :
            for skimmerIndex,skimFileNames in skimmerFileDict.iteritems() :
                if someLooper.xs==None :
                    print "The",len(skimFileNames),"skim files have been written."
                else :
                    effXs=0.0
                    nEvents=someLooper.steps[0].nTotal
                    nPass=someLooper.steps[skimmerIndex].nPass
                    if nEvents>0 : effXs=(someLooper.xs+0.0)*nPass/nEvents
                    print "The",len(skimFileNames),"skim files have effective XS =",someLooper.xs,"*",nPass,"/",nEvents,"=",effXs
                print "( e.g.",skimFileNames[0],")"
                print utils.hyphens

    def mergeDisplays(self,displayFileDict,someLooper) :
        if len(displayFileDict)>0 :
            outputFileName=displayFileDict.values()[0][0].replace(someLooper.name,someLooper.parentName).replace(".root",".ps")
            utils.psFromRoot(displayFileDict.values()[0],outputFileName,beQuiet=False)
            print utils.hyphens

    def profile(self,nCores,onlyMerge) :
        global runFunc
        runFunc=self.loopOverSamples
        import cProfile
        if nCores>1 : print "setting nCores=1 to profile"        
        cProfile.run("analysis.runFunc(1,%s)"%onlyMerge,"resultProfile.out")

    def loopOverSamples(self,nCores,onlyMerge) :
        #loop over events for each looper
        if not onlyMerge :
            if nCores>1 : utils.operateOnListUsingQueue(nCores,utils.goWorker,self.listOfLoopers)
            else :        map(lambda x : x.go(),self.listOfLoopers)

        #merge the output
        self.mergeSplitOutput(cleanUp = not onlyMerge)
