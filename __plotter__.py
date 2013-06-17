import ROOT as r
import os,math,string,itertools
import utils,configuration as conf
from supy import whereami
##############################
def setupStyle() :
    r.gROOT.SetStyle("Plain")
    r.gStyle.SetPalette(1)
    r.gStyle.SetOptStat(1111111)
##############################
def setupTdrStyle() :
    r.gROOT.ProcessLine(".L %s/cpp/tdrstyle.C"%whereami())
    r.setTDRStyle()
    #tweaks
    r.tdrStyle.SetPadRightMargin(0.06)
    r.tdrStyle.SetErrorX(r.TStyle().GetErrorX())
    r.gStyle.SetPalette(1)
##############################
def combineBinContentAndError(histo, binToContainCombo, binToBeKilled) :
    xflows     = histo.GetBinContent(binToBeKilled)
    xflowError = histo.GetBinError(binToBeKilled)

    if xflows==0.0 : return #ugly

    currentContent = histo.GetBinContent(binToContainCombo)
    currentError   = histo.GetBinError(binToContainCombo)
    
    histo.SetBinContent(binToBeKilled, 0.0)
    histo.SetBinContent(binToContainCombo, currentContent+xflows)
    
    histo.SetBinError(binToBeKilled, 0.0)
    histo.SetBinError(binToContainCombo, math.sqrt(xflowError**2+currentError**2))
##############################
def shiftUnderAndOverflows(dimension, histos, dontShiftList = []) :
    if dimension!=1 : return
    for histo in histos:
        if not histo : continue
        if issubclass(type(histo),r.TGraph) : continue
        if histo.GetName() in dontShiftList : continue
        bins = histo.GetNbinsX()
        entries = histo.GetEntries()
        combineBinContentAndError(histo, binToContainCombo = 1   , binToBeKilled = 0     )
        combineBinContentAndError(histo, binToContainCombo = bins, binToBeKilled = bins+1)
        histo.SetEntries(entries)
##############################
def dimensionOfHisto(histos) :
    def D(h) : return 2 if issubclass(type(h),r.TH2) else 1 if (issubclass(type(h),r.TH1) or issubclass(type(h),r.TGraph)) else 0
    dimensions = set([D(h) for h in histos if h])
    assert len(dimensions)==1,"inconsistent histogram dimensions\n{%s}"%','.join(h.GetName() for h in histos if h)
    return next(iter(dimensions))
##############################        
def metFit(histo) :
    funcName="func"
    func=r.TF1(funcName,"[0]*x*exp( -(x-[1])**2 / (2.0*[2])**2 )/[2]",0.5,30.0)
    func.SetParameters(1.0,5.0,3.0)
    histo.Fit(funcName,"lrq","sames")
    histo.GetFunction(funcName).SetLineWidth(1)
    histo.GetFunction(funcName).SetLineColor(histo.GetLineColor())
    return func
##############################
def makeAlphaTFunc(alphaTValue) :
    alphaTFunc=r.TF1("alphaTCurve"+str(alphaTValue),
                     "1.0-2.0*("+str(alphaTValue)+")*sqrt(1.0-x*x)",
                     0.0,1.0)
    alphaTFunc.SetLineColor(r.kBlack)
    alphaTFunc.SetLineWidth(1)
    alphaTFunc.SetNpx(300)
    return alphaTFunc
##############################
def adjustPad(pad, anMode = False, pushLeft = False) :
    if not anMode :
        r.gPad.SetRightMargin(0.15)
        r.gPad.SetTicky()
        r.gPad.SetTickx()
        if pushLeft : r.gPad.SetLeftMargin(0.4)
##############################
def inDict(d, key, default) :
    return d[key] if key in d else default
##############################
class plotter(object) :
    def __init__(self,
                 someOrganizer,
                 pdfFileName = "out.pdf",
                 samplesForRatios = ("",""),
                 sampleLabelsForRatios = ("",""),
                 printRatios = False,
                 showStatBox = True,
                 doLog = True,
                 pegMinimum = None,
                 anMode = False,
                 drawYx = False,
                 doMetFit = False,
                 doColzFor2D = True,
                 compactOutput = False,
                 noSci = False,
                 showErrorsOnDataYields = False,
                 linYAfter = None,
                 nLinesMax = 22,
                 nColumnsMax = 75,
                 pageNumbers = True,
                 latexYieldTable = False,
                 detailedCalculables = False,
                 shiftUnderOverFlows = True,
                 rowColors = [r.kBlack],
                 rowCycle = 5,
                 omit2D = False,
                 dependence2D = False,
                 dontShiftList = ["lumiHisto","xsHisto","nJobsHisto"],
                 blackList = [],
                 whiteList = [],
                 pushLeft = False,
                 doCorrTable = False
                 ) :
        for item in ["someOrganizer","pdfFileName","samplesForRatios","sampleLabelsForRatios","doLog","linYAfter","latexYieldTable",
                     "pegMinimum", "anMode","drawYx","doMetFit","doColzFor2D","nLinesMax","nColumnsMax","compactOutput","pageNumbers",
                     "noSci", "showErrorsOnDataYields", "shiftUnderOverFlows","dontShiftList","whiteList","blackList","showStatBox", "doCorrTable",
                     "detailedCalculables", "rowColors","rowCycle","omit2D","dependence2D", "printRatios","pushLeft"] :
            setattr(self,item,eval(item))

        self.nLinesMax -= nLinesMax/rowCycle
        if "counts" not in self.whiteList : self.blackList.append("counts")
        self.plotRatios = self.samplesForRatios!=("","")
        self.canvas = r.TCanvas("canvas", "canvas", 500, 500) if self.anMode else r.TCanvas()
        self.formerMaxAbsI = -1
        self.pageNumber = -1
        self.pdfOptions = ''
        if pdfFileName[-3:]==".ps" : self.pdfFileName = self.pdfFileName.replace('.ps','.pdf')

        #used for making latex tables
        self.cutDict = {}
        self.yieldDict = {}
        self.sampleList = []

        #used for making corrTable
        self.corrTableData = []
        self.corrTableMC = []

    def plotAll(self) :
        print utils.hyphens
        setupStyle()

        self.printCanvas("[")
        text1 = self.printTimeStamp()
        text2 = self.printNEventsIn()
        self.flushPage()

        if self.detailedCalculables :
            blocks = filter(None, utils.splitList( self.someOrganizer.formattedCalculablesGraph(), ('','','')))
            for page in utils.pages(blocks,50) :
                text3 = self.printCalculablesDetailed(page)
                self.flushPage()
        else :
            text3 = self.printCalculables(selectImperfect = False)
            self.flushPage()
            text4 = self.printCalculables(selectImperfect = True)
            self.flushPage()
            
        nSelectionsPrinted = 0
        selectionsSoFar=[]
        for step in self.someOrganizer.steps :
            if step.isSelector : selectionsSoFar.append(step)
            elif nSelectionsPrinted<len(selectionsSoFar) and not self.compactOutput :
                self.printSteps(selectionsSoFar, printAll = self.compactOutput)
                nSelectionsPrinted = len(selectionsSoFar)
            if (step.name, step.title)==self.linYAfter : self.doLog = False
            for plotName in sorted(step.keys()) :
                if self.compactOutput and plotName not in self.whiteList : continue
                if plotName in self.blackList : continue
                self.onePlotFunction(step[plotName])

        self.printCanvas("]")
        print self.pdfFileName, 'has been written'
        if self.latexYieldTable : self.printLatexYieldTable()
        if self.doCorrTable : self.printCorrTable()
        print utils.hyphens

    def oneTable(self, f, columnSpecs = "", header = "", rows = []) :
        f.write(r'''
\begin{table}
\begin{tabular}{''')
        f.write(columnSpecs)
        f.write(r'''}
\hline\hline
''')
        f.write(header)
        f.write(r''' \\ \hline
''')
        for row in rows : f.write("%s%s"%(row,"\n"))
        f.write(r'''\hline\hline
\end{tabular}
\end{table}
''')

    def printLatexYieldTable(self, blackList = ["passFilter"]) :
        texFile = self.pdfFileName.replace(".pdf",".tex")
        f = open(texFile, "w")
        f.write(r'''
\documentclass[landscape]{article}
\usepackage[landscape]{geometry}
\begin{document}
''')

        #table of letter <--> cut name,desc
        filtered = []
        descDict = {}
        rows = []
        for key in sorted(self.cutDict.keys(), key = string.ascii_letters.index) :
            name,desc = self.cutDict[key]
            if name in blackList :
                filtered.append(key)
                continue
            for item in [name, desc] :
                if item.count("@") : print "WARNING: @ replaced by ! in %s"%item
            name2 = name.replace("@","!")
            desc2 = desc.replace("@","!")
            descDict[key] = r'\verb@%s@'%desc2
            rows.append( r'%s & \verb@%s@ & %s \\'%(key, name2, descDict[key]) )

        self.oneTable(f, columnSpecs = "llr", header = "letter & name & description", rows = rows)


        #tables of cut letter <--> yields; cut desc <--> yields
        for i in range(len(self.sampleList)) :
            if self.sampleList[i].count("@") : print "WARNING: @ replaced by ! in %s"%self.sampleList[i]
            self.sampleList[i] = self.sampleList[i].replace("@","!").lstrip().rstrip()
        names = r"@ & \verb@".join(self.sampleList)
        names = names.join([r"\verb@", "@"])

        rowsLettered = []
        rowsDescribed = []
        for key in sorted(self.yieldDict.keys(), key = string.ascii_letters.index) :
            if key in filtered : continue
            yields = self.yieldDict[key]
            for i in range(len(yields)) :
                if yields[i].count("@") : print "WARNING: @ replaced by ! in %s"%yields[i]
                yields[i] = yields[i].replace("@","!").lstrip().rstrip()
                
            yields = r"@ & \verb@".join(yields)
            yields = yields.join([r"\verb@", "@"])
            rowsLettered.append( r'%s & %s \\'%(key, yields) )
            rowsDescribed.append( r'%s & %s \\'%(descDict[key], yields) )

        self.oneTable(f, columnSpecs = "l"+"c"*len(self.sampleList), header = "letter & "+names, rows = rowsLettered)
        self.oneTable(f, columnSpecs = "l"+"c"*len(self.sampleList), header = "description & "+names, rows = rowsDescribed)

        f.write('''\end{document}''')
        f.close()
        print "The output file \""+texFile+"\" has been written."
        
    def individualPlots(self, plotSpecs, newSampleNames = {}, cms = True, preliminary = True, tdrStyle = True, histos=None) :
        def goods(spec,histos) :
            #if histos is not None: return histos,None
            for item in ["stepName", "stepDesc", "plotName"] :
                if item not in spec : return

            histoList = []
            nMasters = [step.name for step in self.someOrganizer.steps].count("Master")
            if nMasters!=1 : print "I have %d Master step(s)."%nMasters
            
            for step in self.someOrganizer.steps :
                if (step.name, step.title) != (spec["stepName"], spec["stepDesc"]) : continue
                if spec["plotName"] not in step : continue
                histoList.append(step[spec["plotName"]])

            assert histoList,str(spec)
            histos = histoList[spec["index"] if "index" in spec else 0]
            if "sampleWhiteList" not in spec :
                return histos,None
            else :
                return histos,[not (sample["name"] in spec["sampleWhiteList"]) for sample in self.someOrganizer.samples]

        def onlyDumpToFile(histos, spec) :
            if "onlyDumpToFile" in spec and spec["onlyDumpToFile"] :
                rootFileName = self.pdfFileName.replace(".pdf","_%s.root"%spec["plotName"])
                f = r.TFile(rootFileName, "RECREATE")
                for h in histos :
                    h.Write()
                f.Close()
                print "The output file \"%s\" has been written."%rootFileName
                return True
            return False

        def rebin(h, spec) :
            if "reBinFactor" in spec :
                for histo in h :
                    if histo!=None : histo.Rebin(spec["reBinFactor"])
                
        def setTitles(h, spec) :
            if "newTitle" in spec :
                for histo in h :
                    histo.SetTitle(spec["newTitle"])

        def stylize(h) :
            for histo in h :
                histo.UseCurrentStyle()

        def setRanges(h, spec) :
            for item in ["xRange", "yRange"] :
                if item not in spec : continue
                for histo in h :
                    method = "Get%saxis"%item[0].capitalize()
                    getattr(histo, method)().SetRangeUser(*spec[item])

        print utils.hyphens
        if tdrStyle : setupTdrStyle()

        for spec in plotSpecs :
            histos,ignoreHistos = goods(spec,histos)
            if histos==None : continue
            
            if onlyDumpToFile(histos, spec) : continue
            rebin(histos, spec)
            setRanges(histos, spec)
            setTitles(histos, spec)
            stylize(histos)

            individual = {"legendCoords": (0.55, 0.55, 0.85, 0.85),
                          "reverseLegend": False,
                          "stampCoords": (0.75, 0.5),
                          "ignoreHistos": ignoreHistos
                          }
            for key in spec :
                if key in individual :
                    individual[key] = spec[key]

            stuff,pads = self.onePlotFunction(histos, individual = individual)
            if ("stamp" not in spec) or spec["stamp"] :
                utils.cmsStamp(lumi = self.someOrganizer.lumi, cms = cms, preliminary = preliminary, coords = individual["stampCoords"])

            args = {"name":spec["plotName"],
                    "tight":False,#self.anMode
                    "alsoC":spec["alsoC"] if "alsoC" in spec else False,
                    }
            if "sampleName" in spec :
                sampleName = spec["sampleName"]
                assert sampleName in pads,str(pads)
                args["name"] += "_%s"%sampleName.replace(" ","_")
                args["padNumber"] = pads[sampleName]
                setTitles(histos, spec) #to allow for overwriting global title
            ratios = []
            if self.plotRatios : 
                ratios = self.plotRatio(histos,1)
                ratio = ratios[-1]
                self.canvas.cd(2)
                if issubclass(type(histos[0]),r.TGraph): 
                    ratio.Draw("AP")
                else: ratio.Draw()
            fileName = "%s_%s.eps"%(self.pdfFileName.replace(".pdf",""),args['name'])
            pad = self.canvas.cd(0)
            pad.Print(fileName)
            message = "The output file \"%s\" has been written."%fileName
            if args['alsoC'] :
                pad.Print(fileName.replace(".eps",".C"))
                print message.replace(".eps",".C")
            
            if not args['tight'] : #make pdf
                os.system("epstopdf "+fileName)
                os.system("rm       "+fileName)
            else : #make pdf with tight bounding box
                epsiFile = fileName.replace(".eps",".epsi")
                os.system("ps2epsi "+fileName+" "+epsiFile)
                os.system("epstopdf "+epsiFile)
                os.system("rm       "+epsiFile)

            print message.replace(".eps",".pdf")
        print utils.hyphens

    def printCalculablesDetailed(self, blocks) :
        text = r.TText()
        text.SetNDC()
        text.SetTextFont(102)
        text.SetTextSize(0.35*text.GetTextSize())

        maxLensB = [max(len(b) for a,b,c in block) for block in blocks]
        stringBlocks = [["%s%s  %s"%(a,b.ljust(maxLenB),c) for a,b,c in block] for block,maxLenB in zip(blocks,maxLensB)]
        for iLine,line in enumerate(sum(stringBlocks,[])) :
            y=0.98 - 0.35*(iLine+0.5)/self.nLinesMax
            text.DrawTextNDC(0,y, line)
        return text
            
    def printCalculables(self, selectImperfect) :
        text = r.TText()
        text.SetNDC()
        text.SetTextFont(102)
        text.SetTextSize(0.45*text.GetTextSize())

        allCalcs = sum([s.keys() for s in self.someOrganizer.calculables], [])
        genuine = ((name,more,"") for name,more,cat in sorted(set(allCalcs)) if more and cat is "calc")

        def third(c) : return c[2]
        groups = dict((cat,[name for name,more,_ in group]) for cat,group in itertools.groupby(sorted(allCalcs, key=third) , key=third))
        cats = groups.keys()
        fake = conf.fakeString()
        imperfect = ( ( name,  more.replace(fake,""), '  '.join("%4d"%groups[key].count(name) for key in cats))
                      for name,more,cat in set(allCalcs)
                      if cat is 'fake' or cat is "calc" and not ("leaf" in groups and (bool(groups["leaf"].count(name))^bool(groups["calc"].count(name)))) )

        calcs = (([("Calculables",'(imperfect)','  '.join(cats)), ('','','')] + max( list(imperfect), [('','NONE','')])) if selectImperfect else \
                 ([("Calculables",'',''),                         ('','','')] + max( list(genuine), [('','NONE','')])) )

        maxName,maxMore = map(max, zip(*((len(name),len(more)) for name,more,cat in calcs)))
        [text.DrawTextNDC(0.02, 0.98 - 0.4*(iLine+0.5)/self.nLinesMax, line)
         for iLine,line in enumerate("%s   %s   %s"%(name.rjust(maxName+2), more.ljust(maxMore+2), cat)
                                     for name,more,cat in calcs) ]
        return text
        
    def printTimeStamp(self) :
        text=r.TText()
        text.SetNDC()
        dateString="file created at ";
        tdt=r.TDatime()
        text.DrawText(0.1,0.1,dateString+tdt.AsString())
        return text

    def printNEventsIn(self) :
        text = r.TText()
        text.SetNDC()
        text.SetTextFont(102)
        text.SetTextSize(0.38*text.GetTextSize())
        defSize = text.GetTextSize()
        
        def getLumi(sample = None, iSource = None) :
            value = 0.0
            if sample!=None :
                if "lumi" in sample :
                    if iSource!=None :
                        value = sample["lumiOfSources"][iSource]
                    else :
                        value = sample["lumi"]                        
                elif "xs" in sample :
                    if iSource!=None :
                        value = sample["nEvents"][iSource]/sample["xsOfSources"][iSource]
                    else :
                        value = sample["nEvents"]/sample["xs"]
            return "%.1f"%value
            
        def loopOneType(mergedSamples = False) :
            nameEventsLumi = []
            for sample in self.someOrganizer.samples :
                if "sources" not in sample :
                    if mergedSamples : continue
                    nameEventsLumi.append((sample["name"],str(int(sample['nEvents'])),getLumi(sample)))
                else :
                    if not mergedSamples : continue
                    localNEL = []
                    useThese = True

                    for iSource in range(len(sample["sources"])) :
                        name = sample["sources"][iSource]
                        N    = sample["nEvents"][iSource]
                        if type(N) is list : useThese = False; break
                        localNEL.append((name,str(int(N)),getLumi(sample,iSource)))
                    if useThese : nameEventsLumi += localNEL

            nameEventsLumi.sort( key = lambda x: (x[0][:5], int(float(x[2])), -int(x[1]), x[0][5:] ))
            if not nameEventsLumi : return (None,None,None)
            name,events,lumi = zip(*nameEventsLumi)
            return ( ["sample",""]+list(name),
                     ["nEventsIn",""] + list(events),
                     ["  lumi (/pb)",""] + list(lumi) )

        def printOneType(x, sampleNames, nEventsIn, lumis) :
            if not sampleNames : return
            sLength = max([len(item) for item in sampleNames])
            nLength = max([len(item) for item in nEventsIn]  )
            lLength = max([len(item) for item in lumis]      )

            total = sLength + nLength + lLength + 15
            if total>self.nColumnsMax : text.SetTextSize(defSize*self.nColumnsMax/(total+0.0))
                
            for j,(name,events,lumi) in enumerate(zip(sampleNames,nEventsIn,lumis)) :
                y = 0.9 - 0.55*(j+0.5)/self.nLinesMax
                out = name.ljust(sLength) + events.rjust(nLength+3) + lumi.rjust(lLength+3)
                text.DrawTextNDC(x, y, out)

        printOneType( 0.02, *loopOneType(False) )
        printOneType( 0.02, *loopOneType(True)  )
        return text
    
    def flushPage(self) :
        self.printCanvas()
        self.canvas.Clear()

    def printCanvas(self, extra = "") :
        self.pageNumber += 1
        if self.pageNumber>1 :
            text = r.TText()
            text.SetNDC()
            text.SetTextFont(102)
            text.SetTextSize(0.45*text.GetTextSize())
            text.SetTextAlign(33)
            text.DrawText(0.95, 0.03, "page %3d"%self.pageNumber if self.pageNumbers else ".")
        self.canvas.Print(self.pdfFileName+extra,('pdf ' if extra=='[' else 'Title:')+self.pdfOptions)
        self.pdfOptions = ''

    def printSteps(self, steps, printAll=False) :
        if printAll and len(steps)>self.nLinesMax : self.printSteps(steps[:1-self.nLinesMax],printAll)
        self.canvas.cd(0)
        self.canvas.Clear()
        
        text = r.TText()
        text.SetNDC()
        text.SetTextFont(102)
        text.SetTextSize(0.40*text.GetTextSize())

        pageWidth = 120
        nSamples = len(self.someOrganizer.samples) + int(self.printRatios)
        colWidth = min(25, pageWidth/nSamples)
        space = 1

        nametitle = "{0}:  {1:<%d}   {2}" % (3+max([len(s.name) for s in steps]))
        for i,step in enumerate(steps[-self.nLinesMax:]) :
            absI = i + (0 if len(steps) <= self.nLinesMax else len(steps)-self.nLinesMax)

            text.SetTextColor(self.rowColors[absI%len(self.rowColors)])
            letter = string.ascii_letters[absI]
            x = 0.02
            y = 0.98 - 0.34*(i+0.5+(absI/self.rowCycle) - ((absI-i)/self.rowCycle) )/self.nLinesMax

            nums = []
            ratios = [None]*len(self.samplesForRatios)
            for k,sample in zip(step.yields,self.someOrganizer.samples) :
                special = "lumi" in sample and not self.showErrorsOnDataYields
                s = utils.roundString(*k, width=(colWidth-space), noSci = self.noSci or special, noErr = special) if k else "-    "
                if sample["name"] in self.samplesForRatios : ratios[self.samplesForRatios.index(sample["name"])] = k
                nums.append(s.rjust(colWidth))

            if self.printRatios and len(ratios)==2 :
                s = "-    "
                if ratios[0] and ratios[1] and ratios[0][0] and ratios[1][0] :
                    value = ratios[0][0]/float(ratios[1][0])
                    error = value*math.sqrt((ratios[0][1]/float(ratios[0][0]))**2 + (ratios[1][1]/float(ratios[1][0]))**2)
                    ratio = (value, error)
                    s = utils.roundString(*ratio, width=(colWidth-space))
                nums.append(s.rjust(colWidth))
                
            if step.name in ['master','label']: self.pdfOptions = step.title
            if step.name=='label' :
                text.SetTextColor(r.kBlack)
                font = text.GetTextFont()
                text.SetTextFont(62)
                label = "[  %s  ]"%step.title
                text.DrawTextNDC(0.01, y, label)
                text.DrawTextNDC(0.01, y-0.51, label )
                text.SetTextFont(font)
            else:
                text.DrawTextNDC(x, y-0.00, nametitle.format(letter, step.name, step.title ))
                text.DrawTextNDC(x, y-0.51, "%s: %s"%(letter, "".join(nums)))
                self.cutDict[letter] = (step.name, step.title)
                self.yieldDict[letter] = nums

            if absI > self.formerMaxAbsI :
                text.SetTextColor(r.kBlack)
                text.DrawTextNDC(0.008,y-0.00,'|')
                text.DrawTextNDC(0.008,y-0.51,'|')

        self.formerMaxAbsI = absI
        self.sampleList = [s["name"][:(colWidth-space)].rjust(colWidth) for s in self.someOrganizer.samples]
        if self.printRatios and len(self.samplesForRatios)==2 :
            self.sampleList += ("%s/%s"%self.sampleLabelsForRatios)[:(colWidth-space)].rjust(colWidth)
        text.SetTextColor(r.kBlack)
        text.DrawTextNDC(x, 0.5, "   "+"".join(self.sampleList))
        text.SetTextAlign(13)
        text.DrawTextNDC(0.05, 0.03, "events / %.3f pb^{-1}"% self.someOrganizer.lumi )
        self.flushPage()

    def getExtremes(self, dimension, histos, ignoreHistos) :
        globalMax = -1.0
        globalMin = 1.0e9

        for histo,ignore in zip(histos,ignoreHistos) :
            if ignore or (not histo) : continue
            if issubclass(type(histo),r.TGraph):
                globalMax=histo.GetMaximum()
                globalMin=histo.GetMinimum()
                globalMax=1.3
                globalMin=0.
                continue
            if dimension==1 :
                for iBinX in range(histo.GetNbinsX()+2) :
                    content = histo.GetBinContent(iBinX)
                    error   = histo.GetBinError(iBinX)
                    valueUp   = content + error
                    if valueUp>0.0 and valueUp>globalMax : globalMax = valueUp
                    if self.doLog and content>0 : globalMin = min(globalMin,content)
                    if not self.doLog : globalMin = min(globalMin,content-error)
            if dimension==2 :
                for iBinX in range(histo.GetNbinsX()+2) :
                    for iBinY in range(histo.GetNbinsY()+2) :
                        value = histo.GetBinContent(iBinX,iBinY)
                        if value!=0.0 :
                            if value<globalMin : globalMin = value
                            if value>globalMax : globalMax = value                            
        return globalMin,globalMax

    def setRanges(self, histos, globalMin, globalMax) :
        for histo in histos :
            if not histo : continue
            if self.doLog :
                histo.SetMinimum(0.5*globalMin) if self.pegMinimum==None else histo.SetMinimum(self.pegMinimum)
                histo.SetMaximum(2.0*globalMax)
            else :
                histo.SetMaximum(1.1*globalMax)
                histo.SetMinimum(1.1*globalMin if globalMin<0 else 0)

    def prepareCanvas(self,histos,dimension) :
        self.canvas.cd(0)
        self.canvas.Clear()
        if dimension==1 :
            if self.plotRatios :
                split = 0.25
                self.canvas.Divide(1,2)
                self.canvas.cd(1).SetPad(0.01,split+0.01,0.99,0.99)
                self.canvas.cd(2).SetPad(0.01,0.01,0.99,split)
                #self.canvas.cd(2).SetTopMargin(0.07)#default=0.05
                #self.canvas.cd(2).SetBottomMargin(0.45)
                self.canvas.cd(1)
            else :
                self.canvas.Divide(1,1)
                if self.anMode : self.canvas.UseCurrentStyle()
        else :
            mx=1
            my=1
            while mx*my<len(histos) :
                if mx==my : mx+=1
                else :      my+=1
            self.canvas.Divide(mx,my)

    def plotEachHisto(self, dimension, histos, opts) :
        stuffToKeep = []
        legend = r.TLegend(*opts["legendCoords"])
        stuffToKeep.append(legend)
        legendEntries = []
        if self.anMode :
            legend.SetFillStyle(0)
            legend.SetBorderSize(0)

        count = 0
        pads = {}
        for sample,histo,ignore in zip(self.someOrganizer.samples, histos, opts["ignoreHistos"]) :
            #if ignore or (not histo) or (not histo.GetEntries()) : continue
            if ignore or (not histo) : continue

            if "color" in sample :
                for item in ["Line", "Marker"] :
                    getattr(histo,"Set%sColor"%item)(sample["color"])
            for item in ["lineColor", "lineStyle", "lineWidth",
                         "markerStyle", "markerColor","markerSize", "fillStyle", "fillColor"] :
                if item in sample : getattr(histo, "Set"+item.capitalize()[0]+item[1:])(sample[item])

            sampleName = inDict(opts["newSampleNames"], sample["name"], sample["name"])
            legendEntries.append( (histo, sampleName, inDict(sample, "legendOpt", "lp")) )
            if dimension==1 :
                stuffToKeep += self.plot1D(histo, count,
                                           goptions = inDict(sample, "goptions", ""),
                                           double = inDict(sample, "double", ""))
            elif dimension==2 and self.omit2D : continue
            elif dimension==2 :
                legendEntries.append((histo, str(round(histo.GetCorrelationFactor(1,2),3))))
                self.plot2D(histo, count, sampleName, stuffToKeep)
                pads[sampleName] = 1+count
            else :
                print "Skipping histo",histo.GetName(),"with dimension",dimension
                continue
            count+=1
        if dimension==1 :
            if opts["reverseLegend"] : legendEntries.reverse()
            for e in legendEntries : legend.AddEntry(*e)
            legend.Draw()
        return count,stuffToKeep,pads

    def plotRatio(self,histos,dimension) :
        numLabel,denomLabel = self.sampleLabelsForRatios
        numSampleName,denomSampleNames = self.samplesForRatios
        if type(denomSampleNames)!=list: denomSampleNames = [denomSampleNames]

        ratios = []
        try:
            numHisto = histos[self.someOrganizer.indexOfSampleWithName(numSampleName)]
            denomHistos = map(lambda name: histos[self.someOrganizer.indexOfSampleWithName(name)], denomSampleNames)
        except TypeError:
            return ratios

        if not numHisto : return ratios

        same = ""
        for denomHisto in denomHistos :
            ratio = None
            #if numHisto and denomHisto and numHisto.GetEntries() and denomHisto.GetEntries() :
            if numHisto and denomHisto :
                ratio = utils.ratioHistogram(numHisto,denomHisto)
                ratio.SetMinimum(0.8)
                ratio.SetMaximum(1.2)
                ratio.GetYaxis().SetTitle(numLabel+"/"+denomLabel)
                self.canvas.cd(2)
                adjustPad(r.gPad, self.anMode)
                r.gPad.SetGridy()
                if issubclass(type(ratio),r.TH1) : ratio.SetStats(False)
                ratio.GetXaxis().SetLabelSize(0.0)
                ratio.GetXaxis().SetTickLength(3.5*ratio.GetXaxis().GetTickLength())
                ratio.GetYaxis().SetLabelSize(0.12)
                ratio.GetYaxis().SetNdivisions(505,True)
                ratio.GetXaxis().SetTitleOffset(0.2)
                ratio.GetYaxis().SetTitleSize(0.15)
                ratio.GetYaxis().SetTitleOffset([0.2,0.43][self.anMode])
                if len(denomHistos)==1: 
                    ratio.SetMarkerStyle(numHisto.GetMarkerStyle())
                    ratio.SetMarkerSize(numHisto.GetMarkerSize())
                color = numHisto.GetLineColor() if len(denomHistos)==1 else denomHisto.GetLineColor()
                ratio.SetLineColor(color)
                ratio.SetMarkerColor(color)
                if issubclass(type(ratio),r.TGraph) : ratio.Draw("AP")
                else : ratio.Draw(same)
                same = "same"
            else :
                self.canvas.cd(2)
            ratios.append(ratio)
        return ratios

    def onePlotFunction(self, histos, individual = {}) :
        dimension = dimensionOfHisto(histos)
        self.prepareCanvas(histos, dimension)

        options = {"newSampleNames": {},
                   "legendCoords": (0.86, 0.60, 1.00, 0.10),
                   "reverseLegend": False,
                   "ignoreHistos": [],
                   }
        options.update(individual)
        if not options["ignoreHistos"] : options["ignoreHistos"] = [False]*len(histos)
        
        if self.shiftUnderOverFlows : shiftUnderAndOverflows(dimension, histos, self.dontShiftList)
        self.setRanges(histos, *self.getExtremes(dimension, histos, options["ignoreHistos"]))

        count,stuffToKeep,pads = self.plotEachHisto(dimension, histos, options)
        if self.plotRatios and dimension==1 :
            ratios = self.plotRatio(histos,dimension)
        self.canvas.cd(0)
        if count>0 and not individual :
            self.printCanvas()
        if individual :
            return stuffToKeep,pads
        if dimension==2 and self.dependence2D :
            depHistos = tuple(utils.dependence(h) for h in histos)
            self.prepareCanvas(depHistos, dimension)
            count,stuffToKeep,pads = self.plotEachHisto(dimension, depHistos, options)
            self.canvas.cd(0)
            if count>0 : self.printCanvas()

    def plot1D(self, histo, count, goptions = "", double = False) :
        keep = []
        adjustPad(r.gPad, self.anMode)

        if count==0 :
            if not self.anMode : histo.GetYaxis().SetTitleOffset(1.25)
            if self.doLog : r.gPad.SetLogy()
            if issubclass(type(histo),r.TGraph) : goptions+="A"
        else :
            goptions += "same"

        if issubclass(type(histo),r.TH1) : histo.SetStats(self.showStatBox)
        if issubclass(type(histo),r.TGraph) : goptions+="P"
        histo.Draw(goptions)

        if double :
            histo2 = histo.Clone(histo.GetName()+"_cloneDouble")
            histo2.SetFillStyle(0)
            histo2.Draw("histsame")
            keep.append(histo2)

        r.gStyle.SetOptFit(0)
        if self.doMetFit and "met" in histo.GetName() :
            r.gStyle.SetOptFit(1111)
            func=metFit(histo)
            keep.append(func)

            r.gPad.Update()
            tps=histo.FindObject("stats")
            keep.append(tps)
            tps.SetLineColor(histo.GetLineColor())
            tps.SetTextColor(histo.GetLineColor())
            if iHisto==0 :
                tps.SetX1NDC(0.75)
                tps.SetX2NDC(0.95)
                tps.SetY1NDC(0.75)
                tps.SetY2NDC(0.95)
            else :
                tps.SetX1NDC(0.75)
                tps.SetX2NDC(0.95)
                tps.SetY1NDC(0.50)
                tps.SetY2NDC(0.70)

        #move stat box
        r.gPad.Update()
        tps=histo.FindObject("stats")
        keep.append(tps)
        if tps :
            tps.SetTextColor(histo.GetLineColor())
            tps.SetX1NDC(0.86)
            tps.SetX2NDC(1.00)
            tps.SetY1NDC(0.70)
            tps.SetY2NDC(1.00)

        if histo.GetName()=='ksLxy':
			layers=[4.3,7.2,10.95] # pixel
			layers+=[22.5,31.5,40.5,49.5,58.5] # inner strip barrel
			l=[r.TLine() for layer in layers]
			[line.SetLineWidth(4) for line in l]
			for i,layer in enumerate(layers):
				val=histo.GetBinContent(histo.FindFixBin(layer))
				l[i].DrawLine(layer, val*0.5,layer,val*2.)

        return keep

    def lineDraw(self, name, offset, slope, histo, color = r.kBlack, suffix = "") :
        if name not in histo.GetName() : return None
        axis = histo.GetXaxis()
        func = r.TF1(name+suffix,"(%g)+(%g)*x"%(offset,slope),axis.GetXmin(),axis.GetXmax())
        func.SetLineWidth(1)
        func.SetLineColor(color)
        func.Draw("same")
        return func
        
    def plot2D(self,histo,count,sampleName,stuffToKeep) :
    	yx=r.TF1("yx","x",histo.GetXaxis().GetXmin(),histo.GetXaxis().GetXmax())
    	yx.SetLineColor(r.kBlack)
    	yx.SetLineWidth(1)
    	yx.SetNpx(300)
    	
    	self.canvas.cd(count+1)
        adjustPad(r.gPad, pushLeft = self.pushLeft )
        
    	histo.GetYaxis().SetTitleOffset(1.2)
    	oldTitle=histo.GetTitle()
    	newTitle=sampleName if oldTitle=="" else sampleName+"_"+oldTitle
    	histo.SetTitle(newTitle)
    	histo.SetStats(False)
    	#histo.SetStats(self.showStatBox)
    	histo.GetZaxis().SetTitleOffset(1.3)
        if self.doLog : r.gPad.SetLogz()

        #plot-specific stuff
        if 'dependence' in histo.GetName(): r.gPad.SetLogz(0)

        # ABCD count histograms
        if 'counts' in histo.GetName():
            histo.SetMarkerSize(3)
            if 'H' in sampleName: 
                histo.DrawNormalized('TEXTE')
            else:
                histo.Draw('TEXTE')
        else:
	        histo.Draw("colz" if self.doColzFor2D else "")


        # corrTable
        if self.doCorrTable:
            if len(histo.GetName().split('_')) > 2 and "Data" in sampleName and "dependence" not in histo.GetName():
			    self.corrTableData.append(sorted(histo.GetName().split('_')[:2])
                                      +[str(int(100*histo.GetCorrelationFactor(1,2)))])
            if len(histo.GetName().split('_')) > 2 and "QCD" in sampleName and "dependence" not in histo.GetName():
			    self.corrTableMC.append(sorted(histo.GetName().split('_')[:2])
                                      +[str(int(100*histo.GetCorrelationFactor(1,2)))])

        if "deltaHtOverHt_vs_mHtOverHt" in histo.GetName() \
               or "deltaHtOverHt_vs_metOverHt" in histo.GetName() :
            histo.GetYaxis().SetRangeUser(0.0,0.7)
            funcs=[
                makeAlphaTFunc(0.55),
                makeAlphaTFunc(0.50),
                makeAlphaTFunc(0.45)
                ]
            for func in funcs : func.Draw("same")
            stuffToKeep.extend(funcs)
        elif self.drawYx :
            yx.Draw("same")
            stuffToKeep.append(yx)

        stuffToKeep.append( self.lineDraw(name = "alphaTMet_vs_alphaT",      offset = 0.0,   slope = 1.0,   histo = histo) )
        stuffToKeep.append( self.lineDraw(name = "alphaTMet_zoomvs_alphaT",  offset = 0.0,   slope = 1.0,   histo = histo) )
        stuffToKeep.append( self.lineDraw(name = "mhtVsPhotonPt",            offset = 0.0,   slope = 1.0,   histo = histo) )

        #loose
        stuffToKeep.append( self.lineDraw(name = "jurassicEcalIsolation",    suffix = "loose", offset = 4.2,   slope = 0.006,  histo = histo) )
        stuffToKeep.append( self.lineDraw(name = "towerBasedHcalIsolation",  suffix = "loose", offset = 2.2,   slope = 0.0025, histo = histo) )
        stuffToKeep.append( self.lineDraw(name = "hadronicOverEm",           suffix = "loose", offset = 0.05,  slope = 0.0,    histo = histo) )
        stuffToKeep.append( self.lineDraw(name = "hollowConeTrackIsolation", suffix = "loose", offset = 3.5,   slope = 0.001,  histo = histo) )

        #tight
        stuffToKeep.append( self.lineDraw(name = "jurassicEcalIsolation",    suffix = "tight", offset = 4.2,   slope = 0.006,  histo = histo, color = r.kBlue) )
        stuffToKeep.append( self.lineDraw(name = "towerBasedHcalIsolation",  suffix = "tight", offset = 2.2,   slope = 0.0025, histo = histo, color = r.kBlue) )
        stuffToKeep.append( self.lineDraw(name = "hadronicOverEm",           suffix = "tight", offset = 0.05,  slope = 0.0,    histo = histo, color = r.kBlue) )
        stuffToKeep.append( self.lineDraw(name = "hollowConeTrackIsolation", suffix = "tight", offset = 2.0,   slope = 0.001,  histo = histo, color = r.kBlue) )
        stuffToKeep.append( self.lineDraw(name = "sigmaIetaIetaBarrel",      suffix = "tight", offset = 0.013, slope = 0.0,    histo = histo, color = r.kBlue) )
        stuffToKeep.append( self.lineDraw(name = "sigmaIetaIetaEndcap",      suffix = "tight", offset = 0.030, slope = 0.0,    histo = histo, color = r.kBlue) )

    def printCorrTable(self):
        self.corrTableData=sorted(self.corrTableData)
        self.corrTableMC=sorted(self.corrTableMC)
        listOfVars = []
        for item in self.corrTableMC: 
            if item[0] not in listOfVars:listOfVars.append(item[0])
            if item[1] not in listOfVars:listOfVars.append(item[1])
        import string
        print " "*20+"".join(string.ljust(a[:15],20) for a in listOfVars)
        for i in range(len(listOfVars)):
            buff=string.ljust(listOfVars[i][:15],20)+' '*20*(i+1)
            if len(self.corrTableData)>0 and len(self.corrTableMC)>0:
                for item,itemCmp in zip(self.corrTableData,self.corrTableMC):
                    if listOfVars[i]==item[0] :
                        buff+=string.ljust(item[2]+' ('+itemCmp[2]+') %',20)
                print buff
            elif len(self.corrTableData)>0:
                for item in self.corrTableData:
                    if listOfVars[i]==item[0] :
                        buff+=string.ljust(item[2]+' %',20)
                print buff
            elif len(self.corrTableMC)>0:
                for item in self.corrTableMC:
                    if listOfVars[i]==item[0] :
                        buff+=string.ljust(item[2]+' %',20)
                print buff
##############################
