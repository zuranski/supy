#!/bin/bash

Q="hep"
WT="1:00:00"
qsub -q $Q -l walltime=$WT $1
