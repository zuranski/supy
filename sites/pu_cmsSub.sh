#!/bin/bash

Q="hep"
WT="00:30:00"
qsub -q $Q -j oe -l walltime=$WT $1
