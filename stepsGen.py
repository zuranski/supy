import ROOT as r
import utils,collections
from analysisStep import analysisStep
#####################################
pdgLookupExists=False
try:
    import pdgLookup
    pdgLookupExists=True
except ImportError:
    pass
#####################################
class ptHatFilter(analysisStep) :
    """ptHatFilter"""

    def __init__(self,maxPtHat) :
        self.maxPtHat=maxPtHat
        self.moreName = "(pthat<%.1f)"%maxPtHat

    def select (self,eventVars) :
        return eventVars["genpthat"]<self.maxPtHat
#####################################
class susyScanPointPrinter(analysisStep) :
    """susyScanPointPrinter"""

    def __init__(self) :
        self.leavesToPrint=["susyScanA0",
                            "susyScanCrossSection",
                            "susyScanM0",
                            "susyScanM12",
                            "susyScanMu",
                            "susyScanRun",
                            "susyScanTanBeta"
                            ]
        
    def uponAcceptance (self,eventVars) :
        outString=""
        for leafName in self.leavesToPrint :
            outString+=leafName.replace("susyScan","")+" = "+str(eventVars[leafName])+"\t"
        print outString
#####################################
class genJetPrinter(analysisStep) :
    """genJetPrinter"""

    def __init__(self,jetCollection,jetSuffix) :
        self.jetCollection=jetCollection
        self.jetSuffix=jetSuffix
        self.moreName="("
        self.moreName+=self.jetCollection
        self.moreName+="; "
        self.moreName+=self.jetSuffix
        self.moreName+=")"

    def uponAcceptance (self,eventVars) :
        p4Vector        =eventVars[self.jetCollection+'GenJetP4'     +self.jetSuffix]
        #emEnergy        =eventVars[self.jetCollection+'EmEnergy'        +self.jetSuffix]
        #hadEnergy       =eventVars[self.jetCollection+'HadEnergy'       +self.jetSuffix]
        #invisibleEnergy =eventVars[self.jetCollection+'InvisibleEnergy' +self.jetSuffix]
        #auxiliaryEnergy =eventVars[self.jetCollection+'AuxiliaryEnergy' +self.jetSuffix]

        print " jet   pT (GeV)    eta    phi    emF   hadF   invF   auxF"
        print "---------------------------------------------------------"
        for iJet in range(len(p4Vector)) :
            jet=p4Vector[iJet]
            totalEnergy=jet.energy()
            
            outString=" "
            #if (iJet in otherJetIndices) : outString="-"
            #if (iJet in cleanJetIndices) : outString="*"
            
            outString+=" %2d"   %iJet
            outString+="     %#6.1f"%jet.pt()
            outString+="   %#4.1f"%jet.eta()
            outString+="   %#4.1f"%jet.phi()
            #outString+="   %#4.2f"%(       emEnergy[iJet]/totalEnergy)
            #outString+="   %#4.2f"%(      hadEnergy[iJet]/totalEnergy)
            #outString+="   %#4.2f"%(invisibleEnergy[iJet]/totalEnergy)
            #outString+="   %#4.2f"%(auxiliaryEnergy[iJet]/totalEnergy)
            ##outString+="  %#4.2f"%( (emEnergy[iJet]+hadEnergy[iJet]+invisibleEnergy[iJet]+auxiliaryEnergy[iJet]) / totalEnergy )
            print outString
        print
#####################################
class genParticleCountHistogrammer(analysisStep) :
    """genParticleCountHistogrammer"""

    def __init__(self,tanBeta) :
        self.tanBetaThreshold=0.1
        self.tanBeta=tanBeta
        self.maxCountsPerCategory=2 #0 ... this number counted explicitly; otherwise overflows

        #Lo and Hi are both sampled in scan
        self.m0Lo=0.0
        self.m0Hi=4000.0
        self.m0StepSize=50.0
        self.nBinsM0=int(1+(m0Hi-m0Lo)/m0StepSize)

        self.m12Lo=100.0
        self.m12Hi=600.0
        self.m12StepSize=20.0
        self.nBinsM12=int(1+(m12Hi-m12Lo)/m12StepSize)

        self.histoBaseName="genParticleCounter"
        self.madeLabelHisto=False

    def makeCodeString(self,eventVars) :
        codeString=""
        for category,count in eventVars["GenParticleCategoryCounts"].iteritems() :
            if count>self.maxCountsPerCategory :
                count=self.maxCountsPerCategory+1
            codeString+=str(count)
        return codeString
    
    def uponAcceptance (self,eventVars) :
        if abs(eventVars["susyScanTanBeta"]-self.tanBeta)>self.tanBetaThreshold : return

        #make histo with labels
        if not self.madeLabelHisto :
            nCategories=len(eventVars["GenParticleCategoryCounts"])
            labelHistoName=self.histoBaseName+"CategoryLabels"
            self.book(eventVars).fill(-1.0,labelHistoName,
                                      nCategories,-0.5,nCategories-0.5,
                                      ";categories")
            for book in self.books.values() :
                if labelHistoName not in book : continue

                categories=eventVars["GenParticleCategoryCounts"].keys()
                for iCategory in range(len(categories)) :
                    book[labelHistoName].GetXaxis().SetBinLabel(iCategory+1,categories[iCategory])
                    book[labelHistoName].SetBinContent(iCategory+1,self.maxCountsPerCategory)
            self.madeLabelHisto=True

        #get scan point info
        xs=eventVars["susyScanCrossSection"]
        m0=eventVars["susyScanM0"]
        m12=eventVars["susyScanM12"]

        #fill histos
        codeString=self.makeCodeString(eventVars)
        self.book(eventVars).fill( (m0, m12), self.histoBaseName+codeString,
                                   (self.nBinsM0, self.nBinsM12),
                                   (self.m0Lo-self.m0StepSize/2.0, self.m12Lo-self.m12StepSize/2.0),
                                   (self.m0Hi+self.m0StepSize/2.0, self.m12Hi+self.m12StepSize/2.0),
                                   self.histoBaseName+codeString+";m_{0} (GeV);m_{1/2} (GeV)",
                                   )

        self.book(eventVars).fill( (m0, m12), self.histoBaseName+"nEvents",
                                   (self.nBinsM0, self.nBinsM12),
                                   (self.m0Lo-self.m0StepSize/2.0, self.m12Lo-self.m12StepSize/2.0),
                                   (self.m0Hi+self.m0StepSize/2.0, self.m12Hi+self.m12StepSize/2.0),
                                   self.histoBaseName+"nEvents;m_{0} (GeV);m_{1/2} (GeV)",
                                   )

        self.book(eventVars).fill( (m0, m12), self.histoBaseName+"XS",
                                   (self.nBinsM0, self.nBinsM12),
                                   (self.m0Lo-self.m0StepSize/2.0, self.m12Lo-self.m12StepSize/2.0),
                                   (self.m0Hi+self.m0StepSize/2.0, self.m12Hi+self.m12StepSize/2.0),
                                   xs,
                                   self.histoBaseName+"XS;m_{0} (GeV);m_{1/2} (GeV)",
                                   )
#####################################
class genParticlePrinter(analysisStep) :
    """genParticlePrinter"""

    def __init__(self,minPt=-1.0,minStatus=-1):
        self.oneP4=r.Math.LorentzVector(r.Math.PxPyPzE4D('double'))(0.0,0.0,0.0,0.0)
        self.sumP4=r.Math.LorentzVector(r.Math.PxPyPzE4D('double'))(0.0,0.0,0.0,0.0)
        self.zeroP4=r.Math.LorentzVector(r.Math.PxPyPzE4D('double'))(0.0,0.0,0.0,0.0)
        self.minPt=minPt
        self.minStatus=minStatus
        
    def uponAcceptance (self,eventVars) :

        self.sumP4.SetCoordinates(0.0,0.0,0.0,0.0)

        mothers=set(eventVars["genMother"])
        print "mothers: ",mothers
        print "---------------------------------------------------------------------------"
        print " i  st    mo         id            name        E        pt       eta    phi"
        print "---------------------------------------------------------------------------"

        size=len(eventVars["genP4"])
        for iGen in range(size) :

            p4=eventVars["genP4"][iGen]
            if p4.pt()<self.minPt :
                continue

            status=eventVars["genStatus"][iGen]
            if status<self.minStatus :
                continue

            pdgId=eventVars["genPdgId"][iGen]
            outString=""
            outString+="%#2d"%iGen
            outString+=" %#3d"%status
            outString+="  %#4d"%eventVars["genMother"][iGen]
            outString+=" %#10d"%pdgId
            if pdgLookupExists : outString+=" "+pdgLookup.pdgid_to_name(pdgId).rjust(15)
            else :                 outString+="".rjust(16)
            outString+="  %#7.1f"%p4.E()
            outString+="  %#8.1f"%p4.pt()
            outString+="  %#8.1f"%p4.eta()
            outString+="  %#5.1f"%p4.phi()
            #outString+="  %#5.1f"%p4.mass()
        
            if not (iGen in mothers) :
                outString+="   non-mo"
        #        self.sumP4+=self.oneP4
        #        #outString2="non-mo P4 sum".ljust(37)
        #        #outString2+="  %#7.1f"%self.sumP4.E()
        #        #outString2+="  %#8.1f"%self.sumP4.eta()
        #        #outString2+="  %#8.1f"%self.sumP4.pt()
        #        #outString2+="  %#5.1f"%self.sumP4.phi()
        #        #print outString2
        #
            print outString
        #
        #outString="non-mo P4 sum".ljust(37)
        #outString+="  %#7.1f"%self.sumP4.E()
        #outString+="  %#8.1f"%self.sumP4.eta()
        #outString+="  %#8.1f"%self.sumP4.pt()
        #outString+="  %#5.1f"%self.sumP4.phi()
        #print outString
        print
#####################################
class genMassHistogrammer(analysisStep) :
    """genMassHistogrammer"""

    def __init__(self,pdgId = 23):
        self.pdgId = pdgId
        self.histoName = "mass_pdgId==%d"%self.pdgId
        
    def uponAcceptance (self,eventVars) :
        size=len(eventVars["genP4"])
        for iGen in range(size) :
            p4=eventVars["genP4"].at(iGen)
            if eventVars["genPdgId"].at(iGen)!=self.pdgId : continue
            self.book(eventVars).fill(p4.mass(), self.histoName, 100, 0.0, 300.0, title = ";mass (GeV);events / bin")
#####################################
class genSHatHistogrammer(analysisStep) :
    """genSHatHistogrammer"""

    def uponAcceptance (self,eventVars) :
        p4 = eventVars["genP4"]
        size=p4.size()
        counts = [0,0]
        indices = [-1,-1]
        for iGen in range(size) :
            if not eventVars["genMotherStored"].at(iGen) : continue
            motherIndex = eventVars["genMother"].at(iGen)
            if motherIndex!=0 and motherIndex!=1 : continue
            counts[motherIndex] += 1
            indices[motherIndex] = iGen

        if counts[0]!=1 or counts[1]!=1 :
            print "bad counts",counts
            return
        
        rootSHat = ( p4.at(indices[0])+p4.at(indices[1]) ).mass()
        print indices,rootSHat
        self.book(eventVars).fill(rootSHat, "rootSHat", 100, 0.0, 300.0, title = ";#sqrt{#hat{s}} (GeV);events / bin")
#####################################
class genMotherHistogrammer(analysisStep) :
    """genMotherHistogrammer"""

    def __init__(self, indexLabel, specialPtThreshold) :
        self.indexLabel = indexLabel
        self.specialPtThreshold = specialPtThreshold
        self.keyAll       = "motherIdVsPt%sAll"%self.indexLabel
        self.keyAllHighPt = "motherIdVsPt%sAllHighPt"%self.indexLabel        
        self.motherDict = collections.defaultdict(int)
        self.binLabels = []
        self.binLabels.append("other")

        self.addParticle( 1, "d"); self.addParticle(-1, "#bar{d}")
        self.addParticle( 2, "u"); self.addParticle(-2, "#bar{u}")
        self.addParticle( 3, "s"); self.addParticle(-3, "#bar{s}");
        self.addParticle( 4, "c"); self.addParticle(-4, "#bar{c}");
        self.addParticle(21, "gluon")
        self.addParticle(22, "photon")
        self.addParticle(111,"#pi^{0}")
        self.addParticle(221,"#eta")
        self.addParticle(223,"#omega")
        self.addParticle(331,"#eta^{/}")
        
    def addParticle(self, id, name) :
        self.binLabels.append(name)
        self.motherDict[id] = self.binLabels[-1]

    def uponAcceptance (self,eventVars) :
        indices = eventVars[self.indexLabel]
        if len(indices)==0 : return

        p4s = eventVars["genP4"]
        nBinsY = len(self.binLabels)
        for iParticle in indices :
            p4 = p4s.at(iParticle)
            pt = p4.pt()
            motherId = eventVars["genMotherPdgId"][iParticle]
            if not self.motherDict[motherId] :
                #print motherId,"not found"
                yValue = 0
            else :
                yValue = self.binLabels.index(self.motherDict[motherId])
            self.book(eventVars).fill((pt,yValue), self.keyAll, (50,nBinsY), (0.0,-0.5), (500.0, nBinsY-0.5), title = ";GEN photon p_{T} (GeV);mother;photons / bin")
            if pt>self.specialPtThreshold :
                self.book(eventVars).fill(yValue, self.keyAllHighPt,
                                          nBinsY, -0.5, nBinsY-0.5,
                                          title = ";mother [when GEN photon p_{T}> %.1f (GeV)];photons / bin"%self.specialPtThreshold
                                          )
                if motherId==2 :
                    motherIndex = eventVars["genMother"][iParticle]
                    motherP4 = eventVars["genP4"][motherIndex]
                    deltaRPhotonMother = r.Math.VectorUtil.DeltaR(p4,motherP4)
                    deltaRPhotonOther  = r.Math.VectorUtil.DeltaR(p4,motherP4-p4)

                    self.book(eventVars).fill(motherP4.mass(), "mothersMass",
                                              20, -0.1, 0.4,
                                              title = ";mother's mass (GeV) [when GEN photon p_{T}> %.1f (GeV) and mother is u quark];photons / bin"%self.specialPtThreshold
                                              )
                    self.book(eventVars).fill(deltaRPhotonMother, "deltaRPhotonMother",
                                              20, 0.0, 1.5,
                                              title = ";#DeltaR(photon,mother) [when GEN photon p_{T}> %.1f (GeV) and mother is u quark];photons / bin"%self.specialPtThreshold
                                              )
                    self.book(eventVars).fill(deltaRPhotonOther, "deltaRPhotonOther",
                                              20, 0.0, 1.5,
                                              title = ";#DeltaR(photon,mother-photon) [when GEN photon p_{T}> %.1f (GeV) and mother is u quark];photons / bin"%self.specialPtThreshold
                                              )
                

    def endFunc(self,chain,otherChainDict,nEvents,xs) :
        for book in self.books.values() :
            if self.keyAll in book :
                for iParticle in range(len(self.binLabels)) :
                    book[self.keyAll].GetYaxis().SetBinLabel(iParticle+1,self.binLabels[iParticle])
            if self.keyAllHighPt in book :
                for iParticle in range(len(self.binLabels)) :
                    book[self.keyAllHighPt].GetXaxis().SetBinLabel(iParticle+1,self.binLabels[iParticle])
#####################################
