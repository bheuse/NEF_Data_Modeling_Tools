#! /usr/bin/python3

import xmltodict
import requests
import json
import copy
import yaml
import unittest
import sys
import os
import re
from jsonschema import validate, exceptions
import logging
import datetime
from termcolor import colored
import unidecode
import glob
import getopt
from mako.template import Template
from mako.lookup import TemplateLookup
import mako.runtime
import shutil
from typing import Union

### Logging
timestamp = datetime.datetime.now().strftime("%y%m%d-%H%M%S")
logFile   = "."+os.sep+"data_model_to_openapi.log"
logging.basicConfig(filename=logFile, filemode='w', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)

### Defaults / Constants
default_data_model   = "NEF" + os.sep + "API_Data_Model_Sample" + os.sep + "API_Data_Model_Sample"
default_include_dir  = "NEF" + os.sep + "include"
templates_dir_suffix = "_templates"
artifacts_dir_suffix = "_artifacts"
openapi_yaml_suffix  = "_API.yaml"
schema_json_suffix   = "_Schema.json"
json_schema_baseURI  = "https://amdocs.com/schemas/nef/"

###
### Term Util - Print
###

class Term:

    VERBOSE = False

    @staticmethod
    def setVerbose(verbose : bool = True):
        Term.VERBOSE = verbose

    @staticmethod
    def print_verbose(text):
        if (Term.VERBOSE):  print(colored(text, "magenta"))
        logging.debug(text)

    @staticmethod
    def print_error(text, exception : str = None):
        print(colored(text, "red"))
        logging.error(text)
        if (exception):
            print(colored(exception, "red"))
            logging.error(exception)

    @staticmethod
    def print_warning(text, exception : str = None):
        if (Term.VERBOSE):
            print(colored(text, "cyan"))
        logging.warning(text)
        if (exception):
            print(colored(exception, "red"))
            logging.warning(exception)

    @staticmethod
    def print_green(text):
        print(colored(text, "green"))
        logging.debug(text)

    @staticmethod
    def print_red(text):
        print(colored(text, "red"))
        logging.debug(text)

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

    @staticmethod
    def print_flat(tree_dict):
        flat_dict = Util.flatten(tree_dict, ":")
        for key in flat_dict.keys() :
            print(colored(key, "blue") + " : " + colored(flat_dict[key], "yellow"))

    @staticmethod
    def gen_assert(data : dict):
        flat = Util.flatten(data, '/')
        for item in flat.keys():
            if (isinstance(flat[item], str)):
                print("        self.assertEqual(flat[\""+item+"\"], \""+str(flat[item])+"\")")
            else:
                print("        self.assertEqual(flat[\""+item+"\"], "+str(flat[item])+")")

###
### Directories and Files
###


class FileSystem:

    @staticmethod
    def getDirName(filename):
        """ Without Parent Directory  """
        return os.path.dirname(filename)

    @staticmethod
    def getBaseName(filename):
        """ Without Parent Directory  """
        return os.path.basename(filename)

    @staticmethod
    def getNakedName(filename):
        """ Without Parent Directory & Extension """
        return os.path.basename(filename).replace(FileSystem.getExtension(filename), "")

    @staticmethod
    def getStrippedName(filename):
        """ Without Extension """
        return filename.replace(FileSystem.getExtension(filename), "")

    @staticmethod
    def getCompleteName(directory: str, filename: str):
        """ Without Full Directory """
        if (os.path.dirname(filename) == ""):
            if (directory.endswith(os.path.sep)):
                return directory + filename
            else:
                return directory + os.path.sep + filename
        else:
            return filename

    @staticmethod
    def getExtension(filename):
        """ Get Extension """
        return os.path.splitext(os.path.basename(filename))[1]

    @staticmethod
    def isExtension(filename, ext):
        """ Check Extension """
        return FileSystem.getExtension(filename) == ext

    @staticmethod
    def isFileExist(filename):
        return os.path.exists(filename)

    @staticmethod
    def isDirExist(filename):
        return os.path.isdir(filename)

    @staticmethod
    def createDir(dirName):
        # Create target directory & all intermediate directories that do not exist
        if not os.path.exists(dirName):
            os.makedirs(dirName)

    @staticmethod
    def rmDir(dirName, silent : bool = False) -> bool:
        try:
            shutil.rmtree(dirName)
            return True
        except OSError as error:
            if (silent) : return False
            Term.print_error("Directory can not be removed : " + str(dirName) + "\n" + str(error))
            return False

    @staticmethod
    def removeExtension(filename):
        return filename.replace(FileSystem.getExtension(filename), "")

    @staticmethod
    def safeListFiles(directory: str = ".", file_ext: str = "", keepExt=False) -> list:
        myList = list()
        for f in glob.glob(directory+os.sep+"*"+file_ext):
            f = f.replace(directory+os.sep, "")
            if (keepExt is False):
                f = FileSystem.removeExtension(f)
            myList.append(f)
        return myList

    @staticmethod
    def saveFileContent(content, file_name: str):
        with open(file_name, "w") as file:
            content = file.write(content)
            file.close()
        return content

    @staticmethod
    def loadFileContent(file_name: str) -> Union[str, None]:
        if (not FileSystem.isFileExist(file_name)):
            Term.print_error("File not Found : " + file_name)
            return None
        with open(file_name, "r") as file:
            content = file.read()
            file.close()
        return content

    @staticmethod
    def loadFileData(file_name: str) -> Union[dict, None]:
        return FileSystem.loadDataContent(FileSystem.loadFileContent(file_name))

    @staticmethod
    def loadJsonContent(content: str) -> Union[dict, None]:
        if (not content) or (content == "") : return None
        try:
            return json.loads(content)
        except Exception as ex:
            Term.print_error("Error Loading JSON Content : " + str(content)[0: 50] + " ... \n" + str(ex))
            return None

    @staticmethod
    def loadYamlContent(content: str) -> Union[dict, None]:
        if (not content) or (content == "") : return None
        try:
            parsed_data = yaml.safe_load(content)
            if not isinstance(parsed_data, dict): return None
            return parsed_data
        except Exception as ex:
            Term.print_error("Error Reading YAML Content : " + str(content)[0: 50] + " ... \n" + str(ex))
            return None

    @staticmethod
    def loadDataContent(content) -> Union[dict, None]:
        if (not content) or (content == "") : return None
        dc = FileSystem.loadJsonContent(content)
        if (not dc): dc = FileSystem.loadYamlContent(content)
        return dc

###
### Util
###


class Util:

    @staticmethod
    def flatten(pDict : dict, sep: str = "/") -> dict:
        newDict = {}
        for key, value in pDict.items():
            if type(value) == dict:
                fDict = {sep.join([key, _key]): _value for _key, _value in Util.flatten(value, sep).items()}
                newDict.update(fDict)
            elif type(value) == list:
                i = 0
                for el in value:
                    if type(el) == dict:
                        fDict = {sep.join([key, str(i), _key]): _value for _key, _value in Util.flatten(el, sep).items()}
                        newDict.update(fDict)
                    else:
                        newDict[key + sep + str(i)] = str(el)
                        pass
                    i = i + 1
            else:
                newDict[key] = value
        return newDict

    @staticmethod
    def json_load(text : str) -> dict:
        try:
            return json.loads(text)
        except Exception as ex :
            Term.print_error("Error with decoding JSON :")
            Term.print_error(text)
            Term.print_error(str(ex))
            raise ex

    @staticmethod
    def yaml_load(text : str) -> dict:
        try:
            return yaml.safe_load(text)
        except Exception as ex :
            Term.print_error("Error with decoding YAML :")
            Term.print_error(text)
            Term.print_error(str(ex))
            raise ex

    @staticmethod
    def findBetween(content, start, end):
        found = re.search(start + '([\s\S]*?)' + end, content)
        if (found is None): return None
        found = found.group(1)
        found = re.sub(start, "", found)
        found = re.sub(end, "", found)
        return found

    @staticmethod
    def removeBetween(content, start, end) -> Union[str, None]:
        if (not content): return ""
        found = re.sub(start + '([\s\S]*?)' + end, "", content)
        if (found): return found
        return ""

    @staticmethod
    def getParameters(text, prefix) -> Union[str, None] :
        found = Util.findBetween(text.strip(), "<" + prefix + ">", "</" + prefix + ">")
        if (found): return found
        return None

###
### Data Model
###

"""

The content of the Data Model in SQL Architect will be used as in ReadMe File.

THe mapping as follow :


DataModel                       Architect                              

Entity:
    entity["name"]              = Logical Name
    entity["type"]              = "object"
    entity["description"]       = table["remarks"] (stripped off <tags></tags>)
    entity["example"]           = table["@physicalName"]
    entity["NAME"]              = Logical Name
    entity["TABLE"]             = table["@id"]                         N/A
    entity["RELATIONS"]         = {}
    entity["properties"]        = {}
    entity["PATH_PREFIX"]       = _PATH ["@defaultValue"]
    entity["PATH"]              = _PATH ["@physicalName"]
    entity["PATH_OPERATION"]    = _PATH ["remarks"] "read-only"
    entity["PATH_PARAMETERS"]   = _PATH ["remarks"] between <parameters> & </parameters>
    Not Generated               = if ("ignore" in table["@physicalName"]) => Not Generated

Property:

    this_property["name"]        = name
    this_property["type"]        = "INVALID"
    this_property["description"] = att["@name"]
    this_property["example"]     = att["@physicalName"]
    this_property["mandatory"]   = "n"
    this_property["pattern"]     = att["@defaultValue"]
    this_property["type"]        = "string"
    this_property["format"]      = ""

Link:

     TableContenue   = links[link]["TableContained"]
     TableContenante = links[link]["TableContaining"]
     cardinality     = links[link]["Cardinalite"]       OneToOne (3), ZeroToOne (2) , OneToMany (1), ZeroToMany (0) 
     Name            = links[link]["Name"]
     Descr           = links[link]["Description"]

"""


class DataModel:

    def __init__(self, location : str = default_data_model):
        self.location          = location
        self.name              = FileSystem.getBaseName(location)
        # Objects of Interest
        self.entities          = {}
        self.links             = {}
        self.openapi           = {}   # To OpenAPI Yaml
        self.schema_parameters = {}   # To OpenAPI Objects
        self.context           = {}   # Additional Global Context

    def findEntity(self, entity_name):
        """ Return Entity by Name """
        for entity in self.entities.keys():
            if (("NAME" in self.entities[entity]) and (self.entities[entity]["NAME"] == entity_name)):
                return self.entities[entity]
            if (("name" in self.entities[entity]) and (self.entities[entity]["name"] == entity_name)):
                return self.entities[entity]
        return None
    
    def findTableContainedLinks(self, table_containing) -> list:  # links
        """ Return Links for a specified Containing Table """
        lks = list()
        for link in self.links:
            if (self.links[link]["TableContaining"] == table_containing):
                lks.append(self.links[link])
        return lks
   
    def findTableContainedNames(self, table_containing) -> list:  # string
        """ Return Contained Tables for a specified Containing Table """
        tables = list()
        for link in self.findTableContainedLinks(table_containing) :
            tables.append(link["TableContained"])
        return tables
    
    def findTableCardinality(self, table_containing, table_contained) -> Union[str, None]:
        """ Return Contained Tables for a specified Containing Table """
        for relation in self.entities[table_containing]["RELATIONS"]:
            if (self.entities[table_containing]["RELATIONS"][relation]["TableContained"] == table_contained):
                return self.entities[table_containing]["RELATIONS"][relation]["Cardinalite"]
        return None

    def addContext(self, p_context):
        if (not p_context) : return self.context
        if (isinstance(p_context, dict)) :
            self.context = {**self.context, **p_context}
        if ((isinstance(p_context, str)) and (FileSystem.isFileExist(p_context))):
            self.context = {**self.context, **FileSystem.loadFileData(p_context)}
        elif (isinstance(p_context, str)) :
            self.context = {**self.context, **FileSystem.loadDataContent(p_context)}
    ###
    ### Schema Methods
    ###

    @staticmethod
    def setDefault(attribute: str, desc: dict, prop: str, default) -> dict:
        if ((prop not in desc) or (str(desc[prop]).strip() == "")):
            desc[prop] = default
            Term.print_warning("Warning : attribute [" + str(attribute) + "] " + str(prop) + " defaulted to : [" + str(default) + "]")
        return desc

    @staticmethod
    def decodePropSchema(prop: Union[str, None], schema: str, description: str = None, key: str = "schema") -> dict:
        """ Decode for JSON Schema in <schema> </schema>
        - schema is the text to be decoded
        - prop is used to refer to the related property in error messages
        - description will be used as default is not in schema
        """
        desc_schema = dict()
        if (Util.findBetween(schema, "<" + key + ">", "</" + key + ">")):
            schema = Util.findBetween(schema, "<" + key + ">", "</" + key + ">")
            schema = schema.strip()
            try:
                if schema.startswith("{"):  # JSON
                    desc_schema = Util.json_load(schema)
                elif schema.startswith("\""):  # JSON
                    desc_schema = Util.json_load("{" + schema + "}")
                elif (schema == ""):  # JSON
                    desc_schema = dict()
                else:  # YAML
                    desc_schema = Util.yaml_load(schema)
            except Exception as e:
                Term.print_error(schema, str(e))
                desc_schema = dict()

        description = Util.removeBetween(description, "<" + key + ">", "</" + key + ">")
        if (not description or description.strip() == ""):
            description = "No Description"

        # Defaults for both Attributes and Objects
        desc_schema = DataModel.setDefault(prop, desc_schema, "description", description)
        desc_schema = DataModel.setDefault(prop, desc_schema, "markdownDescription", description)
        desc_schema = DataModel.setDefault(prop, desc_schema, "key", False)
        desc_schema = DataModel.setDefault(prop, desc_schema, "filter", False)
        desc_schema = DataModel.setDefault(prop, desc_schema, "validationScript", "")
        desc_schema = DataModel.setDefault(prop, desc_schema, "example", "")
        desc_schema = DataModel.setDefault(prop, desc_schema, "applicableTo", "")
        desc_schema = DataModel.setDefault(prop, desc_schema, "validFor", "")
        return desc_schema

    def checkAsParameter(self, desc, desc_schema):
        """ Check if this desc_schema property should be set as a global schema parameter and create it if necessary
        - desc description will be used as default if not in schema
        """
        if ("asParameter" in desc_schema):
            param_desc = dict()
            param_desc["name"] = desc_schema["name"]
            if ("path" in desc_schema["asParameter"].lower()):
                param_desc["in"] = "path"
            else:
                param_desc["in"] = "query"
            param_desc["description"] = desc["description"]
            if (("required" in desc_schema["asParameter"].lower()) or (
                    "mandatory" in desc_schema["asParameter"].lower())):
                param_desc["required"] = True
            else:
                param_desc["required"] = False
            param_desc["schema"] = dict()
            param_desc["schema"]["type"] = desc_schema["type"]
            if not ((desc_schema["format"] == "") or (desc_schema["format"] == "free")):
                param_desc["schema"]["format"] = desc_schema["format"]
            # param_desc["schema"]["minimum"] =
            # param_desc["schema"]["maximum"] =
            param_desc["schema"]["default"] = desc_schema["defaultValue"]
            if (desc_schema["possibleValues"] and desc_schema["possibleValues"].__len__() >= 1):
                param_desc["schema"]["enum"] = desc_schema["possibleValues"]
            # param = { desc_schema["name"]+"Param" : param_desc }
            # DataModel.schema_parameters.append(param)
            self.schema_parameters[desc_schema["name"] + "Param"] = param_desc
            return param_desc
        else:
            return None

    """
    limitParam:       # Can be referenced as '#/components/parameters/limitParam'
          name: limit
          in: query
          description: Maximum number of items to return.
          required: false
          schema:
            type: integer
            format: int32
            minimum: 1
            maximum: 100
            default: 20
    """

###
### Architect Parser
###


class Architect:

    def __init__(self, architect_model_file : str = None):
        self.architect_file = None    # Architect Data Model File
        self.architect = None         # Full SQL Architect Model
        self.tables    = dict()       # Tables From SQL Architect
        self.relations = dict()       # Links  From SQL Architect
        self.dataModel = DataModel()  # Interim Data Model
        if (architect_model_file):
            self.setFile(architect_model_file)

    def setFile(self, architect_model_file : str):
        if (architect_model_file):
            architect_model_file = str(architect_model_file).replace(".architect", "")

        if (architect_model_file) and FileSystem.isFileExist(architect_model_file + ".architect"):
            self.architect_file = architect_model_file
            Term.print_verbose("Set Model : " + architect_model_file + ".architect")
            if (self.architect_file):
                self.dataModel = DataModel(self.architect_file)
            return self.architect_file
        else:
            self.architect_file = None
            Term.print_error("Model not found : " + str(architect_model_file))
            return None

    @staticmethod
    def cleanName(name: str) -> str:
        return unidecode.unidecode(name.strip()).replace(" ", "_").replace("\\", "_") \
                        .replace("'", "_").replace("/", "-").replace("_fk", "")

    def findTableName(self, table_id):
        for table in self.dataModel.entities.keys():
            if (self.dataModel.entities[table]["TABLE"] == table_id):
                return self.dataModel.entities[table]["NAME"]
        return None

    def findTableKey(self, table_id):
        for table in self.dataModel.entities.keys():
            if (self.dataModel.entities[table]["TABLE"] == table_id):
                return self.dataModel.entities[table]["KEY"]
        return None

    def collectLinks(self) -> dict :   # { link_id , link }
        """ Scan for all Links / Relationships  and their Attributes in the Architect Data Model """
        links = {}
        if isinstance(self.relations, dict) :
            self.relations = [self.relations]
        for relation in self.relations:
            link = dict()
            if ("ignore" in relation["@name"].lower()) :
                # Ignore starting with ignore (or Grey Links)
                Term.print_verbose("Relation Ignored (ignore in name) : " + Architect.cleanName(relation["@name"]))
                continue
            link["TableContaining"] = relation["@pk-table-ref"]
            link["TableContained"]  = relation["@fk-table-ref"]
            if (relation["@fkCardinality"] == "3") :  link["Cardinalite"]     = "ZeroToOne"
            if (relation["@fkCardinality"] == "7") :  link["Cardinalite"]     = "OneToMore"
            if (relation["@fkCardinality"] == "6") :  link["Cardinalite"]     = "ZeroToMore"
            # if (relation["@pkCardinality"] == "3") :  link["Cardinalite"]     = "ZeroToOne"
            # if (relation["@pkCardinality"] == "7") :  link["Cardinalite"]     = "OneToMore"
            # if (relation["@pkCardinality"] == "6") :  link["Cardinalite"]     = "ZeroToMore"
            if (relation["@pkCardinality"] == "2") :  link["Cardinalite"]     = "OneToOne"
            link["Name"]            = Architect.cleanName(relation["@name"])
            link["Description"]     = "No Description"
            ignore = False
            for tlink in self.architect["architect-project"]["play-pen"]["table-link"]:
                if (tlink["@relationship-ref"] == relation["@id"]):
                    # link["Description"] = Architect.cleanName(tlink["@pkLabelText"]) + " " + Architect.cleanName(tlink["@fkLabelText"])
                    link["Description"] = tlink["@pkLabelText"] + " " + tlink["@fkLabelText"]
                    if (link["Description"] == " "): link["Description"] = link["Name"]
                if (ignore is False) :
                    links[relation["@id"]] = link
        return links

    @staticmethod
    def handleObject(table):
        """ Extract Data from Architect Table for Object Descriptors """
        obj_desc = {}
        name = Architect.cleanName(table["@name"])
        obj_desc["name"] = name
        obj_desc["type"] = "object"
        # remarks -> description
        if (table["remarks"] is None):
            table["remarks"] = ""
        obj_desc["description"] = Util.removeBetween(table["remarks"], "<schema>", "</schema>").strip()
        if (obj_desc["description"] == "") :
            obj_desc["description"] = "No Description for " + name

        # remarks : we may have a <schema> </schema> with property description
        desc_schema = DataModel.decodePropSchema(None, table["remarks"], key="schema")
        desc_schema = DataModel.setDefault(name, desc_schema, "key", False)
        desc_schema = DataModel.setDefault(name, desc_schema, "filter", False)
        desc_schema = DataModel.setDefault(name, desc_schema, "validationScript", "")
        desc_schema = DataModel.setDefault(name, desc_schema, "example", "")
        desc_schema = DataModel.setDefault(name, desc_schema, "applicableTo", "")
        desc_schema = DataModel.setDefault(name, desc_schema, "validFor", "")
        obj_desc["Schema"] = desc_schema

        if (table["remarks"]):
            obj_desc["description"] = table["remarks"]
        else:
            obj_desc["description"] = "No Description for " + table["@name"]
        # physicalName -> example
        obj_desc["example"]    = table["@physicalName"]
        obj_desc["properties"] = {}
        obj_desc["NAME"]       = name
        obj_desc["TABLE"]      = table["@id"]
        obj_desc["RELATIONS"]  = {}
        return obj_desc, name

    @staticmethod
    def handleAttribute(obj_desc, att):
        """ Extract Data from Architect Table Attribute for Object Property Descriptors """
        att_property = {}
        att_name = Architect.cleanName(att["@name"])
        att_property["name"] = att_name

        # Handling _PATH for OpenApi Yaml Generation
        if (att_name == "_PATH"):
            # https://amdocs.com<PATH_PREFIX>/<PATH>
            obj_desc["PATH"]           = att["@physicalName"]  # This is the route endpoint
            obj_desc["PATH_PREFIX"]    = att["@defaultValue"]  # This is the route path prefix
            obj_desc["PATH_OPERATION"] = "READ-WRITE"
            if (att["remarks"] is not None):
                parameters = Util.findBetween(att["remarks"], "<parameters>", "</parameters>")
                if (parameters):
                    obj_desc["PATH_PARAMETERS"] = parameters
                    att["remarks"] = Util.removeBetween(att["remarks"], "<parameters>", "</parameters>")
                obj_desc["PATH_OPERATION"]  = att["remarks"]

        # remarks -> description
        if (att["remarks"] is None):
            att["remarks"] = ""
        att_property["description"] = Util.removeBetween(att["remarks"], "<schema>", "</schema>").strip()
        if (att_property["description"] == "") :
            att_property["description"] = "No Description for " + att["@name"]

        # remarks : we may have a <schema> </schema> with property description
        desc_schema = DataModel.decodePropSchema(att_name, att["remarks"], key="schema")
        desc_schema = DataModel.setDefault(att_name, desc_schema, "key", False)
        desc_schema = DataModel.setDefault(att_name, desc_schema, "filter", False)
        desc_schema = DataModel.setDefault(att_name, desc_schema, "validationScript", "")
        desc_schema = DataModel.setDefault(att_name, desc_schema, "valueSpecification", "")
        desc_schema = DataModel.setDefault(att_name, desc_schema, "possibleValues", ["default_value", "value1", "value2"])
        desc_schema = DataModel.setDefault(att_name, desc_schema, "defaultValue", "defaultValue")
        desc_schema = DataModel.setDefault(att_name, desc_schema, "format", "")
        desc_schema = DataModel.setDefault(att_name, desc_schema, "example", "")
        desc_schema = DataModel.setDefault(att_name, desc_schema, "minCardinality", 1)
        desc_schema = DataModel.setDefault(att_name, desc_schema, "maxCardinality", 1)
        desc_schema = DataModel.setDefault(att_name, desc_schema, "applicableTo", "")
        desc_schema = DataModel.setDefault(att_name, desc_schema, "validFor", "")
        att_property["Schema"] = desc_schema

        # physicalName -> example
        if (att["@physicalName"] is None) or (att["@physicalName"] != att_property["name"]):
            if (("example" in desc_schema) and (str(desc_schema["example"]).strip != "")):
                att_property["example"] = desc_schema["example"]
            else:
                att_property["example"] = "No example for " + att["@name"]
        else:
            att_property["example"] = att["@physicalName"]

        # nullable -> not required
        if ((att["@nullable"] == "1") or (att_name == "_PATH") or (att_name == "_ROOT") or (desc_schema["minCardinality"] == 0)) :
            att_property["mandatory"] = "n"
        else:
            if "required" not in obj_desc : obj_desc["required"] = list()
            obj_desc["required"].append(att_name)
            att_property["mandatory"] = "y"

        # defaultValue -> pattern
        att_property["pattern"] = att["@defaultValue"]

        # type -> type + format
        att_property["type"]   = "INVALID"
        att_property["format"] = ""
        if (att["@type"] == "12"):   att_property["type"]   = "string"     # VARCHAR
        if ("@precision" in att):    att_property["precision"]  = att["@precision"]
        if (att["@type"] == "4"):    att_property["type"]   = "integer"    # INTEGER
        if (att["@type"] == "-2"):   att_property["type"]   = "binary"     # BINARY
        if (att["@type"] == "-5"):   att_property["type"]   = "integer"    # BIGINT
        if (att["@type"] == "92"):   att_property["type"]   = "string"     # TIME
        if (att["@type"] == "92"):   att_property["format"] = "date-time"  # -
        if (att["@type"] == "93"):   att_property["type"]   = "string"     # TIMESTAMP
        if (att["@type"] == "93"):   att_property["format"] = "timestamp"  # -
        if (att["@type"] == "2000"): att_property["type"]   = "string"     # JAVA_OBJECT
        if (att["@type"] == "2000"): att_property["format"] = "json"       # -
        if (att["@type"] == "1111"): att_property["type"]   = "any"        # UNKNOWN = any type (needs to be fixed in hooks)
        if (att["@type"] == "16"):   att_property["type"]   = "boolean"    # BOOLEAN
        if (desc_schema["maxCardinality"] > 1):
            # Array
            att_property["items"] = dict()
            att_property["items"]["type"]   = att_property["type"]
            att_property["items"]["format"] = att_property["format"]
            att_property["type"] = "array"
            att_property["minItems"] = desc_schema["minCardinality"]
            att_property["maxItems"] = desc_schema["maxCardinality"]
        if (att_property["type"] == "INVALID"):
            Term.print_error("Unsupported Attribute Type for : " + str(att_name) + " : " + att["@type"])

        # add key name
        if (desc_schema["key"]):  # == True
            obj_desc["KEY"] = att_name

        # add to object descriptor
        if (att_name != "_PATH"):
            obj_desc["properties"][att_name] = att_property

        return obj_desc, att_name

    def collectTables(self) -> dict :  # { entity_name : { entity } }
        """ Scan for all Tables and their Attributes in the Architect Data Model """
        entities = {}
        for table in self.tables:
            data_type, entity_name = self.handleObject(table)
            if ("ignore" in data_type["example"]) :
                Term.print_verbose("Table Ignored (ignore in example/physicalName) : " + Architect.cleanName(entity_name))
                continue
            for folder in table["folder"]:
                if ("index" in folder):
                    if ("index-column" not in folder["index"]): continue
                    # for index_col in folder["index"]["index-column"]:
                    if ("@physicalName" in folder["index"]["index-column"]):
                        data_type["primary_key"] = folder["index"]["index-column"]["@physicalName"]
                if "column" not in folder: continue
                column = folder["column"]
                data_type["KEY"] = None
                if isinstance(column, list):
                    for col in column:
                        data_type, att_name = self.handleAttribute(data_type, col)
                else:
                    data_type, att_name = self.handleAttribute(data_type, column)
            entities[entity_name] = data_type
        return entities

    def collectOpenAPI(self) -> Union[dict, None]:
        """ Scan for OpenAPI Entity and its Attributes in the Architect Data Model """

        # Info Data for OpenAPI / Default Values
        open_api_yaml = dict()
        open_api_yaml["openapi"] = "3.0.2"
        open_api_yaml["info"] = dict()
        open_api_yaml["info"]["title"] = "Business API and Data Model"
        open_api_yaml["info"]["version"] = "1.0.0"
        open_api_yaml["info"]["description"] = "Business API and Data Model. This is generated, modify source SQL Architect data model instead."
        open_api_yaml["info"]["contact"] = {}
        open_api_yaml["info"]["contact"]["name"] = "Bernard Heuse"
        open_api_yaml["info"]["contact"]["url"] = "https://www.amdocs.com/"
        open_api_yaml["info"]["contact"]["email"] = "bheuse@gmail.com"

        if "OpenAPI" not in self.dataModel.entities:
            return None

        # Reading from OpenAPI Entity
        if ("title" in self.dataModel.entities["OpenAPI"]["properties"]):
            title = self.dataModel.entities["OpenAPI"]["properties"]["title"]["example"]
            open_api_yaml["info"]["title"] = title

        if ("version" in self.dataModel.entities["OpenAPI"]["properties"]):
            version = self.dataModel.entities["OpenAPI"]["properties"]["version"]["example"]
            open_api_yaml["info"]["version"] = version

        if ("description" in self.dataModel.entities["OpenAPI"]["properties"]):
            description = self.dataModel.entities["OpenAPI"]["properties"]["description"]["example"] + " " + \
                          self.dataModel.entities["OpenAPI"]["properties"]["description"]["description"]
            open_api_yaml["info"]["description"] = description

        if ("contact" in self.dataModel.entities["OpenAPI"]["properties"]):
            contact = Util.json_load(self.dataModel.entities["OpenAPI"]["properties"]["contact"]["description"])
            open_api_yaml["info"]["contact"] = contact

        if ("security" in self.dataModel.entities["OpenAPI"]["properties"]):
            security = Util.json_load(self.dataModel.entities["OpenAPI"]["properties"]["security"]["description"])
            open_api_yaml["security"] = security

        if ("license" in self.dataModel.entities["OpenAPI"]["properties"]):
            lic = Util.json_load(self.dataModel.entities["OpenAPI"]["properties"]["license"]["description"])
            open_api_yaml["info"]["license"] = lic

        if ("tags" in self.dataModel.entities["OpenAPI"]["properties"]):
            tags = Util.json_load(self.dataModel.entities["OpenAPI"]["properties"]["tags"]["description"])
            open_api_yaml["tags"] = tags

        if ("servers" in self.dataModel.entities["OpenAPI"]["properties"]):
            servers = Util.json_load(self.dataModel.entities["OpenAPI"]["properties"]["servers"]["description"])
            open_api_yaml["servers"] = servers

        if ("securitySchemes" in self.dataModel.entities["OpenAPI"]["properties"]):
            securitySchemes = Util.json_load(self.dataModel.entities["OpenAPI"]["properties"]["securitySchemes"]["description"])
            open_api_yaml["components"] = dict()
            open_api_yaml["components"]["securitySchemes"] = securitySchemes

        if ("context" in self.dataModel.entities["OpenAPI"]["properties"]):
            op_context = Util.json_load(self.dataModel.entities["OpenAPI"]["properties"]["context"]["description"])
            self.dataModel.addContext(op_context)

        del self.dataModel.entities["OpenAPI"]
        self.dataModel.openapi = open_api_yaml

        return open_api_yaml

    def readArchitect(self, architect_model_file : str = None) -> Union[DataModel, None]:
        """ Read and Scan Architect Data Model """
        if (architect_model_file):
            self.setFile(architect_model_file)

        if (not self.architect_file):
            return None

        # Reading architect file
        Term.print_yellow("> read_architect")
        myFile = open(self.architect_file + ".architect", "r")
        architectSchema = myFile.read()
        myFile.close()
        self.architect = xmltodict.parse(architectSchema)

        # Save to JSON Format
        # FileSystem.saveFileContent(json.dumps(self.architect, indent=3), data_model + ".json")
        Term.print_verbose("architect : \n" + json.dumps(self.architect, indent=3))

        # Scan Architect for Data Model
        self.dataModel = DataModel(self.architect_file)

        # Collecting architect tables into data model entities
        if (self.architect["architect-project"]["target-database"]["table"]) :
            self.tables = self.architect["architect-project"]["target-database"]["table"]
            self.dataModel.entities = self.collectTables()

        # Collecting architect relations into data model links
        if (self.architect["architect-project"]["target-database"]["relationships"]) :
            self.relations = self.architect["architect-project"]["target-database"]["relationships"]["relationship"]
            self.dataModel.links = self.collectLinks()

        # Replacing Table IDs by Entity Names & Creating Sub-Relationships
        for entity in self.dataModel.entities:
            for rel in self.dataModel.findTableContainedLinks(self.dataModel.entities[entity]["TABLE"]):
                if (not self.findTableName(rel["TableContained"])): continue
                # Replacing Table IDs by Entity Names
                rel["TableContenanteID"] = rel["TableContaining"]
                rel["TableContenueID"]   = rel["TableContained"]
                rel["TableContaining"]   = self.findTableName(rel["TableContenanteID"])
                rel["TableContained"]    = self.findTableName(rel["TableContenueID"])
                # Handling Sub-Relationships
                self.dataModel.entities[entity]["RELATIONS"][rel["Name"]] = rel
                this_property = dict()
                this_property["description"] = rel["Description"]
                foreign_key = self.findTableKey(rel["TableContenueID"])
                if (rel["Cardinalite"] == "OneToOne") or (rel["Cardinalite"] == "ZeroToOne") :
                    if (foreign_key):
                        this_property["type"] = "string"
                    else:
                        this_property["$ref"] = "#/components/schemas/" + rel["TableContained"]
                else:
                    this_property["type"] = "array"
                    this_property["items"] = {}
                    if (foreign_key):
                        this_property["items"]["type"] = "string"
                    else:
                        this_property["items"]["$ref"] = "#/components/schemas/" + rel["TableContained"]
                self.dataModel.entities[entity]["properties"][rel["TableContained"]] = this_property

        # Collect OpenAPI Data
        self.collectOpenAPI()

        # What did we get ?
        Term.print_verbose("tables    : " + str(self.tables))
        Term.print_verbose("relations : " + str(self.relations))
        Term.print_verbose("entities  : " + str(self.dataModel.entities))
        Term.print_verbose("links     : " + str(self.dataModel.links))
        Term.print_verbose("openapi   : " + str(self.dataModel.openapi))
        Term.print_verbose("context   : " + str(self.dataModel.context))
        Term.print_yellow("< read_architect")

        return self.dataModel

###
### OpenAPI Path Generation
###


class Path:

    paths_template_list_create_prefix  = """
"${PATH_PREFIX}/${PATH}s": {
            "summary": "Path used to manage the list of ${table}s.",
            "description": "The REST endpoint/path used to list and create zero or more `${TABLE}`.  This path contains a `GET` and `POST` operation to perform the list and create tasks, respectively."
"""

    @staticmethod
    def paths_template_list(parameters : str = None) -> str:
        if ((parameters) and (parameters.strip() == "")): parameters = None
        if (not parameters):
            parameters = ""
        else:
            if (parameters.startswith("[")):
                parameters = "\"parameters\" : " + parameters + " , "
            elif (parameters.startswith('"parameters"')):
                parameters = parameters + " , "
            else:
                parameters = "\"parameters\" : [  " + parameters + " ] , "

        paths_template_list = """
                "get": {
                    "operationId": "get${TABLE}s",
                    "summary": "List All ${TABLE}s",
                    "description": "Gets a list of all `${TABLE}` entities.",
                    """ + parameters + """
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {
                                            "$ref": "#/components/schemas/${TABLE}"
                                        }
                                    }
                                }
                            },
                            "description": "Successful response - returns an array of `${TABLE}` entities."
                        }
                    }
                }
"""
        return paths_template_list

    body_content = """
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/${TABLE}"
                                }
                            }
                        },
                        "required": true
"""

    @staticmethod
    def paths_template_create(parameters : str = None) -> str:
        if ((parameters) and (parameters.strip() == "")): parameters = None
        if (not parameters):
            parameters = ""
        else:
            parameters = "\"parameters\" : [  " + parameters + " ] , "
        paths_template_create = """
                    "post": {
                        "operationId": "create${TABLE}",
                        "summary": "Create a ${TABLE}",
                        "description": "Creates a new instance of a `${TABLE}`.",
                        """ + parameters + """
                        "requestBody": {
                            "description": "A new `${TABLE}` to be created.",
                            "content": {
                                "application/json": {
                                        "schema": {
                                            "$ref": "#/components/schemas/${TABLE}"
                                        }
                                }
                            },
                            "required": true
                        },
                        "responses": {
                            "202": {
                                "description": "Successful response.",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "$ref": "#/components/schemas/${TABLE}"
                                        }
                                      }
                                }
                            }
                        }
                    }
        """
        return paths_template_create

    # ${PATH_PREFIX}/${PATH}s/{${PATH}Id}"
    # ${PATH_PREFIX}/${PATH}s/{id}"
    paths_template_read_write_prefix = """
            "${PATH_PREFIX}/${PATH}s/{id}": {
                "summary": "Path used to manage a single ${TABLE}.",
                "description": "The REST endpoint/path used to get, update, and delete single instances of an `${TABLE}`.  This path contains `GET`, `PUT`, and `DELETE` operations used to perform the get, update, and delete tasks, respectively."
    """

    @staticmethod
    def paths_template_get(parameters : str = None) -> str:
        if ((parameters) and (parameters.strip() == "")): parameters = None
        if (not parameters):
            parameters = ""
        else:
            parameters = "\"parameters\" : [  " + parameters + " ] , "
        paths_template_get = """
                    "get": {
                        "operationId": "get${TABLE}",
                        "summary": "Get a ${TABLE}",
                        "description": "Gets the details of a single instance of a `${TABLE}`.",
                        """ + parameters + """
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "$ref": "#/components/schemas/${TABLE}"
                                        }
                                    }
                                },
                                "description": "Successful response - returns a single `${TABLE}`."
                            }
                        }
                    }
        """
        return paths_template_get

    @staticmethod
    def paths_template_put(parameters : str = None) -> str:
        if ((parameters) and (parameters.strip() == "")): parameters = None
        if (not parameters):
            parameters = ""
        else:
            parameters = "\"parameters\" : [  " + parameters + " ] , "
        paths_template_put = """
                    "put": {
                        "operationId": "update${TABLE}",
                        "summary": "Update a ${TABLE}",
                        "description": "Updates an existing `${TABLE}`.",
                        """ + parameters + """
                        "requestBody": {
                            "description": "Updated `${TABLE}` information.",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/${TABLE}"
                                    }
                                }
                            },
                            "required": true
                        },
                        "responses": {
                            "202": {
                                "description": "Successful response.",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "$ref": "#/components/schemas/${TABLE}"
                                        }
                                    }
                                }
                            }
                        }
                    }
        """
        return paths_template_put

    """
                                    "schema": {
                                        "$ref": "#/components/schemas/${TABLE}"
                                    }
    """

    @staticmethod
    def paths_template_patch(parameters : str = None) -> str:
        if ((parameters) and (parameters.strip() == "")): parameters = None
        if (not parameters):
            parameters = ""
        else:
            parameters = "\"parameters\" : [  " + parameters + " ] , "
        paths_template_patch = """
                    "patch": {
                        "operationId": "update${TABLE}",
                        "summary": "Update a ${TABLE}",
                        "description": "Updates an existing `${TABLE}`.",
                        """ + parameters + """
                        "requestBody": {
                            "description": "Updated `${TABLE}` information.",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/${TABLE}"
                                    }
                                }
                            },
                            "required": true
                        },
                        "responses": {
                            "202": {
                                "description": "Successful response.",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "$ref": "#/components/schemas/${TABLE}"
                                         }
                                      }
                                }
                            }
                        }
                    }
        """
        return paths_template_patch

    @staticmethod
    def paths_template_delete(parameters : str = None) -> str:
        if ((parameters) and (parameters.strip() == "")): parameters = None
        if (not parameters):
            parameters = ""
        else:
            parameters = "\"parameters\" : [  " + parameters + " ] , "
        paths_template_delete = """
                    "delete": {
                        "operationId": "delete${TABLE}",
                        "summary": "Delete a ${TABLE}",
                        "description": "Deletes an existing `${TABLE}`.",
                        """ + parameters + """
                        "responses": {
                            "204": {
                                "description": "Successful response."
                            }
                        }
                    }
        """
        return paths_template_delete

    @staticmethod
    def paths_template_parameters() -> str:

        # "name": "${PATH}Id"
        paths_template_parameters = """            
                        {
                            "name": "id",
                            "description": "A unique identifier for a `${TABLE}`.",
                            "schema": {
                                "type": "string"
                            },
                            "in": "path",
                            "required": true
                        }
        """
        return paths_template_parameters

    @staticmethod
    def paths_table(path : str, table: str, path_prefix: str = "", p_paths_template=""):
        l_paths_template = p_paths_template.replace("${PATH_PREFIX}", path_prefix)
        l_paths_template = l_paths_template.replace("${TABLE}", table)
        l_paths_template = l_paths_template.replace("${PATH}", path)
        l_paths_template = l_paths_template.replace("${table}", table.lower())
        return l_paths_template

    @staticmethod
    def create_path(p_model : DataModel):
        entities = p_model.entities
        f_paths_template = ""
        sep = ""
        for entity in entities:
            if ("PATH" in entities[entity]):
                path_par   = None
                list_par   = None
                get_par    = None
                create_par = None
                patch_par  = None
                put_par    = None
                del_par    = None
                schema_par = None
                if ("PATH_PARAMETERS" in entities[entity]) :
                    path_par   = Util.getParameters(entities[entity]["PATH_PARAMETERS"], "path_parameters")
                    list_par   = Util.getParameters(entities[entity]["PATH_PARAMETERS"], "list_parameters")
                    get_par    = Util.getParameters(entities[entity]["PATH_PARAMETERS"], "get_parameters")
                    create_par = Util.getParameters(entities[entity]["PATH_PARAMETERS"], "post_parameters")
                    patch_par  = Util.getParameters(entities[entity]["PATH_PARAMETERS"], "patch_parameters")
                    put_par    = Util.getParameters(entities[entity]["PATH_PARAMETERS"], "put_parameters")
                    del_par    = Util.getParameters(entities[entity]["PATH_PARAMETERS"], "delete_parameters")
                    schema_par = Util.getParameters(entities[entity]["PATH_PARAMETERS"], "schema_parameters")

                # Add Pagination Support
                listParameters = []
                if (list_par):
                    listParameters = json.loads(list_par)
                listParameters.append({"in": "query", "name": "limit", "schema" : {"type": "integer"}, "description": "Pagination Limit"})
                listParameters.append({"in": "query", "name": "offset", "schema" : {"type": "integer"}, "description": "Pagination Offset"})

                # Add Schema Support
                listParameters.append({"in": "query", "name": "schema", "schema" : {"type": "boolean"} , "allowEmptyValue": True, "description": "Return JSON Schema"})

                # Add Filtering Support
                for att in entities[entity]['properties'] :
                    if ('Schema' not in entities[entity]['properties'][att]) : continue
                    if ('filter' not in entities[entity]['properties'][att]['Schema']) : continue
                    if (entities[entity]['properties'][att]['Schema']['filter']):
                        listParameters.append({"in": "query",
                                          "name": entities[entity]['properties'][att]['name'],
                                          "schema": {"type": entities[entity]['properties'][att]['type']},
                                          "description": "Filter for "+entities[entity]['properties'][att]['name']})
                list_par = json.dumps(listParameters)

                if (schema_par and schema_par.strip() != "") :
                    schema_params = Util.json_load(schema_par)
                    for param in schema_params:
                        p_model.schema_parameters[param] = schema_params[param]
                if (not path_par or path_par.strip() == "") :
                    path_par = ""
                    path_parameters = "\"parameters\": [" + Path.paths_template_parameters() + "]"
                else:
                    path_parameters = "\"parameters\": [" + Path.paths_template_parameters() + "," + path_par + "]"
                    path_par = " , \"parameters\": [" + path_par + "]"

                if ("read-only" in entities[entity]["PATH_OPERATION"].lower()):
                    l_paths_template = Path.paths_template_list_create_prefix + "," + Path.paths_template_list(list_par) + path_par + " } ,"
                    l_paths_template = l_paths_template + Path.paths_template_read_write_prefix + "," + path_parameters + "," + Path.paths_template_get(get_par)  + " }"
                elif ("read-create" in entities[entity]["PATH_OPERATION"].lower()):
                    l_paths_template = Path.paths_template_list_create_prefix + "," + Path.paths_template_list(list_par) + "," + Path.paths_template_create(create_par) + path_par + " } ,"
                    l_paths_template = l_paths_template + Path.paths_template_read_write_prefix + "," + path_parameters + "," + Path.paths_template_get(get_par) + " } "
                elif ("create-only" in entities[entity]["PATH_OPERATION"].lower()):
                    l_paths_template = Path.paths_template_list_create_prefix + "," + Path.paths_template_create(create_par) + path_par + "," + path_parameters + " }"
                elif ("read-create-patch" in entities[entity]["PATH_OPERATION"].lower()):
                    l_paths_template = Path.paths_template_list_create_prefix + "," + Path.paths_template_list(list_par) + "," + Path.paths_template_create(create_par)  + path_par + " } ,"
                    l_paths_template = l_paths_template + Path.paths_template_read_write_prefix + "," + path_parameters + "," + Path.paths_template_get(get_par) + "," + Path.paths_template_patch(patch_par) + " } "
                else:  # "read-write"
                    l_paths_template = Path.paths_template_list_create_prefix + "," + Path.paths_template_list(list_par) + "," + Path.paths_template_create(create_par) + path_par + " } ,"
                    l_paths_template = l_paths_template + Path.paths_template_read_write_prefix + "," + path_parameters + "," + Path.paths_template_get(get_par) + "," + Path.paths_template_put(put_par) + "," + Path.paths_template_delete(del_par) + " } "

                path   = entities[entity]["PATH"]
                if (str(entities[entity]["PATH_PREFIX"]).strip() == "") and ("PATH_PREFIX" in p_model.context):
                    prefix = p_model.context["PATH_PREFIX"]
                else:
                    prefix = entities[entity]["PATH_PREFIX"]
                f_paths_template = f_paths_template + sep + Path.paths_table(path, entity, path_prefix=prefix, p_paths_template=l_paths_template)
                sep = ", "
        Term.print_verbose(f_paths_template)
        return f_paths_template


###
### Code Generation & Rendering
###

"""
Note : The OpenAPI Components and JSON Schema do not have exactly the same structure.

There are multiple types for stuff to be generated:
- OpenAPI Components and Operations          : Components + Path  
  => using PATH indicators - CodeGenerator.renderOpenAPI + Path.create_path
- JSON Schema for APIs Validation            : for API Validation
  => using PATH indicators - CodeGenerator.generatePathJsonSchema
- JSON Schema for Configuration Validation   : for Configuration  
  => using ROOT indicators - CodeGenerator.generateRootJsonSchema
- Contexts for Code Generation (using mako)  : This is a JSON Object with all Entities and OpenAPI Details 
  => renderArtifacts = CodeGenerator.generateEntitiesJsonSchema + CodeGenerator.renderOpenAPI + CodeGenerator.renderDir
"""


class CodeGenerator:

    def __init__(self, p_model_location : str = None):
        self.model_location  = p_model_location if p_model_location else default_data_model
        self.templates_dir   = self.model_location + templates_dir_suffix
        self.includes_dir    = default_include_dir
        self.artifacts_dir   = self.model_location + artifacts_dir_suffix
        self.context_file    = None

    def configureDir(self, p_model_location : str, p_templates_dir : str, p_includes_dir : str, p_artifacts_dir : str, p_context_file : str):
        self.model_location = p_model_location.replace(".architect", "")
        Term.print_yellow("Model Location : " + str(self.templates_dir))

        self.templates_dir = p_templates_dir if p_templates_dir else self.model_location + templates_dir_suffix
        Term.print_yellow("Templates Dir  : " + str(self.templates_dir))

        self.includes_dir = p_includes_dir if p_includes_dir else default_include_dir
        Term.print_yellow("Include Dir    : " + str(self.includes_dir))

        self.artifacts_dir = p_artifacts_dir if p_artifacts_dir else  self.model_location + artifacts_dir_suffix
        Term.print_yellow("Artifacts Dir  : " + str(self.artifacts_dir))

        self.context_file = p_context_file if p_context_file else None
        Term.print_yellow("Context File   : " + str(self.context_file))

    def checkDir(self, forRendering : bool = True):

        if (self.artifacts_dir) and (not FileSystem.isDirExist(self.artifacts_dir)):
            FileSystem.createDir(self.artifacts_dir)

        if (self.artifacts_dir) and (not FileSystem.isDirExist(self.artifacts_dir)):
            Term.print_error("Artifacts Dir not found : " + str(self.artifacts_dir))
            Term.print_yellow(read_command_line_args([], p_usage=True))
            quit()

        if (not forRendering) : return

        if (self.templates_dir) and (not FileSystem.isDirExist(self.templates_dir)):
            Term.print_error("Templates Dir not found : " + str(self.templates_dir))
            Term.print_yellow(read_command_line_args([], p_usage=True))
            quit()

        if (self.includes_dir) and (not FileSystem.isDirExist(self.includes_dir)):
            Term.print_error("Include Dir not found : " + str(self.includes_dir))
            Term.print_yellow(read_command_line_args([], p_usage=True))
            quit()

        if (self.context_file) and (not FileSystem.isFileExist(self.context_file)):
            Term.print_error("Context File not found : " + str(self.context_file))
            Term.print_yellow(read_command_line_args([], p_usage=True))
            quit()

    @staticmethod
    def filterBlankLines(string):
        result = ""
        for line in string.splitlines():
            strippedLine = line.strip()
            if strippedLine == '':
                continue
            elif strippedLine == '\\n':
                result += '\n'
            else:
                result += line + '\n'
        return result

    @staticmethod   # Rendering
    def renderFile(p_template_filename : str, p_include_dir : str, p_rendered_filename, p_context: dict):
        Term.print_blue("Rendering : [" + p_template_filename)
        Term.print_blue("   > into : [" + p_rendered_filename + "]")
        template_string = FileSystem.loadFileContent(p_template_filename)
        # dos2unix magic !
        "\n".join(template_string.splitlines())
        # Rendering Template
        mako.runtime.UNDEFINED = 'MISSING_IN_CONTEXT'
        rendered_template = Template(template_string, lookup=TemplateLookup(directories=[p_include_dir])).render(**p_context)
        rendered_template = CodeGenerator.filterBlankLines(rendered_template)
        # And Saving to File ...
        FileSystem.saveFileContent(rendered_template, p_rendered_filename)

    @staticmethod   # Rendering
    def renderDir(p_templates_dir : str, p_include_dir : str, p_artifacts_dir : str, p_context : dict, root : bool = True, p_name : str = None):
        Term.print_yellow("Rendering Templates Dir : [" + p_templates_dir + "]")
        Term.print_yellow("Rendering Artifacts Dir : [" + p_artifacts_dir + "]")
        if (root) :
            # Generating Context File
            contexts_dir = p_artifacts_dir + os.sep + "_Contexts"
            FileSystem.createDir(contexts_dir)
            context_file_yaml = contexts_dir + os.sep + p_context["DATAMODEL"] + "_context.yaml"
            context_file_json = contexts_dir + os.sep + p_context["DATAMODEL"] + "_context.json"
            Term.print_yellow("Rendering Context File  : [" + context_file_yaml + "]")
            Term.print_verbose("Rendering Context : [\n" + yaml.safe_dump(p_context, indent=2, default_flow_style=False, sort_keys=False) + "\n]")
            FileSystem.saveFileContent(yaml.safe_dump(p_context, indent=2, default_flow_style=False, sort_keys=False), context_file_yaml)
            FileSystem.saveFileContent(json.dumps(p_context, indent=3), context_file_json)
            for entity in p_context["ENTITIES"]:
                context_file_yaml = contexts_dir + os.sep + entity + "_context.yaml"
                context_file_json = contexts_dir + os.sep + entity + "_context.json"
                FileSystem.saveFileContent(yaml.safe_dump(p_context["ENTITIES"][entity], indent=2, default_flow_style=False, sort_keys=False), context_file_yaml)
                FileSystem.saveFileContent(json.dumps(p_context["ENTITIES"][entity], indent=3), context_file_json)
        # Rendering Multi Level Template Directory
        for template_file in os.listdir(p_templates_dir):
            if template_file.startswith("."+os.sep+".git"): continue
            if template_file.startswith("."+os.sep+".idea"): continue
            if template_file.startswith("."+os.sep+"venv"): continue
            if (os.path.isdir(p_templates_dir + os.sep + template_file)):
                if ("${ENTITY}" in template_file) :
                    # One SubDir per Entity
                    if ("ENTITIES" in p_context):
                        for entity in p_context["ENTITIES"] :
                            new_dir = p_artifacts_dir + os.sep + template_file.replace("${ENTITY}", entity)
                            Term.print_blue("Creating Dir : "+new_dir)
                            if not os.path.exists(new_dir): os.makedirs(new_dir)
                            CodeGenerator.renderDir(p_templates_dir + os.sep + template_file, p_include_dir, new_dir, p_context["ENTITIES"][entity], root=False, p_name=entity)
                else:
                    # A Single SubDir, Use Entity Context
                    new_dir = p_artifacts_dir + os.sep + template_file
                    Term.print_blue("Creating Dir : " + new_dir)
                    if not os.path.exists(new_dir): os.makedirs(new_dir)
                    CodeGenerator.renderDir(p_templates_dir + os.sep + template_file, p_include_dir, new_dir, p_context, root=False)
            else:
                if ("${ENTITY}" in template_file) :
                    # One File per Entity
                    if ("ENTITIES" in p_context):
                        # Use Entity Context
                        for entity in p_context["ENTITIES"]:
                            template_filename = p_templates_dir  + os.sep + template_file
                            rendered_filename = p_artifacts_dir + os.sep + template_file.replace("${ENTITY}", entity)
                            CodeGenerator.renderFile(template_filename, p_include_dir, rendered_filename, p_context["ENTITIES"][entity])
                    else:
                        # Use Global Context
                        template_filename = p_templates_dir  + os.sep + template_file
                        rendered_filename = p_artifacts_dir + os.sep + template_file.replace("${ENTITY}", p_name)
                        CodeGenerator.renderFile(template_filename, p_include_dir, rendered_filename, p_context)
                else:
                    # A Single File
                    template_filename = p_templates_dir + os.sep + template_file
                    rendered_filename = p_artifacts_dir + os.sep + template_file.replace("_Template", "").replace(".mako", "")
                    CodeGenerator.renderFile(template_filename, p_include_dir, rendered_filename, p_context)

    def renderOpenAPI(self, p_dataModel : DataModel):
        """ Create Openapi Yaml from Data Model """
        Term.print_yellow("> render Openapi Yaml")
        self.checkDir(forRendering=False)

        # Clean-up Entities to comply to OpenApI Components
        entities_yaml = copy.deepcopy(p_dataModel.entities)
        for entity in entities_yaml:
            if ("TABLE" in entities_yaml[entity])           : del entities_yaml[entity]["TABLE"]
            if ("RELATIONS" in entities_yaml[entity])       : del entities_yaml[entity]["RELATIONS"]
            if ("NAME" in entities_yaml[entity])            : del entities_yaml[entity]["NAME"]
            if ("KEY" in entities_yaml[entity])             : del entities_yaml[entity]["KEY"]
            if ("prepend" in entities_yaml[entity])         : del entities_yaml[entity]["prepend"]
            if ("append" in entities_yaml[entity])          : del entities_yaml[entity]["append"]
            if ("options" in entities_yaml[entity])         : del entities_yaml[entity]["options"]
            if ("PATH_OPERATION" in entities_yaml[entity])  : del entities_yaml[entity]["PATH_OPERATION"]
            if ("PATH_PARAMETERS" in entities_yaml[entity]) : del entities_yaml[entity]["PATH_PARAMETERS"]
            if ("PATH_PREFIX" in entities_yaml[entity])     : del entities_yaml[entity]["PATH_PREFIX"]
            if ("PATH"  in entities_yaml[entity])           : del entities_yaml[entity]["PATH"]
            if ("_ROOT" in entities_yaml[entity])           : del entities_yaml[entity]["_ROOT"]
            if ("name" in entities_yaml[entity])            : del entities_yaml[entity]["name"]
            if ("mandatory" in entities_yaml[entity])       : del entities_yaml[entity]["mandatory"]
            if ("properties" in entities_yaml[entity]) :
                if ("name" in entities_yaml[entity]["properties"])      : del entities_yaml[entity]["properties"]["name"]
                if ("mandatory" in entities_yaml[entity]["properties"]) : del entities_yaml[entity]["properties"]["mandatory"]
                if ("_ROOT" in entities_yaml[entity]["properties"])     : del entities_yaml[entity]["properties"]["_ROOT"]
                for prop in entities_yaml[entity]["properties"] :
                    if ("name" in entities_yaml[entity]["properties"][prop])      : del entities_yaml[entity]["properties"][prop]["name"]
                    if ("mandatory" in entities_yaml[entity]["properties"][prop]) : del entities_yaml[entity]["properties"][prop]["mandatory"]
                    if ("precision" in entities_yaml[entity]["properties"][prop]) : del entities_yaml[entity]["properties"][prop]["precision"]
                    if ("Schema" in entities_yaml[entity]["properties"][prop]):
                        DataModel.schema_parameters = DataModel.checkAsParameter(p_dataModel, entities_yaml[entity]["properties"][prop], entities_yaml[entity]["properties"][prop]["Schema"])
                    if ("Schema" in entities_yaml[entity]["properties"][prop])    : del entities_yaml[entity]["properties"][prop]["Schema"]
            if ("Schema" in entities_yaml[entity]) : del entities_yaml[entity]["Schema"]

        # Create OpenAPI Specification
        open_api_yaml = p_dataModel.openapi if p_dataModel.openapi else dict()

        # Create API Operations, add as Paths
        paths = Util.json_load("{" + Path.create_path(p_dataModel) + "}")
        open_api_yaml["paths"] = paths

        # Add Components
        if "components" in open_api_yaml:
            open_api_yaml["components"]["schemas"] = entities_yaml
        else:
            open_api_yaml["components"] = {"schemas": entities_yaml}

        # Add Parameters
        if "components" in open_api_yaml:
            open_api_yaml["components"]["parameters"] = p_dataModel.schema_parameters
        else:
            open_api_yaml["components"] = {"parameters": p_dataModel.schema_parameters}

        # Re-Order
        open_api = dict()
        if "openapi"      in open_api_yaml : open_api["openapi"]      = open_api_yaml["openapi"]
        if "info"         in open_api_yaml : open_api["info"]         = open_api_yaml["info"]
        if "externalDocs" in open_api_yaml : open_api["externalDocs"] = open_api_yaml["externalDocs"]
        if "servers"      in open_api_yaml : open_api["servers"]      = open_api_yaml["servers"]
        if "security"     in open_api_yaml : open_api["security"]     = open_api_yaml["security"]
        if "paths"        in open_api_yaml : open_api["paths"]        = open_api_yaml["paths"]
        if "components"   in open_api_yaml : open_api["components"]   = open_api_yaml["components"]

        # Apply Custom for Specific Models
        open_api_yaml = customOpenApi(self.model_location, open_api)

        Term.print_yellow("< render Openapi Yaml")
        Term.print_verbose(open_api_yaml)

        # Done - Save
        yaml_text = yaml.safe_dump(open_api_yaml, indent=2, default_flow_style=False, sort_keys=False)
        Term.print_verbose(yaml_text)
        yaml_file = self.artifacts_dir + os.sep + FileSystem.getBaseName(self.model_location) + openapi_yaml_suffix
        FileSystem.saveFileContent(yaml_text, yaml_file)
        Term.print_blue("Ready   : " + yaml_file)

        return open_api

    def renderArtifacts(self, p_dataModel : DataModel):
        """ Create Artifacts from Templates & Data Model """
        Term.print_yellow("> render Artifacts")
        self.checkDir(forRendering=True)

        p_dataModel.addContext(self.context_file)

        context = p_dataModel.context if p_dataModel.context else {}
        context["DATAMODEL"] = FileSystem.getBaseName(p_dataModel.name)
        context["ENTITIES"]  = p_dataModel.entities
        context["OPENAPI"]   = self.renderOpenAPI(p_dataModel)

        CodeGenerator.renderDir(self.templates_dir, self.includes_dir, self.artifacts_dir, context)

        Term.print_yellow("< render Artifacts")

    def generateEntitiesJsonSchema(self, p_dataModel: DataModel):
        """ Create Json Schema from Data Model Entities """

        # Create a Schema for each Entity
        # Create internal sub-objects References for Relationships to other Entities
        # Generate example objects for the entities schema
        Term.print_yellow("> generate Entities Json Schema")
        self.checkDir(forRendering=False)

        json_schemas   = {}
        example_objets = {}

        # Clean-up before generation
        entities_json = copy.deepcopy(p_dataModel.entities)
        for entity in entities_json:
            if ("TABLE" in entities_json[entity])           : del entities_json[entity]["TABLE"]
            if ("RELATIONS" in entities_json[entity])       : del entities_json[entity]["RELATIONS"]
            if ("NAME" in entities_json[entity])            : del entities_json[entity]["NAME"]
            if ("KEY" in entities_json[entity])             : del entities_json[entity]["KEY"]
            if ("prepend" in entities_json[entity])         : del entities_json[entity]["prepend"]
            if ("append" in entities_json[entity])          : del entities_json[entity]["append"]
            if ("options" in entities_json[entity])         : del entities_json[entity]["options"]
            if ("PATH_OPERATION" in entities_json[entity])  : del entities_json[entity]["PATH_OPERATION"]
            if ("PATH_PARAMETERS" in entities_json[entity]) : del entities_json[entity]["PATH_PARAMETERS"]
            if ("PATH_PREFIX" in entities_json[entity])     : del entities_json[entity]["PATH_PREFIX"]
            if ("PATH"  in entities_json[entity])           : del entities_json[entity]["PATH"]
            # if ("name" in entities_json[entity])          : del entities_json[entity]["name"]
            # if ("mandatory" in entities_json[entity])     : del entities_json[entity]["mandatory"]
            Term.print_verbose("> " + entity)
            for prop in entities_json[entity]["properties"] :
                Term.print_verbose(" - " + prop)
                # if ("name" in entities_json[entity]["properties"][prop])      : del entities_json[entity]["properties"][prop]["name"]
                # if ("mandatory" in entities_json[entity]["properties"][prop]) : del entities_json[entity]["properties"][prop]["mandatory"]
                continue

        for entity in entities_json:
            Term.print_yellow("["+entity+"]")
            Term.print_verbose(json.dumps(entities_json[entity], indent=3))
            Term.print_verbose(" - description : " + str(entities_json[entity]["description"]))
            Term.print_verbose(" - type        : " + str(entities_json[entity]["type"]))
            Term.print_verbose(" - example     : " + str(entities_json[entity]["example"]))
            Term.print_verbose(" - " + str(entities_json[entity]))

            example_obj = {}
            json_schema = {}
            object_desc = entities_json[entity]

            #  Object Details
            json_schema["$schema"]     = "http://json-schema.org/draft-07/schema"
            json_schema["$id"]         = json_schema_baseURI+entity+".json"
            json_schema["type"]        = "object"
            json_schema["title"]       = "Schema for " + entity
            json_schema["description"] = object_desc["description"]
            json_schema["default"]     = {}
            json_schema["examples"]    = []
            json_schema["required"]    = []
            json_schema["properties"]  = {}
            json_schema["additionalProperties"] = True

            # Object Properties Details
            for new_property in object_desc["properties"]:
                Term.print_verbose(" #> [" + str(object_desc["properties"][new_property]) + "]")
                Term.print_verbose(json.dumps(object_desc["properties"][new_property], indent=3))
                property_desc = object_desc["properties"][new_property]
                Term.print_verbose(" #>> " + str(property_desc))
                prop_schema = {}
                if ("$ref" in property_desc):
                    # Sub-object
                    Term.print_verbose("   #>> object        : " + str(property_desc["$ref"]))
                    item = re.sub("#/components/schemas/" , ""   , str(property_desc["$ref"]))
                    # prop_schema["$ref"]  = os.path.basename(p_dataModel.name) + "_" + item + "_schema.json"
                    prop_schema["$ref"]  = "#/$defs/" + item + ""
                    json_schema["properties"][item] = prop_schema
                elif ("items" in property_desc):
                    # Array of ...
                    if ("$ref" in property_desc["items"]):
                        # Array of Sub-objects
                        Term.print_verbose("   #>> Array objects : " + str(property_desc["items"]["$ref"]))
                        item = re.sub("#/components/schemas/", "", str(property_desc["items"]["$ref"]))
                        prop_schema["type"] = "array"
                        # prop_schema["items"] = {"$ref" : "" + os.path.basename(data_model) + "_" + item + "_schema.json"}
                        prop_schema["items"] = {"$ref" : "#/$defs/" + item + ""}
                        # json_schema["properties"][item+"s"] = prop_schema
                        json_schema["properties"][item] = prop_schema
                    else:
                        # Array of Basic Types
                        Term.print_verbose("   #>> Array Types : " + str(property_desc["items"]["type"]))
                        prop_schema["type"] = "array"
                        prop_schema["items"] = {"type" : property_desc["items"]["type"]}
                        if ("format" in property_desc["items"]):
                            prop_schema["items"]["format"] = property_desc["items"]["format"]
                        json_schema["properties"][new_property] = prop_schema
                else:
                    # Value Property
                    desc = property_desc["description"]
                    desc_schema = {}
                    if ("Schema" in property_desc):
                        desc_schema = property_desc["Schema"]

                    if ("name" not in property_desc) :
                        continue
                    if (property_desc["name"] != "_ROOT"):
                        example_obj[property_desc["name"]] = property_desc["example"] if ("example" in property_desc) else "noExample"
                    prop_schema["$id"]          = "#/properties/" + property_desc["name"]
                    prop_schema["type"]         = property_desc["type"]
                    prop_schema["title"]        = property_desc["name"]
                    prop_schema["description"]  = desc.strip()
                    prop_schema["default"]      = ""
                    prop_schema["examples"]     = [property_desc["example"] ,  property_desc["pattern"]]

                    prop_schema["validationScript"] = desc_schema["validationScript"] if ("validationScript" in desc_schema) else ""
                    prop_schema["possibleValues"]   = desc_schema["possibleValues"]   if ("possibleValues"   in desc_schema) else ["default_value", "value1" , "value2"]
                    prop_schema["defaultValue"]     = desc_schema["defaultValue"]     if ("defaultValue"     in desc_schema) else "default_value"
                    prop_schema["applicableTo"]     = desc_schema["applicableTo"]     if ("applicableTo"     in desc_schema) else ""
                    prop_schema["minCardinality"]   = desc_schema["minCardinality"]   if ("minCardinality"   in desc_schema) else 1
                    prop_schema["maxCardinality"]   = desc_schema["maxCardinality"]   if ("maxCardinality"   in desc_schema) else 1
                    prop_schema["validFor"]         = desc_schema["validFor"]         if ("validFor"         in desc_schema) else ""
                    prop_schema["format"]           = desc_schema["format"]           if ("format"           in desc_schema) else ""
                    prop_schema["examples"]         = desc_schema["examples"]         if ("examples"         in desc_schema) else prop_schema["examples"]
                    prop_schema["description"]      = desc_schema["description"]      if ("description"      in desc_schema) else desc
                    prop_schema["markdownDescription"] = desc_schema["markdownDescription"] if ("markdownDescription"  in desc_schema) else ""
                    prop_schema["valueSpecification"]  = desc_schema["valueSpecification"]  if ("valueSpecification"   in desc_schema) else {}
                    if (property_desc["name"] != "_ROOT"):
                        example_obj[property_desc["name"]] = prop_schema["defaultValue"]

                    Term.print_verbose("   #>> name        : " + str(property_desc["name"]))
                    Term.print_verbose("   #>> description : " + str(property_desc["description"]))
                    Term.print_verbose("   #>> type        : " + str(property_desc["type"]))
                    Term.print_verbose("   #>> format      : " + str(property_desc["format"]))
                    Term.print_verbose("   #>> example     : " + str(property_desc["example"]))
                    Term.print_verbose("   #>> pattern     : " + str(property_desc["pattern"]))
                    Term.print_verbose("   #>> format      : " + str(property_desc["format"]))
                    Term.print_verbose("   #>> mandatory   : " + str(property_desc["mandatory"]))
                    if (property_desc["mandatory"] and property_desc["mandatory"] == "y"):
                        json_schema["required"].append(property_desc["name"])
                    json_schema["properties"][property_desc["name"]] = prop_schema
            Term.print_verbose("Sample Object: "+str(example_obj))
            json_schema["examples"] = [example_obj]
            example_objets[entity]  = example_obj
            json_schemas[entity]    = json_schema

            # Add Required Relationship Sub Objects Schemas
            for link in p_dataModel.links:
                cardinality     = p_dataModel.links[link]["Cardinalite"]
                TableContenue   = p_dataModel.links[link]["TableContained"]
                TableContenante = p_dataModel.links[link]["TableContaining"]
                Term.print_verbose(TableContenante + " Contains [" + cardinality + "] " + TableContenue)
                if (entity == TableContenante) and (str(cardinality)  in ["1", "3", "OneToMore" , "OneToOne"]):
                    json_schema["required"].append(TableContenue)

        Term.print_verbose("json_schemas   : \n" + json.dumps(json_schemas,   indent=3))
        Term.print_verbose("example_objets : \n" + json.dumps(example_objets, indent=3))

        Term.print_yellow("< generate Entities Json Schema")

        return json_schemas

    def generatePathJsonSchema(self, p_dataModel: DataModel,  with_saving : bool = True):
        """ Create Json Schema for PATH Entity (used for API Validation) """

        # Create a Schema for each PATH Entity, and only for PATH Entities
        # Create References for Relationships to external Entities (which have a PATH)
        # Create Definitions for Relationships to internal Entities (which do not have a PATH)
        Term.print_yellow("> generate Path Json Schema")
        self.checkDir(forRendering=False)

        # Get a copy of the schema
        json_schemas  = self.generateEntitiesJsonSchema(p_dataModel)
        # Get a copy of the Entities
        entities_json = copy.deepcopy(p_dataModel.entities)

        # Clean-up Entities before schema generation
        for entity in entities_json:
            if ("TABLE" in entities_json[entity])     : del entities_json[entity]["TABLE"]
            if ("RELATIONS" in entities_json[entity]) : del entities_json[entity]["RELATIONS"]
            # if ("NAME" in entities_json[entity])      : del entities_json[entity]["NAME"]
            if ("KEY" in entities_json[entity])       : del entities_json[entity]["KEY"]
            if ("prepend" in entities_json[entity])   : del entities_json[entity]["prepend"]
            if ("append" in entities_json[entity])    : del entities_json[entity]["append"]
            if ("options" in entities_json[entity])   : del entities_json[entity]["options"]
            if ("PATH_OPERATION" in entities_json[entity])  : del entities_json[entity]["PATH_OPERATION"]
            if ("PATH_PARAMETERS" in entities_json[entity]) : del entities_json[entity]["PATH_PARAMETERS"]
            if ("PATH_PREFIX" in entities_json[entity])     : del entities_json[entity]["PATH_PREFIX"]
            if ("Schema" in entities_json[entity])          : del entities_json[entity]["Schema"]
            # if ("PATH"  in entities_json[entity]):           del entities_json[entity]["PATH"]
            # if ("name" in entities_json[entity]) :           del entities_json[entity]["name"]
            # if ("mandatory" in entities_json[entity]) :      del entities_json[entity]["mandatory"]
            if ("_ROOT" in entities_json[entity]["properties"]) :  del entities_json[entity]["properties"]["_ROOT"]
            Term.print_verbose("> " + entity)
            for prop in entities_json[entity]["properties"] :
                Term.print_verbose(" - " + prop)
                # if ("name" in entities_json[entity]["properties"][prop]):           del entities_json[entity]["properties"][prop]["name"]
                # if ("mandatory" in entities_json[entity]["properties"][prop]):      del entities_json[entity]["properties"][prop]["mandatory"]
                if ("Schema" in entities_json[entity]["properties"][prop]):     del entities_json[entity]["properties"][prop]["Schema"]
                continue

        # Generating Schema for _PATH Entities
        for entity in entities_json:
            entity_desc = entities_json[entity]
            if ("PATH" not in entity_desc) : continue

            entities_json[entity]["$schema"]     = "http://json-schema.org/draft-07/schema"
            entities_json[entity]["$id"]         = json_schema_baseURI+entity+".json"
            entities_json[entity]["type"]        = "object"
            entities_json[entity]["title"]       = "Schema for " + entity

            # Add $ref and $defs for Sub-Objects in Relationships
            for rel_entity in json_schemas:
                if (rel_entity == entity) : continue
                if (rel_entity not in p_dataModel.findTableContainedNames(entity)): continue
                # Entity contain relationship to this schema
                if ("PATH" in entities_json[rel_entity]):
                    # Entity is external - Create a Reference to its schema ($ref)
                    card = p_dataModel.findTableCardinality(entity, rel_entity)
                    if (card and (card == "OneToOne" or card == "ZeroToOne")):
                        entities_json[entity]["properties"][rel_entity]["-$ref"] = p_dataModel.name + "_" + rel_entity + schema_json_suffix
                        entities_json[entity]["properties"][rel_entity]["type"] = "string"
                    if (card and (card == "OneToMore" or card == "ZeroToMore")):
                        entities_json[entity]["properties"][rel_entity]["type"]  = "array"
                        entities_json[entity]["properties"][rel_entity]["items"] = {}
                        entities_json[entity]["properties"][rel_entity]["items"]["-$ref"] = p_dataModel.name + "_" + rel_entity + schema_json_suffix
                        entities_json[entity]["properties"][rel_entity]["items"]["type"] = "string"
                    pass
                else:
                    # Entity is internal - Add Definition to internal schema ($defs)
                    card = p_dataModel.findTableCardinality(entity, rel_entity)
                    if (card and (card == "OneToOne" or card == "ZeroToOne")):
                        entities_json[entity]["properties"][rel_entity]["$ref"] = "#/$defs/"+rel_entity
                        if ("$defs" not in entities_json[entity]):
                            entities_json[entity]["$defs"] = {}
                        entities_json[entity]["$defs"][rel_entity] = entities_json[rel_entity]
                    if (card and (card == "OneToMore" or card == "ZeroToMore")):
                        entities_json[entity]["properties"][rel_entity]["type"]  = "array"
                        entities_json[entity]["properties"][rel_entity]["items"] = {}
                        entities_json[entity]["properties"][rel_entity]["items"]["$ref"] = "#/$defs/"+rel_entity
                        if ("$defs" not in entities_json[entity]):
                            entities_json[entity]["$defs"] = {}
                        entities_json[entity]["$defs"][rel_entity] = entities_json[rel_entity]

        Term.print_yellow("< generate Path Json Schema")

        # Collecting Schema List for _PATH Entities & Saving
        schema_list = {}
        schema_dir = self.artifacts_dir + os.sep + "_Schemas"
        if (with_saving):
            # Create Directory
            FileSystem.createDir(schema_dir)
            Term.print_yellow("Schema  Dir : " + schema_dir)

        for entity in entities_json:
            entity_desc = entities_json[entity]
            if ("PATH" not in entity_desc): continue
            if ("PATH" in entities_json[entity]): del entities_json[entity]["PATH"]
            schema_list[entity] = entities_json[entity]
            if (with_saving):
                # Create Schema Files
                schema_file = schema_dir + os.sep + p_dataModel.name + "_" + entity + schema_json_suffix
                Term.print_yellow("Schema File : " + schema_file)
                FileSystem.saveFileContent(json.dumps(entities_json[entity], indent=3), schema_file)
                FileSystem.saveFileContent(yaml.safe_dump(entities_json[entity], indent=4, default_flow_style=False), schema_file.replace(".json", ".yaml"))

        Term.print_yellow("< generate Path Json Schema")
        return schema_list

    def generateRootJsonSchema(self, p_dataModel: DataModel, with_saving: bool = True):
        """ Create Json Schema from Data Model _ROOT Entity """

        # Json Schema Used for Configuration Server.
        # Create a Schema for each ROOT Entity, and only ROOT Entities
        Term.print_yellow("> generate Root Json Schema")
        self.checkDir(forRendering=False)

        json_schemas  = self.generateEntitiesJsonSchema(p_dataModel)
        root_count = 0
        root_list  = []
        for schema in json_schemas:
            if "properties" not in json_schemas[schema]: continue
            if ("_ROOT" in json_schemas[schema]["properties"]) :
                root_count = root_count + 1
                root_list.append(schema)
        Term.print_blue("- Roots : " + str(root_count) + " = " + str(root_list))
        if (root_count == 0) :
            Term.print_error("No _ROOT Entry")
            return None

        generated_schemas = {}
        json_schemas2 = copy.deepcopy(json_schemas)
        # Add $defs Sub-Objects Schemas & Generating Schemas
        for schema in json_schemas:
            if "properties" not in json_schemas[schema]: continue
            if ("_ROOT" in json_schemas2[schema]["properties"]) :
                # del json_schemas[schema]["properties"]["_ROOT"]
                json_schemas[schema]["$defs"] = {}
                for schema2 in json_schemas2:
                    if "_ROOT" in json_schemas2[schema2]["properties"] :
                        if "_ROOT" in json_schemas[schema2]["properties"]:
                            del json_schemas[schema2]["properties"]["_ROOT"]
                        continue
                    if ("$schema" in json_schemas[schema2]): del json_schemas[schema2]["$schema"]
                    if ("$id"     in json_schemas[schema2]): del json_schemas[schema2]["$id"]
                    json_schemas[schema]["$defs"][schema2] = json_schemas[schema2]
                if (root_count > 1) :
                    generated_schemas[schema] = json_schemas[schema]
                    # Generate Schema File - multiple _ROOT
                    schema_file = self.artifacts_dir + os.sep + p_dataModel.name + "_" + schema + schema_json_suffix
                    if (with_saving) :
                        FileSystem.saveFileContent(json.dumps(json_schemas[schema], indent=3), schema_file)
                        Term.print_blue("Schema Ready   : " + schema_file)
                else:
                    generated_schemas["ROOT"] = json_schemas[schema]
                    # Generate Schema File - assuming only one _ROOT
                    schema_file = self.artifacts_dir + os.sep + p_dataModel.name + schema_json_suffix
                    if (with_saving) :
                        FileSystem.saveFileContent(json.dumps(json_schemas[schema], indent=3), schema_file)
                        Term.print_blue("Schema Ready   : " + schema_file)

        Term.print_verbose("ROOT Schemas   : \n" + json.dumps(generated_schemas,   indent=3))

        Term.print_yellow("< generate Root Json Schema")

        return generated_schemas

    def configure_ANME_DataStore(self, p_dataModel: DataModel):
        """ Create Json Schema from Data Store _PATH Entity """

        Term.print_yellow("> configure ANME DataStore")
        # Generate  DataStore Schema (for _PATH Entities)
        self.generatePathJsonSchema(p_dataModel)

        # Creating DataStore and Loading Schema for _PATH Entities
        schema_list = {}
        entities_json = copy.deepcopy(p_dataModel.entities)
        schema_dir = self.artifacts_dir + os.sep + "_Schemas"
        Term.print_yellow("Schema Dir : " + schema_dir)
        for entity in entities_json:
            entity_desc = entities_json[entity]
            if ("PATH" not in entity_desc): continue
            api_target = entity_desc["PATH"]
            if ("PATH" in entities_json[entity]): del entities_json[entity]["PATH"]
            schema_file = schema_dir + os.sep + p_dataModel.name + "_" + entity + schema_json_suffix
            schema_list[entity] = entities_json[entity]
            curl = 'curl -X POST -H "Content-Type: application/json" -d @'+schema_file+' https://127.0.0.1:5000/datastore/'+api_target+'?create'
            Term.print_yellow(curl)
            req = "https://127.0.0.1:5000"+"/datastore/"+api_target+"s"+"?create"
            res = requests.post(req, json=FileSystem.loadFileData(schema_file), verify=False)
            Term.print_yellow(str(res))

        Term.print_yellow("< configure ANME DataStore")
        return schema_list


class TestCodeGen(unittest.TestCase):

    def setUp(self) -> None:
        Term.print_green("> Setup")
        Term.setVerbose()
        FileSystem.rmDir("NEF" + os.sep + "NEF_SCEF" + os.sep + "NEF_SCEF_artifacts", silent=True)
        Term.print_green("< Setup")

    def test_Validate_Schema(self):
        Term.print_green("> testValidateSchema")
        schema = {
            "items": {
                "anyOf": [
                    {"type": "integer", "minimum"  : 5},
                    {"type": "string",  "maxLength": 2}
                ]
            }
        }
        self.assertIsNone(validate(instance=[],                                       schema=schema))
        self.assertIsNone(validate(instance=[5],                                      schema=schema))
        self.assertIsNone(validate(instance=["fo"],                                   schema=schema))
        self.assertIsNone(validate(instance=["fo", 5],                                schema=schema))
        self.assertIsNone(validate(instance=[5, "fo"],                                schema=schema))
        self.assertRaises(exceptions.ValidationError, validate, instance=[True],      schema=schema)
        self.assertRaises(exceptions.ValidationError, validate, instance=["fos", 5],  schema=schema)
        self.assertRaises(exceptions.ValidationError, validate, instance=[5, "fos"],  schema=schema)
        self.assertRaises(exceptions.ValidationError, validate, instance=["fo", 3],   schema=schema)
        self.assertRaises(exceptions.ValidationError, validate, instance=[3, "fo"],   schema=schema)
        self.assertRaises(exceptions.ValidationError, validate, instance=[{}, 3, "foo"],  schema=schema)
        # self.assertRaises(exceptions.ValidationError, validate, instance={},          schema=schema)
        # self.assertRaises(exceptions.ValidationError, validate, instance={"name": "Eggs", "price": 34.99},          schema=schema)
        Term.print_green("< testValidateSchema")

    def test_Architect_Parser(self):
        Term.print_red("> test_Architect_Parser")
        Term.setVerbose(False)

        arch = Architect("NA" + os.sep + "API_Data_Model_Sample" + os.sep + "API_Data_Model_Sample")

        self.assertIsNone(arch.architect_file)
        self.assertEqual(arch.dataModel.location, "NEF\API_Data_Model_Sample\API_Data_Model_Sample")
        self.assertEqual(arch.dataModel.name,     "API_Data_Model_Sample")
        dataModel = arch.readArchitect()
        self.assertIsNone(dataModel)

        arch = Architect("NEF" + os.sep + "API_Data_Model_Sample" + os.sep + "API_Data_Model_Sample")
        self.assertEqual(arch.architect_file, "NEF" + os.sep + "API_Data_Model_Sample" + os.sep + "API_Data_Model_Sample")
        self.assertEqual(arch.dataModel.location, "NEF" + os.sep + "API_Data_Model_Sample" + os.sep + "API_Data_Model_Sample")
        self.assertEqual(arch.dataModel.name, "API_Data_Model_Sample")
        dataModel = arch.readArchitect()
        self.assertIsNotNone(dataModel)

        flat = Util.flatten(dataModel.entities)
        Term.print_verbose(json.dumps(flat, indent=3))
        Term.gen_assert(flat)

        self.assertEqual(dataModel.entities["API"]["NAME"], "API")
        self.assertEqual(dataModel.entities["API"]["properties"]["API_Name"]["Schema"]["minCardinality"], 1)
        self.assertEqual(dataModel.entities["API"]["RELATIONS"]["API_API_Details"]["Cardinalite"], "OneToOne")
        self.assertEqual(dataModel.context["PATH_PREFIX"], "/datastore")
        self.assertEqual(dataModel.openapi["tags"][0]["name"], "NEF")

        self.assertEqual(flat["TestRoot2/properties/_ROOT/example"], "_ROOT")
        self.assertEqual(flat["TestRoot2/properties/Version/Schema/filter"], False)
        self.assertEqual(flat["TestRoot2/properties/API_Documentation/Schema/filter"], False)
        self.assertEqual(flat["TestRoot2/properties/API_Description/Schema/possibleValues/1"], "value1")
        self.assertEqual(flat["TestRoot2/properties/YAML/description"], "API YAML - EndPoints")

    def test_CodeGenerator_generateEntitiesJsonSchema(self):
        Term.setVerbose(False)
        Term.print_red("> test generateEntitiesJsonSchema")
        FileSystem.rmDir("NEF" + os.sep + "API_Data_Model_Sample" + os.sep + "API_Data_Model_Sample_artifacts")
        dataModel = Architect(default_data_model).readArchitect()
        codeGen   = CodeGenerator(default_data_model)
        schemas   = codeGen.generateEntitiesJsonSchema(dataModel)

        flat = Util.flatten(schemas)
        Term.print_verbose(json.dumps(flat, indent=3))

        # Check Schema Generation
        Term.gen_assert(schemas)
        self.assertIn("API", schemas)
        self.assertEqual(9, len(schemas.keys()))
        self.assertEqual(schemas["API"]["properties"]["API_Description"]["title"], "API_Description")

    def test_CodeGenerator_generatePathJsonSchema(self):
        Term.setVerbose(False)
        Term.print_red("> test generatePathJsonSchema")
        FileSystem.rmDir("NEF" + os.sep + "API_Data_Model_Sample" + os.sep + "API_Data_Model_Sample_artifacts")
        dataModel = Architect(default_data_model).readArchitect()
        codeGen   = CodeGenerator(default_data_model)
        schemas   = codeGen.generatePathJsonSchema(dataModel)

        flat = Util.flatten(schemas)
        Term.print_verbose(json.dumps(flat, indent=3))

        # Check File Generation
        self.assertTrue(FileSystem.isFileExist(codeGen.artifacts_dir + os.sep + "_Schemas" + os.sep + "API_Data_Model_Sample_API_Article_Schema.json"))
        self.assertTrue(FileSystem.isFileExist(codeGen.artifacts_dir + os.sep + "_Schemas" + os.sep + "API_Data_Model_Sample_API_Category_Schema.json"))

        # Check Schema Generation
        Term.gen_assert(schemas)
        self.assertIn("API", schemas)
        self.assertEqual(flat["API_Article/properties/ArticlePage/mandatory"], "y")
        self.assertNotIn("API/properties/_ROOT/name", flat)
        self.assertEqual(schemas["API"]["properties"]["API_Description"]["name"], "API_Description")

    def test_CodeGenerator_generateRootJsonSchema(self):
        Term.setVerbose(False)
        Term.print_red("> test generateRootJsonSchema")
        FileSystem.rmDir("NEF" + os.sep + "API_Data_Model_Sample" + os.sep + "API_Data_Model_Sample_artifacts")
        dataModel = Architect(default_data_model).readArchitect()
        codeGen   = CodeGenerator(default_data_model)
        schemas   = codeGen.generateRootJsonSchema(dataModel)

        flat = Util.flatten(schemas)
        Term.print_verbose(json.dumps(flat, indent=3))

        # Check File Generation
        self.assertTrue(FileSystem.isFileExist(codeGen.artifacts_dir + os.sep + "API_Data_Model_Sample_API_Schema.json"))
        self.assertTrue(FileSystem.isFileExist(codeGen.artifacts_dir + os.sep + "API_Data_Model_Sample_TestRoot2_Schema.json"))

        # Check Schema Generation
        # Term.gen_assert(schemas)
        self.assertEqual(flat["API/required/3"], "API_Name")
        self.assertEqual(flat["API/$defs/UsagePolicy/title"], "Schema for UsagePolicy")
        self.assertEqual(flat["API/properties/API_Description/title"], "API_Description")

    def test_CodeGenerator_OpenAPI(self):
        Term.setVerbose(False)
        Term.print_red("> test CodeGenerator renderOpenAPI")
        FileSystem.rmDir("NEF" + os.sep + "API_Data_Model_Sample" + os.sep + "API_Data_Model_Sample_artifacts")
        dataModel = Architect(default_data_model).readArchitect()
        codeGen   = CodeGenerator(default_data_model)
        open_api  = codeGen.renderOpenAPI(dataModel)

        flat = Util.flatten(open_api)
        Term.print_verbose(json.dumps(flat, indent=3))
        Term.gen_assert(open_api)

        self.assertTrue(FileSystem.isFileExist("NEF" + os.sep + "API_Data_Model_Sample" + os.sep + "API_Data_Model_Sample_artifacts" + os.sep + "API_Data_Model_Sample" + openapi_yaml_suffix))

        self.assertEqual(flat["openapi"], "3.0.2")
        self.assertEqual(flat["servers/0/url"], "{apiRoot}/nef-services-catalog-service/22-03")
        self.assertEqual(flat["servers/0/description"], "Amdocs NEF Release 22-03")
        self.assertEqual(flat["paths//datastore/APIs/post/requestBody/description"], "A new `TestRoot2` to be created.")
        self.assertEqual(flat["paths//datastore/APIs/post/requestBody/content/application/json/schema/$ref"], "#/components/schemas/TestRoot2")
        self.assertEqual(flat["paths//datastore/API_Bundles/get/parameters/1/description"], "Pagination Offset")
        self.assertEqual(flat["paths//datastore/collections/get/parameters/0/description"], "Pagination Limit")
        self.assertEqual(flat["components/schemas/API/properties/API_Documentation/description"], "No Description for API Documentation ")
        self.assertEqual(flat["components/schemas/API/required/6"], "API_Documentation")
        self.assertEqual(flat["components/schemas/UsagePolicy/properties/VariableType/example"], "VariableType")

    def test_CodeGenerator_Artifacts(self):
        Term.setVerbose(False)
        Term.print_red("> test CodeGenerator renderArtifacts")
        FileSystem.rmDir("NEF" + os.sep + "API_Data_Model_Sample" + os.sep + "API_Data_Model_Sample_artifacts")
        dataModel = Architect(default_data_model).readArchitect()
        codeGen   = CodeGenerator(default_data_model)
        codeGen.renderArtifacts(dataModel)

        # Check File Generation
        self.assertTrue(FileSystem.isFileExist(codeGen.artifacts_dir + os.sep + "_Contexts" + os.sep + "API_Data_Model_Sample_context.json"))
        self.assertTrue(FileSystem.isFileExist(codeGen.artifacts_dir + os.sep + "_Contexts" + os.sep + "API_Data_Model_Sample_context.yaml"))
        self.assertTrue(FileSystem.isFileExist(codeGen.artifacts_dir + os.sep + "ServicesCatalog.sql"))
        self.assertIn("TT", FileSystem.loadFileContent(codeGen.artifacts_dir + os.sep+"ServicesCatalog.sql"))

        # Check Generation Context
        context = FileSystem.loadFileData(codeGen.artifacts_dir + os.sep + "_Contexts" + os.sep + "API_Data_Model_Sample_context.json")

        flat = Util.flatten(context)
        Term.print_verbose(json.dumps(flat, indent=3))

        Term.gen_assert(context)
        self.assertEqual(flat["PATH_PREFIX"], "/datastore")
        self.assertEqual(flat["DATAMODEL"], "API_Data_Model_Sample")
        self.assertEqual(flat["ENTITIES/API/name"], "API")
        self.assertEqual(flat["ENTITIES/API/type"], "object")
        self.assertEqual(flat["ENTITIES/UsagePolicy/type"], "object")
        self.assertEqual(flat["OPENAPI/paths//datastore/API_Bundles/get/description"], "Gets a list of all `API_Bundle` entities.")
        self.assertEqual(flat["OPENAPI/paths//datastore/APIs/{id}/put/responses/202/description"], "Successful response.")

    def test_CodeGenerator_configure_ANME_DataStore(self):
        Term.setVerbose(False)
        Term.print_red("> test configure_ANME_DataStore")
        FileSystem.rmDir("NEF" + os.sep + "API_Data_Model_Sample" + os.sep + "API_Data_Model_Sample_artifacts")
        dataModel = Architect(default_data_model).readArchitect()
        codeGen   = CodeGenerator(default_data_model)
        schemas   = codeGen.configure_ANME_DataStore(dataModel)

        flat = Util.flatten(schemas)
        Term.print_verbose(json.dumps(flat, indent=3))

        # Check Schema Generation
        Term.gen_assert(schemas)
        self.assertEqual(flat["API/required/3"], "API_Name")
        self.assertEqual(flat["API/properties/API_Category/description"], "API_API_Category")
        self.assertEqual(flat["API_Bundle/properties/id/mandatory"], "y")


class TestArchitectModels(unittest.TestCase):

    def setUp(self) -> None:
        Term.print_green("> Setup")
        Term.setVerbose(False)
        Term.print_green("< Setup")

    def testGenerate_NEF_Configuration_Service_Schema(self):
        Term.print_green("> testGenerate_NEF_Configuration_Service_Schema")
        data_model_location = "NEF"+os.sep+"NEF_Configuration"+os.sep+"NEF_Configuration"
        generate({"WHAT" : "config", "DATA_MODEL" : data_model_location}, clean_artifacts=True)

    def testGenerate_NEF_MarketPlace_DataService(self):
        Term.print_green("> testGenerate_NEF_MarketPlace_DataService")
        data_model_location = "NEF"+os.sep+"NEF_MarketPlace"+os.sep+"NEF_MarketPlace_DataModel"
        generate({"WHAT" : "schema openapi render", "DATA_MODEL" : data_model_location}, clean_artifacts=True)

    def testGenerate_NEF_Catalog_DataService(self):
        Term.print_green("> testGenerate_NEF_Catalog_DataService")
        data_model_location = "NEF"+os.sep+"NEF_Catalog"+os.sep+"NEF_Catalog_DataModel"
        generate({"WHAT" : "schema openapi render", "DATA_MODEL" : data_model_location}, clean_artifacts=True)

    def testGenerate_NEF_ApplicationUserProfile_DataService(self):
        Term.print_green("> testGenerate_NEF_ApplicationUserProfile_DataService")
        data_model_location = "NEF"+os.sep+"NEF_ApplicationUserProfile"+os.sep+"NEF_ApplicationUserProfile_DataModel"
        generate({"WHAT" : "schema openapi render", "DATA_MODEL" : data_model_location}, clean_artifacts=True)

    def testGenerate_NEF_API_Subscription_DataService(self):
        Term.print_green("> testGenerate_NEF_API_Subscription_DataService")
        data_model_location = "NEF" + os.sep + "NEF_API_Subscription" + os.sep + "NEF_API_Subscription_Procedure"
        context_file        = data_model_location + "_context.yaml"
        includes_dir        = default_include_dir
        generate({"WHAT" : "schema openapi", "DATA_MODEL" : data_model_location, "CONTEXT_FILE" : context_file, "INCLUDES_DIR" : includes_dir}, clean_artifacts=True)

    def testGenerate_SCEF_Service(self):
        Term.print_green("> testGenerate_SCEF_Service")
        data_model_location = "NEF" + os.sep + "NEF_SCEF" + os.sep+"NEF_SCEF"
        context_file        = None
        includes_dir        = None
        generate({"WHAT" : "openapi", "DATA_MODEL" : data_model_location,
                  "INCLUDES_DIR"    : includes_dir , "CONTEXT_FILE" : context_file}, clean_artifacts=True)

    def testGenerate_NEF_API_Data_Model_Sample(self):
        Term.print_green("> testGenerate_NEF_API_Data_Model_Sample")
        data_model_location = "NEF" + os.sep + "API_Data_Model_Sample" + os.sep + "API_Data_Model_Sample"
        FileSystem.rmDir(data_model_location + artifacts_dir_suffix)
        context_file  = data_model_location + "_context.json"
        templates_dir = data_model_location + templates_dir_suffix
        artifacts_dir = data_model_location + artifacts_dir_suffix
        includes_dir  = default_include_dir
        generate({"WHAT" : "openapi schema render config", "DATA_MODEL" : data_model_location,
                  "TEMPLATES_DIR" : templates_dir, "INCLUDES_DIR" : includes_dir,
                  "ARTIFACTS_DIR" : artifacts_dir, "CONTEXT_FILE" : context_file},
                  clean_artifacts=True)

        # Check Generated File Existence
        self.assertTrue(FileSystem.isFileExist(artifacts_dir + os.sep + "API_Data_Model_Sample_API.yaml"))
        self.assertTrue(FileSystem.isFileExist(artifacts_dir + os.sep + "_Contexts" + os.sep + "API_Data_Model_Sample_context.json"))
        self.assertTrue(FileSystem.isFileExist(artifacts_dir + os.sep + "_Contexts" + os.sep + "API_Data_Model_Sample_context.yaml"))
        self.assertTrue(FileSystem.isFileExist(artifacts_dir + os.sep + "ServicesCatalog.sql"))

        # Check Generated File Content
        self.assertIn("TT", FileSystem.loadFileContent(artifacts_dir + os.sep+"ServicesCatalog.sql"))

        # Check Code Generation Context
        context = Util.flatten(FileSystem.loadFileData(artifacts_dir + os.sep + "_Contexts" + os.sep + "API_Data_Model_Sample_context.json"))
        Term.gen_assert(context)
        flat = Util.flatten(context)
        self.assertEqual(flat["DD"], "Context")
        self.assertEqual(flat["ENTITIES/API/name"], "API")
        self.assertEqual(flat["ENTITIES/API/properties/id/Schema/defaultValue"], "noDefaultalue")


def generate(cl_args : dict, clean_artifacts : bool = False):

    what = cl_args["WHAT"]                      if ("DATA_MODEL"    in cl_args) else ""
    data_model_location = cl_args["DATA_MODEL"] if ("DATA_MODEL"    in cl_args) else None
    templates_dir = cl_args["TEMPLATES_DIR"]    if ("TEMPLATES_DIR" in cl_args) else None
    includes_dir  = cl_args["INCLUDES_DIR"]     if ("INCLUDES_DIR"  in cl_args) else None
    artifacts_dir = cl_args["ARTIFACTS_DIR"]    if ("ARTIFACTS_DIR" in cl_args) else None
    context_file  = cl_args["CONTEXT_FILE"]     if ("CONTEXT_FILE"  in cl_args) else None

    # Check Command Line Arguments
    if (data_model_location) :
        data_model_location = str(data_model_location).replace(".architect" , "")

    if (data_model_location) and FileSystem.isFileExist(data_model_location + ".architect"):
        data_model = data_model_location
        Term.print_blue("Model Location : "+data_model+".architect")
    else:
        Term.print_error("Model not found : "+str(data_model_location))
        Term.print_yellow(read_command_line_args([], p_usage=True))
        quit()

    if (templates_dir) and (not FileSystem.isDirExist(templates_dir)):
        FileSystem.createDir(templates_dir)
    if (templates_dir) and (not FileSystem.isDirExist(templates_dir)):
        Term.print_error("Templates Dir not found : " + str(templates_dir))
        Term.print_yellow(read_command_line_args([], p_usage=True))
        quit()
    # templates_dir = templates_dir if templates_dir else data_model_location + templates_dir_suffix
    Term.print_yellow("Templates Dir  : " + str(templates_dir))

    if (includes_dir) and (not FileSystem.isDirExist(includes_dir)):
        FileSystem.createDir(includes_dir)
    if (includes_dir) and (not FileSystem.isDirExist(includes_dir)):
        Term.print_error("Include Dir not found : " + str(includes_dir))
        Term.print_yellow(read_command_line_args([], p_usage=True))
        quit()
    # includes_dir = includes_dir if includes_dir else default_include_dir
    Term.print_yellow("Includes Dir   : " + str(includes_dir))

    if (clean_artifacts):
        if (artifacts_dir) and (FileSystem.isDirExist(artifacts_dir)):
            FileSystem.rmDir(artifacts_dir)
        elif FileSystem.isDirExist(data_model_location + artifacts_dir_suffix):
            FileSystem.rmDir(data_model_location + artifacts_dir_suffix)

    if (artifacts_dir) and (not FileSystem.isDirExist(artifacts_dir)):
        FileSystem.createDir(artifacts_dir)
    if (artifacts_dir) and (not FileSystem.isDirExist(artifacts_dir)):
        Term.print_error("Artifacts Dir not found : " + str(artifacts_dir))
        Term.print_yellow(read_command_line_args([], p_usage=True))
        quit()
    artifacts_dir = artifacts_dir if artifacts_dir else data_model_location + artifacts_dir_suffix
    Term.print_yellow("Artifacts Dir  : " + str(artifacts_dir))

    if (context_file) and (not FileSystem.isFileExist(context_file)):
        Term.print_error("Context File not found : " + str(context_file))
        Term.print_yellow(read_command_line_args([], p_usage=True))
        quit()
    Term.print_yellow("Context File   : "+str(context_file))

    Term.print_yellow("Generating     : " + str(cl_args["WHAT"]))
    Term.print_blue("Model          : " + data_model_location + ".architect")

    # Backup architect file
    backup_dir  = FileSystem.getDirName(data_model_location) + os.sep + "Archive"
    backup_file = FileSystem.getBaseName(data_model_location) + "_" + datetime.datetime.now().strftime("%y%m%d-%H%M%S") + ".architect"
    FileSystem.createDir(backup_dir)
    shutil.copyfile(data_model_location + ".architect", backup_dir + os.sep + backup_file)
    Term.print_blue("Backup         : " + backup_dir + os.sep + backup_file)

    # Read architect file
    Term.print_blue("Reading        : " + data_model_location + ".architect")
    dataModel = Architect(data_model_location).readArchitect()

    # Configure CodeGenerator
    codeGen   = CodeGenerator(data_model_location)
    codeGen.configureDir(data_model_location, templates_dir, includes_dir, artifacts_dir, context_file)

    # Generate ...
    if ("config" in what.lower()):
        codeGen.generateRootJsonSchema(dataModel)
    if ("schema" in what.lower()):
        codeGen.generatePathJsonSchema(dataModel)
    if (("openapi" in what.lower()) or ("yaml" in what.lower())):
        codeGen.renderOpenAPI(dataModel)
    if (("render" in what.lower()) or ("artifacts" in what.lower())):
        codeGen.renderArtifacts(dataModel)
    if (("anme" in what.lower()) or ("datastore" in what.lower())):
        codeGen.configure_ANME_DataStore(dataModel)


# This method to alter/customize Generated OpenAPI, when needed.
def customOpenApi(p_model : str, open_api : dict) -> dict:

    Term.print_yellow("> OpenApi Customizations on : " + p_model)

    # Some Custom for NEF_Configuration_Service
    if ("NEF_Configuration_Service" in p_model) :
        Term.print_yellow("> Customs for NEF_Configuration_Service")
        for path in open_api["paths"] :
            for op in open_api["paths"][path]:
                if (op == "get") :
                    del open_api["paths"][path][op]["responses"]["200"]["content"]["application/json"]["schema"]
                if (op == "post"):
                    open_api["paths"][path][op]["requestBody"]["content"]["application/json"]["schema"]["$ref"] = "#/components/schemas/Configuration"
                    # open_api["paths"][path][op]["responses"]["202"]["content"]["application/json"]["schema"]
                if (op == "patch"):
                    del open_api["paths"][path][op]["requestBody"]
                    # del open_api["paths"][path][op]["requestBody"]["content"]["application/json"]["schema"]
                    # del open_api["paths"][path][op]["responses"]["202"]["content"]["application/json"]["schema"]

    # Some Custom for NEF_Configuration_Service
    if ("NEF_SCEF" in p_model) :
        Term.print_yellow("> Customs for NEF_SCEF")
        # open_api["paths"]["/notify/message"] = open_api["paths"]["/notify/messages"]
        # del open_api["paths"]["/notify/messages"]
        # open_api["paths"]["/request/message"] = open_api["paths"]["/request/messages"]
        # del open_api["paths"]["/request/messages"]
        for path in open_api["paths"] :
            if ("/request/messages" == path):
                del open_api["paths"]["/request/messages"]["parameters"]
                open_api["paths"]["/request/messages"]["post"]["responses"]["202"]["content"]["application/json"]["schema"]["$ref"] = "#/components/schemas/Response"
                open_api["paths"]["/request/messages"]["description"] = "Submit Message Request"
                open_api["paths"]["/request/messages"]["summary"] = "Submit Message Request"
            if ("/notify/messages" == path):
                del open_api["paths"]["/notify/messages"]["parameters"]
                open_api["paths"]["/notify/messages"]["post"]["responses"]["202"]["content"]["application/json"]["schema"]["$ref"] = "#/components/schemas/Response"
                open_api["paths"]["/notify/messages"]["description"] = "Transmit a Notification"
                open_api["paths"]["/notify/messages"]["summary"] = "Transmit a Notification"
        del open_api["components"]["schemas"]["AVP"]["properties"]["Value"]["type"]
        del open_api["components"]["schemas"]["AVP"]["properties"]["AVP"]
        open_api["components"]["schemas"]["AVP"]["properties"]["Value"]["oneOf"] = [{"type" : "integer"} ,
                                                                                    {"type" : "string"},
                                                                                    {"type" : "boolean"},
                                                                                    {"type" : "number"},
                                                                                    {"type" : "array" ,
                                                                          "items" : {"$ref" : "#/components/schemas/AVP"}}]

    return open_api


def read_command_line_args(argv, p_usage : bool = False) -> Union[str, dict, None]:

    Term.print_yellow("Command Line Arguments : " + str(argv))

    usage = """
Usage: -h -v -r -y -o -g -s -d -m <model> -t <templates_dir> -a <artifacts_dir> -i <includes_dir> -c <context_file>  
       -m --model    <file> : Generate for model <model_file>.architect                 
       -t --templates <dir> : Use <dir> as templates dir                      
       -i --include   <dir> : Use <dir> as include template dir                      
       -a --artifacts <dir> : Use <dir> as artifacts dir                      
       -c --context  <file> : Context File for rendering <context_file>.[json|yaml]                 
       -r --render      : CodeGenerator <model_file>_template dir into <model_file>_artifacts dir
       -y --yaml        : Generate OpenAPI Yaml <model_file>_artifacts dir
       -o --openapi     : Generate OpenAPI Yaml <model_file>_artifacts dir
       -s --schema      : Generate PATH JSON Schema <model_file>_artifacts/_Schemas dir
       -g --config      : Generate ROOT JSON Schema <model_file>_artifacts/_Schemas dir
       -d --datastore   : Generate and provision ANME Datastore               
       -v --verbose     : Verbose     
       -h --help        : Usage help 
"""

    if (p_usage) :
        return usage

    cl_args = dict()
    cl_args["WHAT"]          = ""
    cl_args["DATA_MODEL"]    = None
    cl_args["TEMPLATES_DIR"] = None
    cl_args["INCLUDES_DIR"]  = None
    cl_args["ARTIFACTS_DIR"] = None
    cl_args["CONTEXT_FILE"]  = None

    try:
        opts, args = getopt.getopt(argv, "hvgrydosm:t:a:i:c:", ["verbose", "datastore", "schema" , "openapi" , "yaml" , "render" , "config" , "include=", "model=", "templates=", "artifacts=", "context="])
    except getopt.GetoptError as e:
        Term.print_yellow("GetoptError : " + str(e))
        print(usage)
        sys.exit(2)
    for opt, arg in opts:
        if opt.lower() in ("-h", "--help"):
            print(usage)
            quit()
        elif opt.lower() in ("-v", "-verbose"):
            Term.setVerbose(True)
            continue
        elif opt.lower() in ("-o", "-openapi"):
            cl_args["WHAT"] = cl_args["WHAT"] + "openapi "
            continue
        elif opt.lower() in ("-y", "-yaml"):
            cl_args["WHAT"] = cl_args["WHAT"] + "openapi "
            continue
        elif opt.lower() in ("-g", "-config"):
            cl_args["WHAT"] = cl_args["WHAT"] + "config "
            continue
        elif opt.lower() in ("-s", "-schema"):
            cl_args["WHAT"] = cl_args["WHAT"] + "schema "
            continue
        elif opt.lower() in ("-d", "-datastore"):
            cl_args["WHAT"] = cl_args["WHAT"] + "anme "
            continue
        elif opt.lower() in ("-r", "-render"):
            cl_args["WHAT"] = cl_args["WHAT"] + "render "
            continue
        elif opt.lower() in ("-m", "-model"):
            cl_args["DATA_MODEL"] = arg
            continue
        elif opt.lower() in ("-t", "-templates"):
            cl_args["TEMPLATES_DIR"] = arg
            continue
        elif opt.lower() in ("-i", "-include"):
            cl_args["INCLUDES_DIR"] = arg
            continue
        elif opt.lower() in ("-a", "-artifacts"):
            cl_args["ARTIFACTS_DIR"] = arg
            continue
        elif opt.lower() in ("-c", "-context"):
            cl_args["CONTEXT_FILE"] = arg
            continue
    Term.print_yellow("Command Line Args : \n" + json.dumps(cl_args, indent=3))
    return cl_args

if __name__ == '__main__':

    args = read_command_line_args(argv=sys.argv[1:])
    generate(args)
