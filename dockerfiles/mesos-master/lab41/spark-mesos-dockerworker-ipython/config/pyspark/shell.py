#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""
An interactive shell.

This file is designed to be launched as a PYTHONSTARTUP script.
"""

import sys
if sys.version_info[0] != 2:
    print("Error: Default Python used is Python%s" % sys.version_info.major)
    print("\tSet env variable PYSPARK_PYTHON to Python2 binary and re-run it.")
    sys.exit(1)


import atexit
import os
import platform

import py4j

import pyspark
from pyspark.conf import SparkConf
from pyspark.context import SparkContext
from pyspark.sql import SQLContext, HiveContext
from pyspark.storagelevel import StorageLevel

import json
import os
import urllib2
import IPython, jupyter_core
import glob
from IPython.lib import kernel

# find an available port for SparkUI
def ui_get_available_port():
  import socket;

  # default UI host/port
  host = "127.0.0.1"
  port = 4040

  # check
  check = notfound = 0

  # find the first available unoccupied port
  while (check==notfound):

      # check if available
      sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      check = sock.connect_ex((host, port))

      # try again if port unavailable
      if check == notfound:
         port += 1

  # return the first available port
  return port


# this is the deprecated equivalent of ADD_JARS
add_files = None
if os.environ.get("ADD_FILES") is not None:
    add_files = os.environ.get("ADD_FILES").split(',')

if os.environ.get("SPARK_EXECUTOR_URI"):
    SparkContext.setSystemProperty("spark.executor.uri", os.environ["SPARK_EXECUTOR_URI"])

# setup mesos-based connection
conf = (SparkConf()
         .setMaster(os.environ["SPARK_MASTER"]))

# set the UI port
conf.set("spark.ui.port", ui_get_available_port())

# configure docker containers as executors
conf.setSparkHome(os.environ.get("SPARK_HOME"))
conf.set("spark.mesos.executor.docker.image", "lab41/spark-mesos-dockerworker-ipython")
conf.set("spark.mesos.executor.home", "/usr/local/spark-{}-bin-hadoop{}".format(os.environ.get('SPARK_VERSION', '1.5.2'), os.environ.get('HADOOP_VERSION', '2.4')))
conf.set("spark.executorEnv.MESOS_NATIVE_LIBRARY", "/usr/local/lib/libmesos.so")
conf.set("spark.network.timeout", "100")

# locate current notebook server
api = 'http://127.0.0.1:8888/'
with open(glob.glob("{}/nbserver-*.json".format(jupyter_core.paths.jupyter_runtime_dir()))[0]) as infile:
    cfg = json.loads(infile.read())
    if cfg['url']:
        api = cfg['url']

# search all sessions in notebook server
sessions = json.load(urllib2.urlopen('{}api/sessions'.format(api)))

# locate current notebook kernel
connection_file_path = kernel.get_connection_file()
connection_file = os.path.basename(connection_file_path)
kernel_id = connection_file.split('-', 1)[1].split('.')[0]

# get name of notebook matching current notebook kernel
notebook_name = "pyspark"
for sess in sessions:
    if sess['kernel']['id'] == kernel_id:
        notebook_name =  os.path.basename(sess['notebook']['path'])
        break

# establish config-based context
sc = SparkContext(appName=notebook_name, pyFiles=add_files, conf=conf)
atexit.register(lambda: sc.stop())

try:
    # Try to access HiveConf, it will raise exception if Hive is not added
    sc._jvm.org.apache.hadoop.hive.conf.HiveConf()
    sqlCtx = sqlContext = HiveContext(sc)
except py4j.protocol.Py4JError:
    sqlCtx = sqlContext = SQLContext(sc)

print("""Welcome to
      ____              __
     / __/__  ___ _____/ /__
    _\ \/ _ \/ _ `/ __/  '_/
   /__ / .__/\_,_/_/ /_/\_\   version %s
      /_/
""" % sc.version)
print("Using Python version %s (%s, %s)" % (
    platform.python_version(),
    platform.python_build()[0],
    platform.python_build()[1]))
print("SparkContext available as sc, %s available as sqlContext." % sqlContext.__class__.__name__)

if add_files is not None:
    print("Warning: ADD_FILES environment variable is deprecated, use --py-files argument instead")
    print("Adding files: [%s]" % ", ".join(add_files))

# The ./bin/pyspark script stores the old PYTHONSTARTUP value in OLD_PYTHONSTARTUP,
# which allows us to execute the user's PYTHONSTARTUP file:
_pythonstartup = os.environ.get('OLD_PYTHONSTARTUP')
if _pythonstartup and os.path.isfile(_pythonstartup):
    execfile(_pythonstartup)
