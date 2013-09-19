import ROOT as r
#####################################
def cmsStamp(lumi = None, cms = True, preliminary = True, simulation = False, coords = (0.75, 0.5)) :
    latex = r.TLatex()
    latex.SetNDC()
    size = 0.035
    latex.SetTextSize(size)
    
    #latex.SetTextAlign(11) #align left, bottom
    #latex.DrawLatex(0.1, 0.91, "CMS Preliminary")

    x,y = coords
    slope = 1.1*size
    latex.SetTextAlign(21) #align center, bottom

    cmsstr = "CMS%s"%(" Simulation"if simulation else " Preliminary" if preliminary else "")
    sqrtsstr = "#sqrt{s} = 8 TeV"
    factor = 0.0
    if lumi is None or simulation: latex.DrawLatex(x,y-factor*slope, cmsstr+", "+sqrtsstr)
    else:
        lumistr = "#int L dt = %.1f fb^{-1}"%(lumi/1000.) if lumi>1000 else "#int L dt = %.0f pb^{-1}"%lumi
        if (not preliminary and not simulation): 
           latex.DrawLatex(x,y-factor*slope, cmsstr+", "+sqrtsstr+", "+lumistr);# factor+=1.8
           #latex.DrawLatex(x,y-factor*slope,lumistr)
        else:
           latex.DrawLatex(x,y-factor*slope, cmsstr); factor+=1.6
           latex.DrawLatex(x,y-factor*slope, lumistr+", "+sqrtsstr)

#####################################
def cmsswFuncData(fileName = None, par = None) :
    if not fileName or not par: return None
    lines = open(fileName).readlines(10000)
    lines = lines[lines.index("[%s]\n"%par):]
    lines = lines[:1+[L[0] for L in lines[1:]].index('[')]

    ROOT_funcString = lines[1].split()[4]
    funcs = []
    for line in lines[2:] :
        pars = [float(s) for s in line.split()]
        binLo,binHi = tuple(pars[:2])
        domainLo,domainHi = tuple(pars[3:5])
        funcPars = pars[5:]
        f = r.TF1("%s_%s_%f_%f"%(fileName,par,binLo,binHi), ROOT_funcString, domainLo, domainHi)
        for i,p in enumerate(funcPars) : f.SetParameter(i,p)
        f.SetNpx(500)
        funcs.append( (binLo,binHi,f) )
    funcs.sort()
    return funcs
#####################################
