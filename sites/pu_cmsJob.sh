#!/bin/bash

export SCRAM_ARCH=slc5_amd64_gcc434
source /tigress-hsm/cmssoft/base5/cmsset_default.sh
cd /tigress-hsm/cmssoft/base5/slc5_amd64_gcc434/cms/cmssw/CMSSW_5_0_0/src && eval `scram runtime -sh` && cd - >& /dev/null
