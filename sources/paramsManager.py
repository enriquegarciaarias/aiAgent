"""
@Purpose: Handles project-wide parameters
@Usage: Functions called by the main process
"""
from sources.common.common import logger, processControl, writeLog
from sources.common.utils import configLoader, dbTimestamp, preparaDirectorio

import argparse
import json
import os
import sys
import shutil
import socket
import warnings


# Constants for parameter files
JSON_PARMS = "deepMountainParms.json"

def manageArgs():
    """
    @Desc: Parse command-line arguments to configure the process.
    @Result: Returns parsed arguments as a Namespace object.
    """
    parser = argparse.ArgumentParser(description="Main process for Corpus handling.")
    parser.add_argument('--debug', type=str, help='Debug level: 0 Error, 1 Debug, 2 Info', default="DEBUG")
    parser.add_argument('--proc', type=str, help="Process type: Check, CORPUS, MODEL, APPLY, SENTENCE, INFERENCE, FEATURES", default="FEATURES")
    parser.add_argument('--model', type=str, help="architecture: bilstm, bigru, cnn, multicnn, transpmean", default="transpmean")
    parser.add_argument('--corpus', type=str, help="Name of corpus", default="DM")
    parser.add_argument('--prefix', type=str, help="Prefix of processes", default="_MPNet_transpmean_DM")
    parser.add_argument('--embedd', type=str, help="Embedding of processes", default="MPNet")
    return parser.parse_args()


def manageEnv():
    """
    @Desc: Defines environment paths and variables.
    @Result: Returns a dictionary containing environment paths.
    """
    base_path = os.path.realpath(os.getcwd())
    config = configLoader()
    storageProcesses = config.getStorageProcesses()

    env_data = {}
    for key in storageProcesses:
        env_data[key] = os.path.join(base_path, storageProcesses[key])

    env_data["timestamp"] = dbTimestamp()
    env_data["realPath"] = base_path
    env_data["uid"] = config.get_uid()
    env_data["hostname"] = socket.gethostname()
    env_data["systemName"] = socket.getfqdn()
    env_data["environment"] = config.get_environment()
    return env_data


def manageDefaults():
    config = configLoader()
    defaults = config.getDefaults()
    return defaults


def validateDataParams():
    """
    @Desc: Validates and adjusts parameter configurations before training.
    """
    return True

def setEnvironment():
    return True

def getConfigs():
    """
    @Desc: Load environment settings, arguments, and hyperparameters.
    @Result: Stores configurations in processControl variables.
    """
    try:
        processControl.datasetVars = {}
        processControl.args = manageArgs()
        processControl.env = manageEnv()
        processControl.defaults = manageDefaults()
        setEnvironment()
        validateDataParams()

    except Exception as e:
        raise Exception(f"Error validating execution parameters: {e}")
