from bisect import bisect
#####################################
class analysisStep(object) :
    """generic analysis step"""

    integerWidth = 10
    docWidth = 30
    moreWidth = 40
    moreName = ""
    moreName2 = ""

    ignoreInAccounting = False
    disabled = False
    quietMode = False
    needToConsiderPtHatThresholds = False
    
    def go(self,eventVars) :
        if self.disabled :
            return True
        
        if not self.isSelector :
            self.uponAcceptance(eventVars)
            return True

        passed = bool(self.select(eventVars))
        self.increment(passed)
        return passed
    def increment(self, passed, w = 1) : self.book().fill(passed, "counts", 2, 0, 2, w = w)
    def setup(self, inputChain, fileDirectory, name, outputDir) : return
    def endFunc(self, otherChainDict) : return
    def mergeFunc(self, productList, someLooper) : return
    def name(self) : return self.__class__.__name__
    def name1(self) : return self.name().ljust(self.docWidth)+self.moreName.ljust(self.moreWidth)
    def name2(self) : return "" if self.moreName2=="" else "\n"+"".ljust(self.docWidth)+self.moreName2.ljust(self.moreWidth)
    def varsToPickle(self) : return []
    def requiresNoSetBranchAddress(self) : return False
    def disable(self) : self.disabled = True
    def makeQuiet(self) : self.quietMode = True
    def nFromHisto(self, bin) : return self.book()["counts"].GetBinContent(bin) if "counts" in self.book() and self.book()["counts"] else 0.0
    def nFail(self) :  return int(self.nFromHisto(1))
    def nPass(self) :  return int(self.nFromHisto(2))
    def ignore(self) : self.ignoreInAccounting = True
        
    def printStatistics(self) :
        passString="-" if self.disabled else str(self.nPass())
        failString="-" if self.disabled else str(self.nFail())

        statString = "" if not hasattr(self,"select") else \
                     "  %s %s" % ( passString.rjust(self.integerWidth), ("("+failString+")").rjust(self.integerWidth+2) )
        print "%s%s%s" % (self.name1(),self.name2(),statString)

    def book(self, eventVars = None) :
        return self.books[None]
#####################################
