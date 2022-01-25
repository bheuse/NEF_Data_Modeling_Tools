import json
from jsonschema import validate
import yaml
import os
import glob
import logging
import datetime
from termcolor import colored
import copy
import unittest
from expiringdict import ExpiringDict
import requests
from requests_file import FileAdapter


"""
Bernard, the link on SBA configuration distribution 
https://confluence.openet.com/display/5G/Configuration+Update+Over+Rsync+-+HLD
"""

timestamp = datetime.datetime.now().strftime("%y%m%d-%H%M%S")
logFile   = "."+os.sep+"db_schema_to_openapi.log"
logging.basicConfig(filename=logFile, filemode='w', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)

###
### Print
###


class Term:

    VERBOSE = False

    @staticmethod
    def setVerbose(verbose = True):
        Term.VERBOSE = verbose

    @staticmethod
    def print_green(text):
        print(colored(text, "green"))
        logging.debug(text)

    @staticmethod
    def print_red(text):
        print(colored(text, "red"))
        logging.debug(text)

    @staticmethod
    def print_verbose(text):
        if (Term.VERBOSE):
            print(colored(text, "magenta"))
        logging.debug(text)

    @staticmethod
    def print_error(text):
        print(colored(text, "cyan"))
        logging.error(text)

    @staticmethod
    def print_yellow(text):
        print(colored(text, "yellow"))
        logging.debug(text)

    @staticmethod
    def print_grey(text):
        print(colored(text, "grey"))
        logging.debug(text)

    @staticmethod
    def print_blue(text):
        print(colored(text, "blue"))
        logging.debug(text)

    # Flattening Nested Dictionary
    # {'b:w': 3, 'b:u': 1, 'b:v:y': 2, 'b:v:x': 1, 'b:v:z': 3, 'a:r': 1, 'a:s': 2, 'a:t': 3}
    @staticmethod
    def flatten(myDict, sep: str = ":"):
        newDict = {}
        for key, value in myDict.items():
            if type(value) == dict:
                fDict = {sep.join([key, _key]): _value for _key, _value in Term.flatten(value, sep).items()}
                newDict.update(fDict)
            elif type(value) == list:
                i=0
                for el in value :
                    fDict = {sep.join([key, str(i), _key]): _value for _key, _value in Term.flatten(el, sep).items()}
                    newDict.update(fDict)
                    i=i+1
            else:
                newDict[key] = value
        return newDict

    @staticmethod
    def print_flat(tree_dict):
        flat_dict = Term.flatten(tree_dict, "/")
        for key in flat_dict.keys() :
            print(colored(key, "blue") + " : " + colored(flat_dict[key], "yellow"))

###
### Directories and Files
###


class FileSystem:

    @staticmethod
    def saveFileContent(content, file_name: str):
        with open(file_name, "w") as file:
            content = file.write(content)
            file.close()
        return content

    @staticmethod
    def get_basename(filename):
        """ Without Parent Directory  """
        return os.path.basename(filename)

    @staticmethod
    def get_nakedname(filename):
        """ Without Parent Directory & Extension """
        return os.path.basename(filename).replace(FileSystem.get_extension(filename), "")

    @staticmethod
    def get_strippedname(filename):
        """ Without Extension """
        return filename.replace(FileSystem.get_extension(filename), "")

    @staticmethod
    def get_completename(directory: str, filename: str):
        """ Without Full Directory """
        if (os.path.dirname(filename) == ""):
            if (directory.endswith(os.path.sep)):
                return directory + filename
            else:
                return directory + os.path.sep + filename
        else:
            return filename

    @staticmethod
    def get_extension(filename):
        """ Get Extension """
        return os.path.splitext(os.path.basename(filename))[1]

    @staticmethod
    def is_ext(filename, ext):
        """ Check Extension """
        return FileSystem.get_extension(filename) == ext

    @staticmethod
    def is_FileExist(filename):
        try:
            return os.path.exists(filename)
        except Exception as e:
            return False

    @staticmethod
    def is_DirExist(filename):
        try:
            return os.path.isdir(filename)
        except Exception as e:
            return False

    @staticmethod
    def remove_extension(filename):
        return filename.replace(FileSystem.get_extension(filename), "")

    @staticmethod
    def safeListFiles(dir: str = ".", file_ext: str = "", keepext=False) -> list:
        myList = list()
        for f in glob.glob(dir+os.sep+"*"+file_ext):
            f = f.replace(dir+os.sep, "")
            if (keepext is False):
                f = FileSystem.remove_extension(f)
            myList.append(f)
        return myList

    @staticmethod
    def loadYamlFile(file_name: str) -> dict:
        try:
            with open(file_name, 'r') as yaml_stream:
                return yaml.safe_load(yaml_stream)
        except:
            Term.print_error("Error Reading File : " + file_name)
            raise

    @staticmethod
    def loadJsonFile(file_name: str) -> dict:
        try:
            if (not FileSystem.is_FileExist(file_name)):
                Term.print_error("File not Found : "+file_name)
                return None
            with open(file_name, 'r') as json_stream:
                return json.load(json_stream)
        except:
            Term.print_error("Error Reading File : "+file_name)
            raise

###
### Scan Current Nef Configuration File Structure and Data
###

def explore(explore_dir):
    data = dict()
    dirlist = FileSystem.safeListFiles(explore_dir, keepext=True)
    for elem in dirlist:
        file_name = explore_dir + os.sep + elem
        if FileSystem.is_ext(file_name, ".yaml"):
            print("Reading : "+file_name)
            data[elem] = FileSystem.loadYamlFile(file_name)
        elif FileSystem.is_ext(file_name, ".json"):
            print("Reading : " + file_name)
            data[elem] = FileSystem.loadJsonFile(file_name)
        elif FileSystem.is_ext(file_name, ".xml"):
            print("Reading : "+file_name)
            myFile = open(file_name, "r")
            xmlContent = myFile.read()
            myFile.close()
            # data[elem] = xmltodict.parse(xmlContent)
        elif FileSystem.is_DirExist(file_name):
            data[elem] = explore(file_name)
        else:
            print("Unknown file type : "+file_name)
    return data

NefConfiguration_SchemaFile = "Nef" + os.sep + "NEF_Configuration_Schema.json"
NefConfiguration_SchemaFile = "NEF_Configuration_Schema.json"
NefConfiguration_SchemaFileURL = "file:///" + NefConfiguration_SchemaFile
# file:///C:/Users/bheuse/PycharmProjects/

class NefConfigurationBase :

    def __init__(self, pConfigFilename, pSchemaFile : dict = None):
        self.loadConfig(pConfigFilename)
        self.loadSchema(pSchemaFile)
        self.status = self.validateConfiguration()

    def loadConfig(self, pURI : str):
        # self.loader = requests.Session()
        # self.loader.mount('file://', FileAdapter())
        # resp = self.loader.get(NefConfiguration_SchemaFileURL)
        # Term.print_blue(str(resp))
        lConfigFilename = pURI
        if pURI.startswith("file:///") :
            lConfigFilename = pURI.replace("file:///", "")
        self.config = FileSystem.loadJsonFile(pURI.replace(lConfigFilename))
        if (not self.config):
            Term.print_error("NefConfiguration File not found : "+lConfigFilename)

    def loadSchema(self, pURI : str):
        # self.loader = requests.Session()
        # self.loader.mount('file://', FileAdapter())
        # resp = self.loader.get(NefConfiguration_SchemaFileURL)
        # Term.print_blue(str(resp))
        lSchemaFile = pURI if (pURI) else NefConfiguration_SchemaFile
        if pURI.startswith("file:///") :
            lSchemaFile = pURI.replace("file:///", "")
        self.schema = FileSystem.loadJsonFile(lSchemaFile)
        if (not self.schema):
            Term.print_error("NefConfiguration Scheme not found : "+lSchemaFile)


    def getFlattened(self, sep: str = "/") -> dict:
        newDict = {}
        for key, value in self.config.items():
            if type(value) == dict:
                fDict = {sep.join([key, _key]): _value for _key, _value in self.getFlattened(value, sep).items()}
                newDict.update(fDict)
            elif type(value) == list:
                i = 0
                for el in value:
                    fDict = {sep.join([key, str(i), _key]): _value for _key, _value in self.getFlattened(el, sep).items()}
                    newDict.update(fDict)
                    i = i + 1
            else:
                newDict[key] = value
        return newDict

    def validateConfiguration(self, configuration=None) -> bool :
        if (not configuration) :
            configuration = self.config
        try :
            validate(configuration, schema=self.schema)
            self.status = True
        except Exception as e:
            Term.print_error("Invalid Configuration : " + str(e))
            self.status = False
        return self.status

    def matchNfProfile(self, pNfProfile, pNfIdentification):
        if pNfIdentification["vendorId"] != pNfProfile["vendorId"] : return False
        if pNfIdentification["nfType"]   != pNfProfile["nfType"]   : return False
        for featureId in pNfIdentification["features"] :
            for featureProf in pNfProfile["features"]:
                if featureId["featureName"]    != featureProf["featureName"] : continue
                if featureId["featureVersion"] != featureProf["featureVersion"]: return False
        return True

    def strNfProfile(self, pNfProfile):
        if (not pNfProfile) : return "[]"
        l_str = "[" + pNfProfile["nfType"] + "-" + pNfProfile["vendorId"]
        for feature in  pNfProfile["features"] :
            l_str = l_str + ":" + feature["featureName"]  + "=" + feature["featureVersion"]
        l_str = l_str + "]"
        return l_str

    def listNfProfiles(self):
        lNfProfilelist = []
        for nfProfile in self.config["nf_profiles"] :
            lNfProfilelist.append(nfProfile["nf_identification"])
        return lNfProfilelist

    def getNfProfile(self, pNfIdentification):
        if (not pNfIdentification) : return None
        for nfProfile in self.config["nf_profiles"] :
            if self.matchNfProfile(nfProfile["nf_identification"], pNfIdentification):
                return nfProfile
        return None


class NefConfigurationGetter(NefConfigurationBase):

    def __init__(self, pConfigFilename, pSchemaFile: dict = None):
        super().__init__(pConfigFilename, pSchemaFile)
        self.cache  = ExpiringDict(max_len=200, max_age_seconds=30)

    def getServiceParameter(self, pNfProfile : dict, pApiProfile, pService, pParameterName, pDefaultValue):
        """
        :param pNfProfile: can be None
        :param pApiProfile:
        :param pService:
        :param pParameterName:
        :param pDefaultValue:
        :return:
        """
        # Check Cache
        cacheKey = "/ServiceParameter/" + self.strNfProfile(pNfProfile) + "/" + pApiProfile + "/" + pService + "/" + pParameterName
        val = self.cache.get(cacheKey)
        if val : return val
        # Access
        l_service = None
        l_from    = "pDefaultValue"
        profile = self.getNfProfile(pNfProfile)
        if ((profile) and (pService in profile["services"])):
            l_service = profile["services"][pService]
            l_from    = "/nf_profiles/"+self.strNfProfile(pNfProfile)+"/services/"+pService
        else:
            Term.print_verbose("No nfProfile for : " + json.dumps(pNfProfile, indent=3))
            if (pApiProfile in self.config["api_profiles"]) and (pService in self.config["api_profiles"][pApiProfile]["services"]):
                l_service = self.config["api_profiles"][pApiProfile]["services"][pService]
                l_from    = "/api_profiles/"+pApiProfile+"/services/"+pService
            else:
                Term.print_verbose("No api_profiles for : " + pApiProfile)
                if (pService in self.config["NefCommon"]["services"]):
                    l_service = self.config["NefCommon"]["services"][pService]
                    l_from    = "/NefCommon/services/"+pService
                else:
                    Term.print_verbose("No NefCommon for : " + pService)
        if (not l_service):
            rv = pDefaultValue, "pDefaultValue"
        elif (pParameterName not in l_service):
            rv = pDefaultValue, "pDefaultValue"
        else:
            rv = l_service[pParameterName],      l_from+"/"+pParameterName
        # Cache & Return
        self.cache[cacheKey] = rv
        return rv

    def getNfClientParameter(self, pNfProfile : dict, pApiProfile, pClientService, pOperation, pParameterName, pDefaultValue):
        """
        :param pNfProfile: can be None
        :param pApiProfile:
        :param pClientService:
        :param pOperation: can be None
        :param pParameterName:
        :param pDefaultValue:
        :return:
        """
        # Check Cache
        cacheKey = "/NfClientParameter/" + self.strNfProfile(pNfProfile) + "/" + pApiProfile + "/" + pClientService + "/" + pOperation + "/" + pParameterName
        val = self.cache.get(cacheKey)
        if val : return val
        # Access
        l_nfClient = None
        l_from     = "pDefaultValue"
        profile = self.getNfProfile(pNfProfile)
        if ((profile) and (pClientService in profile["nfClients"])):
            l_nfClient = profile["nfClients"][pClientService]
            l_from     = "/nf_profiles/"+self.strNfProfile(pNfProfile)+"/nfClients/"+pClientService
        else:
            Term.print_verbose("No nfProfile for : " + json.dumps(pNfProfile, indent=3))
            if (pApiProfile in self.config["api_profiles"]) and (pClientService in self.config["api_profiles"][pApiProfile]["nfClients"]):
                l_nfClient = self.config["api_profiles"][pApiProfile]["nfClients"][pClientService]
                l_from     = "/api_profiles/"+pApiProfile+"/nfClients/"+pClientService
            else:
                Term.print_verbose("No api_profiles for : " + pApiProfile)
                if (pClientService in self.config["NefCommon"]["nfClients"]):
                    l_nfClient = self.config["NefCommon"]["nfClients"][pClientService]
                    l_from     = "/NefCommon/nfClients/"+pClientService
                else:
                    Term.print_verbose("No NefCommon for : " + pClientService)
        if (not l_nfClient):
            rv = pDefaultValue, "pDefaultValue"
        elif (pOperation not in l_nfClient):
            rv = pDefaultValue, "pDefaultValue"
        elif (pParameterName not in l_nfClient[pOperation]):
            # if (pParameterName in l_nfClient):
            #   rv = l_nfClient[pParameterName], l_from+"/"+pParameterName
            # else:
            rv = pDefaultValue, "pDefaultValue"
        else:
            rv = l_nfClient[pOperation][pParameterName],     l_from+"/"+pOperation+"/"+pParameterName
        # Cache & Return
        self.cache[cacheKey] = rv
        return rv

    def getStageParameter(self, pNfProfile : dict, pApiProfile, pStage, pParameterName, pDefaultValue):
        """
        :param pNfProfile: can be None
        :param pApiProfile:
        :param pStage:
        :param pParameterName:
        :param pDefaultValue:
        :return:
        """
        # Check Cache
        cacheKey = "/StageParameter/" + self.strNfProfile(pNfProfile) + "/" + pApiProfile + "/" + pStage+ "/" + pParameterName
        val = self.cache.get(cacheKey)
        if val : return val
        # Access
        l_stage = None
        l_from  = ""
        profile = self.getNfProfile(pNfProfile)
        if ((profile) and (pStage in profile["stages"])):
            l_stage = profile["stages"][pStage]
            l_from    = "/nf_profiles/"+self.strNfProfile(pNfProfile)+"/stages/"+pStage
        else:
            Term.print_verbose("No nfProfile for : " + json.dumps(pNfProfile, indent=3))
            if (pApiProfile in self.config["api_profiles"]) and (pStage in self.config["api_profiles"][pApiProfile]["stages"]):
                l_stage = self.config["api_profiles"][pApiProfile]["stages"][pStage]
                l_from = "/api_profiles/"+pApiProfile+"/stages/"+pStage
            else:
                Term.print_verbose("No api_profiles for : " + pApiProfile)
                if (pStage in self.config["NefCommon"]["stages"]):
                    l_stage = self.config["NefCommon"]["stages"][pStage]
                    l_from = "/NefCommon/stages/"+pStage
                else:
                    Term.print_verbose("No NefCommon for : " + pStage)
        if (not l_stage):
            rv = pDefaultValue, "pDefaultValue"
        elif (pParameterName not in l_stage):
            rv = pDefaultValue, "pDefaultValue"
        else:
            rv = l_stage[pParameterName],      l_from+"/"+pParameterName
        # Cache & Return
        self.cache[cacheKey] = rv
        return rv

    def getNefParameter(self, pParameterName, pDefaultValue):
        # Check Cache
        cacheKey = "/NefParameter/" + pParameterName
        val = self.cache.get(cacheKey)
        if val : return val
        # Access
        if (pParameterName in self.config["NefParameters"]):
            rv = self.config["NefParameters"][pParameterName], "/NefParameters"
        else:
            rv = pDefaultValue, "pDefaultValue"
        # Cache & Return
        self.cache[cacheKey] = rv
        return rv


class NefConfigurationBrowser(NefConfigurationGetter) :

    def __init__(self, pConfigFilename, pSchemaFile: dict = None):
        super().__init__(pConfigFilename, pSchemaFile)

    def listAPIs(self):
        lApiList = []
        for api in self.config["api_profiles"] :
            lApiList.append(api)
        return lApiList

    def getAPI(self, pApiName : str):
        lApiYaml = None
        for api in self.config["api_profiles"] :
            if (pApiName == api) :
                lApiYaml = self.config["api_profiles"][pApiName]["openAPIyaml"]
        return lApiYaml

    def getParameterDescriptor(self, parameterPath, separator="/"):
        """    We should have a utility that from a ConfigurationID and ParameterID (JSONPath),
               return the Schema for this property(parameter) / object (category).
               /nf_profiles/0/stages/MeSelectLocationServiceStage/locationService
                            ^ array  ^object                      ^object or property
        """
        parameterDescriptor = self.schema
        keys = parameterPath.split(separator, -1)
        for key in keys:
            if (key == '') : continue
            if (parameterDescriptor["type"] == "array"):
                parameterDescriptor = parameterDescriptor["items"]
                if ("$ref" in parameterDescriptor):
                    parameterDescriptor = self.schema["$defs"][parameterDescriptor["$ref"].replace("#/$defs/", '')]
                continue
            parameterDescriptor = parameterDescriptor["properties"][key]
            if ("$ref" in parameterDescriptor):
                parameterDescriptor = self.schema["$defs"][parameterDescriptor["$ref"].replace("#/$defs/",'')]
        return parameterDescriptor


class NefConfigurationEditor(NefConfigurationBrowser) :

    def __init__(self, pConfigFilename, pSchemaFile : dict = None):
        super().__init__(pConfigFilename, pSchemaFile)

    def cloneConfiguration(self) -> bool :
        return copy.deepcopy(self.conf)

    def addNfProfiles(self, pNfIdentification):
        nfProfile = dict()
        nfProfile["nf_identification"] = pNfIdentification
        cfg = self.cloneConfiguration()
        cfg["nf_profiles"].append(nfProfile)
        if (not self.validateConfiguration(cfg)): return False
        self.config["nf_profiles"].append(nfProfile)
        return True

    def setNefParameter(self, pParameterName, pValue):
        cfg = self.cloneConfiguration()
        cfg["NefParameters"][pParameterName] = pValue
        if (not self.validateConfiguration(cfg)): return False
        self.config["NefParameters"][pParameterName] = pValue
        return True

    def setServiceParameter(self, pNfProfile : dict = None, pApiProfile = None, pService = None, pParameterName = None, pValue = None):
        """
        if pNfProfile = None & pApiProfile = None  => Set at NFCommon level
        if pNfProfile = None & pApiProfile = API   => Set at pApiProfile level
        if pNfProfile = None & pApiProfile = None  => Set at pNfProfile level
        :param pNfProfile:
        :param pApiProfile:
        :param pService:
        :param pParameterName:
        :param pValue:
        :return:
        """
        return True




Nef_Configuration_Sample_FileName = "Nef"+os.sep+"Nef_Configuration_Sample.json"
Nef_Configuration_Sample_FileName = "Nef_Configuration_Sample.json"

class Test(unittest.TestCase):

    def setUp(self) -> None:
        Term.setVerbose()
        Term.print_red("> Setup")
        Term.print_red("< Setup")

    def testDigger(self):
        data = explore("Nef" + os.sep + "nef-deployment-configuration")
        Term.print_verbose(json.dumps(data, indent=3))
        FileSystem.saveFileContent(json.dumps(data, indent=3), "nef-deployment-configuration" + ".json")

    def testValidateSchema(self):
        Term.print_green("> testValidateSchema")
        cfg = NefConfiguration(Nef_Configuration_Sample_FileName)
        cfg.validateConfiguration()
        Term.print_green("< testValidateSchema")

    def testNefConfiguration(self):
        Term.setVerbose(False)
        cfg = NefConfigurationBrowser(Nef_Configuration_Sample_FileName)
        # Term.print_blue(json.dumps(cfg.config , indent=3))
        # Term.print_flat(cfg.config)

        nfProfile = {"vendorId": "vendorId", "nfType": "AMF", "features": [{"featureVersion": "featureVersion", "featureName": "featureName"}]}

        value = cfg.getStageParameter(pNfProfile=nfProfile, pApiProfile="as-session-with-qos", pStage="AuthStage", pParameterName="enabled", pDefaultValue=False)
        Term.print_blue(str(value))

        value = cfg.getServiceParameter(pNfProfile=None, pApiProfile="traffic-influence", pService="MobileCodes", pParameterName="mcc", pDefaultValue=1050)
        Term.print_blue(str(value))

        value = cfg.getNfClientParameter(pNfProfile=None, pApiProfile="traffic-influence", pClientService="GmlcLocationService", pOperation="CancelLocation", pParameterName="timeout", pDefaultValue=100)
        Term.print_blue(str(value))
        self.assertEqual(value[0], 4001)

        value = cfg.getNefParameter("webGuiPort", pDefaultValue=50)
        Term.print_blue(str(value))

        value = cfg.getStageParameter(pNfProfile=None, pApiProfile="as-session-with-qos", pStage="AuthStage", pParameterName="enabled", pDefaultValue=False)
        Term.print_blue(str(value))
        self.assertEqual(value[0], True)
        value = cfg.getStageParameter(pNfProfile=None, pApiProfile="as-session-with-qos", pStage="AuthStage", pParameterName="enabled", pDefaultValue=False)
        Term.print_blue(str(value))
        self.assertEqual(value[0], True)

        value = cfg.getStageParameter(pNfProfile=None, pApiProfile="as-session-with-qos", pStage="AuthStage", pParameterName="toto", pDefaultValue="TT")
        Term.print_blue(str(value))
        self.assertEqual(value[0], "TT")
        value = cfg.getStageParameter(pNfProfile=None, pApiProfile="as-session-with-qos", pStage="AuthStage", pParameterName="toto", pDefaultValue="TT")
        Term.print_blue(str(value))
        self.assertEqual(value[0], "TT")

        value = cfg.listNfProfiles()
        Term.print_blue(str(value))

        value = cfg.listAPIs()
        Term.print_blue(str(value))

        value = cfg.getAPI("traffic-influence")
        Term.print_blue(str(value))

        value = cfg.getParameterDescriptor("schemaUri")
        Term.print_blue(str(value))

        value = cfg.getParameterDescriptor("NefCommon")
        Term.print_blue(str(value))

        value = cfg.getParameterDescriptor("nf_profiles/0/stages/MeSelectLocationServiceStage/locationService")
        Term.print_blue(str(value))

        value = cfg.getParameterDescriptor("/nf_profiles/[AMF-vendorId:featureName=featureVersion]/stages/AuthStage/enabled")
        Term.print_blue(json.dumps(value, indent=2))

