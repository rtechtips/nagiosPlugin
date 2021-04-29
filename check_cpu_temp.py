#!/usr/bin/python

# check_cpu_temp
#
# Copyright (c) <2021>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# Author: Ritesh Kumar Srivastava
# Contributor: Romeo Tudureanu
# 2021-02-23 Version 1
#

# Use pip version 19 or 20 for rhel 7.x . above pip will not work to install requierments
# The script should run, locally, on a linux machine running with lm_sensors and
# pysensors installed

# Requirements:
# - python 2.7.x installed
# - lm_sensors package
# - python pysensors module


from __future__ import unicode_literals
import sys
import platform
import argparse
import os

# detect linux distributin
distro = platform.dist()
distro= distro[0]

REDHAT_BASED = ['centos','redhat','fedora']
DEBIAN_BASED = ['debian','ubuntu']

# take care of pysensors different output CentOS vs. Debian
if distro in REDHAT_BASED:
    pos = 1
    sp = "lm_sensors"
elif distro in DEBIAN_BASED:
    pos = 0
    sp = "lm-sensors"
else:
    raise Exception('Unknown distro')

# check if sensors package is installed
if not os.path.exists('/usr/bin/sensors'):
    print('Sensors binary not found. Please install {} package!'.format(sp))
    sys.exit()

# check if pysensors python module is installed
try:
    import sensors
    sensors.init()
except ImportError, e:
    print('Module pysensors not found. Please install it!')
    sys.exit()

# deal with python 2.x unicode error for degree sign when using check_nrpe
reload(sys)
sys.setdefaultencoding('utf8')

# define nagios status codes
OK = 0
WARN = 1
CRIT = 2
UNK = 3

# degree sign
ds = "\u00b0"

# some default variables
averages = []
high_temp = 0
crit_temp = 0
status = OK

# use arguments from warning and critical values
parser = argparse.ArgumentParser(description='Nagios plugin to check CPU(s) temperature(s)')
parser.add_argument("-w", "--warn", dest="warn", help="Check temperature against a custom HIGH value", default='', required=False)
parser.add_argument("-c", "--crit", dest="crit", help="Check temperature against a custom CRIT value", default='', required=False)
args = parser.parse_args()

# if no arguments provided use the default HIGH/CRIT values
if args.warn:
    high_temp = int(args.warn)
if args.crit:
    crit_temp = int(args.crit)

# let's do it
try:
    chips = list(sensors.iter_detected_chips())
    for chip in chips:
        if chip.prefix == 'coretemp':
            features = list(chip)
            temp_sum = 0

            for feature in features[pos:]:
                subfeatures = list(feature)
                current_temp = subfeatures[0].get_value()
                temp_sum += current_temp

            if not high_temp:
		        high_temp = subfeatures[1].get_value()
            if not crit_temp:
                crit_temp = subfeatures[2].get_value()

            averages.append(temp_sum/len(features[1:]))

    # assign status codes
    for average in averages:
        if average >= high_temp:
            status = WARN
        if average >= crit_temp:
            status = CRIT

    # format cpu averages
    averages=map(int,averages)
    averages=map(lambda s: unicode(s) + ds + "C",averages)
    output="CPU(s) temperature(s): {}; high={}; crit={}".format(" ".join(averages),high_temp,crit_temp)

    # print statuses + output
    if status == OK:
        print("OK - " + output)
        sys.exit(0)
    elif status == WARN:
        print("WARNING - " + output)
        sys.exit(0)
    elif status == CRIT:
        print("CRITICAL - " + output)
        sys.exit(0)

except Exception as e:
    print e
    status = UNK
    raise

finally:
    sensors.cleanup()
