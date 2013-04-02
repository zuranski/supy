#!/bin/bash

#Q="hep"
WT="01:30:00"
#qsub -q $Q -j oe -l walltime=$WT $1
qsub -j oe -l walltime=$WT $1
