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
from jsonschema import validate
import logging
import datetime
from termcolor import colored
import unidecode
import glob
from mako.template import Template
import mako.runtime
import dicttoxml
import markdown
import platform, socket, shutil, errno, getopt
from jsonpath_ng import jsonpath, parse

timestamp = datetime.datetime.now().strftime("%y%m%d-%H%M%S")
logFile   = "."+os.sep+"sql_architect_to_openapi.log"
logging.basicConfig(filename=logFile, filemode='w', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)

default_data_model = "API_Data_Model_Sample"

input_dir_suffix  = "_templates"
output_dir_suffix = "_artifacts"

data_model  = "API_Data_Model_Sample"
input_dir   = "." + os.sep + default_data_model + input_dir_suffix
output_dir  = "." + os.sep + default_data_model + output_dir_suffix

###
### Print
###

VERBOSE = False


class Term:

    @staticmethod
    def flatten(pDict : dict, sep: str = ":") -> dict:
        newDict = {}
        for key, value in pDict.items():
            if type(value) == dict:
                fDict = {sep.join([key, _key]): _value for _key, _value in Term.flatten(value, sep).items()}
                newDict.update(fDict)
            elif type(value) == list:
                i = 0
                for el in value:
                    if type(el) == dict:
                        fDict = {sep.join([key, str(i), _key]): _value for _key, _value in Term.flatten(el, sep).items()}
                        newDict.update(fDict)
                    else:
                        # fDict = { key + str(i) , str(el)}
                        # newDict.update(fDict)
                        newDict[key + sep + str(i)] = str(el)
                        pass
                    i = i + 1
            else:
                newDict[key] = value
        return newDict

    @staticmethod
    def setVerbose(verbose : bool = True):
        global VERBOSE
        VERBOSE = verbose

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
        global VERBOSE
        if (VERBOSE):
            print(colored(text, "magenta"))
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
        global VERBOSE
        if (VERBOSE):
            print(colored(text, "cyan"))
        logging.warning(text)
        if (exception):
            print(colored(exception, "red"))
            logging.warning(exception)

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
        flat_dict = Term.flatten(tree_dict, ":")
        for key in flat_dict.keys() :
            print(colored(key, "blue") + " : " + colored(flat_dict[key], "yellow"))

    @staticmethod
    def json_load(text : str ) -> dict:
        try:
            return json.loads(text)
        except Exception as ex :
            Term.print_error("Error with decoding JSON :")
            Term.print_error(text)
            Term.print_error(str(ex))
            raise ex

    @staticmethod
    def yaml_load(text : str ) -> dict:
        try:
            return yaml.safe_load(text)
        except Exception as ex :
            Term.print_error("Error with decoding YAML :")
            Term.print_error(text)
            Term.print_error(str(ex))
            raise ex

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
        except:
            return False

    @staticmethod
    def is_DirExist(filename):
        try:
            return os.path.isdir(filename)
        except:
            return False

    @staticmethod
    def createDir(dirName):
        # Create target directory & all intermediate directories if don't exists
        if not os.path.exists(dirName):
            os.makedirs(dirName)

    @staticmethod
    def remove_extension(filename):
        return filename.replace(FileSystem.get_extension(filename), "")

    @staticmethod
    def safeListFiles(dir: str = ".", file_ext: str = "", keepExt = False) -> list:
        myList = list()
        for f in glob.glob(dir+os.sep+"*"+file_ext):
            f = f.replace(dir+os.sep, "")
            if (keepExt is False):
                f = FileSystem.remove_extension(f)
            myList.append(f)
        return myList

    @staticmethod
    def loadFileContent(file_name: str) -> str:
        if (not FileSystem.is_FileExist(file_name)):
            Term.print_error("File not Found : " + file_name)
            return None
        with open(file_name, "r") as file:
            content = file.read()
            file.close()
        return content

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

    @staticmethod
    def render(p_template_filename : str, p_rendered_filename, context: dict):
        Term.print_blue("Rendering : [" + p_template_filename )
        Term.print_blue("   > into : [" + p_rendered_filename + "]")
        template_string = FileSystem.loadFileContent(p_template_filename)
        # dos2unix magic !
        "\n".join(template_string.splitlines())
        # Rendering Template
        mako.runtime.UNDEFINED = 'MISSING_IN_CONTEXT'
        rendered_template = Template(template_string).render(**context)
        rendered_template = FileSystem.filterBlankLines(rendered_template)
        # And Saving to File ...
        FileSystem.saveFileContent(rendered_template, p_rendered_filename)

    @staticmethod
    def renderDir(p_input_dir : str, p_output_dir : str, context : dict, file_ext: str = ""):
        template_files = FileSystem.safeListFiles(p_input_dir, file_ext=file_ext, keepExt=True)
        Term.print_yellow ("Rendering Templates Dir : [" + p_input_dir  + "]")
        Term.print_yellow ("Rendering Artifacts Dir : [" + p_output_dir + "]")
        # Generating Context File
        contexts_dir = p_output_dir + os.sep + "_Contexts"
        FileSystem.createDir(contexts_dir)
        context_file_yaml = contexts_dir + os.sep + context["DATAMODEL"] + "_context.yaml"
        context_file_json = contexts_dir + os.sep + context["DATAMODEL"] + "_context.json"
        Term.print_yellow ("Rendering Context File  : [" + context_file_yaml + "]")
        Term.print_verbose("Rendering Context : [\n" + yaml.safe_dump(context, indent=2, default_flow_style=False, sort_keys=False) + "\n]")
        FileSystem.saveFileContent(yaml.safe_dump(context, indent=2, default_flow_style=False, sort_keys=False), context_file_yaml)
        FileSystem.saveFileContent(json.dumps(context, indent=3), context_file_json)
        # Rendering Single Level Template Directory
        for template_file in template_files:
            if os.path.isdir(p_input_dir  + os.sep + template_file) : continue
            p_template_filename = p_input_dir  + os.sep + template_file
            p_rendered_filename = p_output_dir + os.sep + template_file.replace("_Template", "").replace(".mako", "").replace("_mako", "")
            FileSystem.render(p_template_filename, p_rendered_filename, context)

    @staticmethod
    def renderDir2(p_input_dir : str, p_output_dir : str, context : dict, file_ext: str = "", root : bool = True, name : str = None):
        Term.print_yellow("Rendering Templates Dir : [" + p_input_dir + "]")
        Term.print_yellow("Rendering Artifacts Dir : [" + p_output_dir + "]")
        if (root) :
            # Generating Context File
            contexts_dir = p_output_dir + os.sep + "_Contexts"
            FileSystem.createDir(contexts_dir)
            context_file_yaml = contexts_dir + os.sep + context["DATAMODEL"] + "_context.yaml"
            context_file_json = contexts_dir + os.sep + context["DATAMODEL"] + "_context.json"
            Term.print_yellow("Rendering Context File  : [" + context_file_yaml + "]")
            Term.print_verbose("Rendering Context : [\n" + yaml.safe_dump(context, indent=2, default_flow_style=False,sort_keys=False) + "\n]")
            FileSystem.saveFileContent(yaml.safe_dump(context, indent=2, default_flow_style=False, sort_keys=False),context_file_yaml)
            FileSystem.saveFileContent(json.dumps(context, indent=3), context_file_json)
            for entity in context["ENTITIES"]:
                context_file_yaml = contexts_dir + os.sep + entity + "_context.yaml"
                context_file_json = contexts_dir + os.sep + entity + "_context.json"
                FileSystem.saveFileContent(yaml.safe_dump(context["ENTITIES"][entity], indent=2, default_flow_style=False, sort_keys=False),context_file_yaml)
                FileSystem.saveFileContent(json.dumps(context["ENTITIES"][entity], indent=3), context_file_json)
        # Rendering Multi Level Template Directory
        for template_file in os.listdir(p_input_dir):
            if template_file.startswith("."+os.sep+".git"): continue
            if template_file.startswith("."+os.sep+".idea"): continue
            if template_file.startswith("."+os.sep+"venv"): continue
            print(str(p_input_dir + os.sep + template_file))
            if (os.path.isdir(p_input_dir + os.sep + template_file)):
                if ("${ENTITY}" in template_file) :
                    for entity in context["ENTITIES"] :
                        new_dir = p_output_dir + os.sep + template_file.replace("${ENTITY}", entity)
                        Term.print_blue("Creating Dir : "+new_dir)
                        if not os.path.exists(new_dir): os.makedirs(new_dir)
                        FileSystem.renderDir2(p_input_dir + os.sep + template_file, new_dir, context["ENTITIES"][entity], root=False, name=entity)
                else:
                    new_dir = p_output_dir + os.sep + template_file
                    Term.print_blue("Creating Dir : " + new_dir)
                    if not os.path.exists(new_dir): os.makedirs(new_dir)
                    FileSystem.renderDir2(p_input_dir + os.sep + template_file, new_dir, context, root=False)
            else:
                if ("${ENTITY}" in template_file) :
                    if ("ENTITIES" in context):
                        for entity in context["ENTITIES"]:
                            p_template_filename = p_input_dir  + os.sep + template_file
                            p_rendered_filename = p_output_dir + os.sep + template_file.replace("${ENTITY}", entity)
                            FileSystem.render(p_template_filename, p_rendered_filename, context["ENTITIES"][entity])
                    else:
                        p_template_filename = p_input_dir  + os.sep + template_file
                        p_rendered_filename = p_output_dir + os.sep + template_file.replace("${ENTITY}", name)
                        FileSystem.render(p_template_filename, p_rendered_filename, context)
                else:
                    p_template_filename = p_input_dir + os.sep + template_file
                    p_rendered_filename = p_output_dir + os.sep + template_file.replace("_Template", "").replace(".mako", "").replace("_mako", "")
                    FileSystem.render(p_template_filename, p_rendered_filename, context)


    @staticmethod
    def listFiles(p_input_dir : str):
        for root, dirs, files in os.walk(p_input_dir):
            if root.startswith("."+os.sep+".git"): continue
            if root.startswith("."+os.sep+".idea"): continue
            if root.startswith("."+os.sep+"venv"): continue
            print(str(root) + str(dirs) + str(files))

###
### Util
###

class Util:

    @staticmethod
    def find_between(content, start, end):
        found = re.search(start + '([\s\S]*?)' + end, content)
        if (found is None): return None
        found = found.group(1)
        found = re.sub(start, "", found)
        found = re.sub(end, "", found)
        return found

    @staticmethod
    def remove_between(content, start, end):
        if (not content): return ""
        found = re.sub(start + '([\s\S]*?)' + end, "", content)
        found = re.sub(start + '([\s\S]*?)' + end, "", content)
        return found

    @staticmethod
    def get_parameters(text, prefix) -> str :
        found = Util.find_between(text.strip(), "<"+prefix+">", "</"+prefix+">")
        if (found): return found
        return None

###
### Path Generation
###


class Path:

    paths_template_list_create_prefix  = """
"${PATH_PREFIX}/${PATH}s": {
            "summary": "Path used to manage the list of ${table}s.",
            "description": "The REST endpoint/path used to list and create zero or more `${TABLE}`.  This path contains a `GET` and `POST` operation to perform the list and create tasks, respectively."
"""

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
    def create_path(entities):
        global schema_parameters
        f_paths_template = ""
        sep = ""
        for entity in entities:
            if ("PATH" in entities[entity]):
                path_par = None
                list_par = None
                get_par = None
                create_par = None
                patch_par = None
                put_par = None
                del_par = None
                schema_par = None
                if ("PATH_PARAMETERS" in entities[entity]) :
                    path_par   = Util.get_parameters(entities[entity]["PATH_PARAMETERS"], "path_parameters")
                    list_par   = Util.get_parameters(entities[entity]["PATH_PARAMETERS"], "list_parameters")
                    get_par    = Util.get_parameters(entities[entity]["PATH_PARAMETERS"], "get_parameters")
                    create_par = Util.get_parameters(entities[entity]["PATH_PARAMETERS"], "post_parameters")
                    patch_par  = Util.get_parameters(entities[entity]["PATH_PARAMETERS"], "patch_parameters")
                    put_par    = Util.get_parameters(entities[entity]["PATH_PARAMETERS"], "put_parameters")
                    del_par    = Util.get_parameters(entities[entity]["PATH_PARAMETERS"], "delete_parameters")
                    schema_par = Util.get_parameters(entities[entity]["PATH_PARAMETERS"], "schema_parameters")

                # Add Pagination Support
                list_parj = []
                if (list_par):
                    list_parj = json.loads(list_par)
                list_parj.append({"in": "query", "name": "limit",  "schema" : { "type": "integer" }, "description": "Pagination Limit"})
                list_parj.append({"in": "query", "name": "offset", "schema" : { "type": "integer" }, "description": "Pagination Offset"})

                # Add Schema Support
                list_parj.append({"in": "query", "name": "schema", "type": "boolean" ,  "allowEmptyValue": "true" ,"description": "Return JSON Schema"})

                # Add Filtering Support
                for att in entities[entity]['properties'] :
                    if ('Schema' not in entities[entity]['properties'][att]) : continue
                    if ('filter' not in entities[entity]['properties'][att]['Schema']) : continue
                    if (entities[entity]['properties'][att]['Schema']['filter']):
                        list_parj.append( {"in": "query",
                                           "name": entities[entity]['properties'][att]['name'],
                                           "schema": {"type": entities[entity]['properties'][att]['type']},
                                           "description": "Filter for "+entities[entity]['properties'][att]['name']})
                list_par = json.dumps(list_parj)

                if (schema_par and schema_par.strip() != "") :
                    schema_params = Term.json_load(schema_par)
                    for param in schema_params:
                        schema_parameters[param] = schema_params[param]
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
                prefix = entities[entity]["PATH_PREFIX"]
                f_paths_template = f_paths_template + sep + Path.paths_table(path, entity, path_prefix=prefix, p_paths_template=l_paths_template)
                sep = ", "
        Term.print_verbose(f_paths_template)
        return f_paths_template


###
### Schema Methods
###

def set_default(attribute : str, desc : dict, prop : str, default) -> dict:
    if ((prop not in desc) or (str(desc[prop]).strip() == "")):
        desc[prop] = default
        Term.print_warning("Warning : attribute [" + str(attribute) + "] " + str(prop) + " defaulted to : [" + str(default) + "]")
    return desc


def decode_prop_schema(prop: str, schema: str, description: str = None, key : str = "schema") -> dict:
    """ Decode for JSON Schema in <schema> </schema>
    - schema is the text to be decoded
    - prop is used to refer to the related property in error messages
    - description will be used as default is not in schema
    """
    desc_schema = dict()
    if (Util.find_between(schema, "<"+key+">", "</"+key+">")):
        schema = Util.find_between(schema, "<"+key+">", "</"+key+">")
        schema = schema.strip()
        try:
            if schema.startswith("{"):  # JSON
                desc_schema = Term.json_load(schema)
            elif schema.startswith("\""):  # JSON
                desc_schema = Term.json_load("{" + schema + "}")
            elif (schema == ""):  # JSON
                desc_schema = dict()
            else:  # YAML
                desc_schema = Term.yaml_load(schema)
        except Exception as e:
                Term.print_error(schema, str(e))
                desc_schema = dict()

    description = Util.remove_between(description, "<"+key+">", "</"+key+">")
    if (not description or description.strip() == ""):
        description = "No Description"

    # Defaults for both Attributes and Objects
    desc_schema = set_default(prop, desc_schema, "description",          description)
    desc_schema = set_default(prop, desc_schema, "markdownDescription",  description)
    desc_schema = set_default(prop, desc_schema, "key",  False)
    desc_schema = set_default(prop, desc_schema, "filter",  False)
    desc_schema = set_default(prop, desc_schema, "validationScript",     "")
    desc_schema = set_default(prop, desc_schema, "example",          "")
    desc_schema = set_default(prop, desc_schema, "applicableTo",     "")
    desc_schema = set_default(prop, desc_schema, "validFor",         "")
    return desc_schema


def check_as_parameter(desc, desc_schema):
    """ Check if this desc_schema property should be set as a global schema parameter and create it if necessary
    - description will be used as default if not in schema
    """
    global schema_parameters
    if ("asParameter" in desc_schema):
        param_desc = dict()
        param_desc["name"] = desc_schema["name"]
        if ("path" in desc_schema["asParameter"].lower())  :
            param_desc["in"] = "path"
        else:
            param_desc["in"] = "query"
        param_desc["description"] = desc["description"]
        if (("required" in desc_schema["asParameter"].lower()) or ("mandatory" in desc_schema["asParameter"].lower())) :
            param_desc["required"] = True
        else:
            param_desc["required"] = False
        param_desc["schema"] = dict()
        param_desc["schema"]["type"]   = desc_schema["type"]
        if not ((desc_schema["format"] == "") or (desc_schema["format"] == "free")):
            param_desc["schema"]["format"] = desc_schema["format"]
        # param_desc["schema"]["minimum"] =
        # param_desc["schema"]["maximum"] =
        param_desc["schema"]["default"] = desc_schema["defaultValue"]
        if (desc_schema["possibleValues"] and desc_schema["possibleValues"].__len__() >=1):
            param_desc["schema"]["enum"]    = desc_schema["possibleValues"]
        # param = { desc_schema["name"]+"Param" : param_desc }
        # schema_parameters.append(param)
        schema_parameters[desc_schema["name"]+"Param"] = param_desc
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


def clean_name(name: str) -> str:
    return unidecode.unidecode(name.strip()).replace(" ", "_").replace("\\", "_").replace("'", "_").replace("/", "-").replace("_fk", "")


def find_entity(entities, entity_name):
    """ Return Entity by Name """
    for entity in entities.keys():
        if (("NAME" in entities[entity]) and (entities[entity]["NAME"] == entity_name)):
            return entities[entity]
        if (("name" in entities[entity]) and (entities[entity]["name"] == entity_name)):
            return entities[entity]
    return None


def find_table_contained(links, table_containing) -> list:
    """ Return Contained Tables for a specified Containing Table """
    lks = []
    for link in links:
        if (links[link]["TableContaining"] == table_containing):
            lks.append(links[link])
    return lks


def find_table_contained_names(table_containing) -> list:
    """ Return Contained Tables for a specified Containing Table """
    lks = find_table_contained(links, table_containing)
    tables = list()
    for lk in lks :
        tables.append(lk["TableContained"])
    return tables


def find_table_cardinatilty(table_containing, table_contained) -> str:
    """ Return Contained Tables for a specified Containing Table """
    for rel in entities[table_containing]["RELATIONS"]:
        if (entities[table_containing]["RELATIONS"][rel]["TableContained"] == table_contained):
            return entities[table_containing]["RELATIONS"][rel]["Cardinalite"]
    return None

"""
The content of the Data Model in SQL Architect will be used as in ReadMe File

"""


# Objects of Interest
entities          = {}
links             = {}
openapi           = {}
schema_parameters = {}   # To OpenAPI Objects

"""
                                Architect                              DbSchema
Entity:
    entity["name"]              = Logical Name
    entity["type"]              = "object"
    entity["description"]       = table["remarks"]
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

     cardinality     = links[link]["Cardinalite"]       OneToOne (3), ZeroToOne (2) , OneToMany (1), ZeroToMany (0) 
     TableContenue   = links[link]["TableContained"]
     TableContenante = links[link]["TableContaining"]
     Name            = links[link]["Name"]
     Descr           = links[link]["Description"]

"""


class Architect:

    def __init__(self):
        self.architect = None
        self.tables    = dict()  # From SQL Architect
        self.relations = dict()  # From SQL Architect

    def find_table_name(self, table_id):
        global entities, links
        for table in entities.keys():
            if (entities[table]["TABLE"] == table_id):
                return entities[table]["NAME"]
        return None

    def find_table_key(self, table_id):
        global entities, links
        for table in entities.keys():
            if (entities[table]["TABLE"] == table_id):
                return entities[table]["KEY"]
        return None

    def collect_links(self):
        """ Scan for all Links / Relationships  and their Attributes in the Architect Data Model """
        global entities, links
        if isinstance(self.relations, dict) :
            self.relations = [self.relations]
        for relation in self.relations:
            link = dict()
            if ("ignore" in relation["@name"]) :
                # Ignore starting with ignore (or Grey Links)
                Term.print_verbose("Relation Ignored (ignore in name) : "+clean_name(relation["@name"]))
                continue
            link["TableContaining"] = relation["@pk-table-ref"]   # find_table_name(relation["@pk-table-ref"])
            link["TableContained"]  = relation["@fk-table-ref"]   # find_table_name(relation["@fk-table-ref"])
            if   (relation["@fkCardinality"] == "3") :  link["Cardinalite"]     = "ZeroToOne"
            elif (relation["@fkCardinality"] == "7") :  link["Cardinalite"]     = "OneToMore"
            elif (relation["@fkCardinality"] == "6") :  link["Cardinalite"]     = "ZeroToMore"
            # if   (relation["@pkCardinality"] == "3") :  link["Cardinalite"]     = "ZeroToOne"
            # elif (relation["@pkCardinality"] == "7") :  link["Cardinalite"]     = "OneToMore"
            # elif (relation["@pkCardinality"] == "6") :  link["Cardinalite"]     = "ZeroToMore"
            # elif (relation["@pkCardinality"] == "2") :  link["Cardinalite"]     = "OneToOne"
            link["Name"]            = clean_name(relation["@name"])
            link["Description"]     = "No Description"
            ignore = False
            for tlink in self.architect["architect-project"]["play-pen"]["table-link"]:
                # if (tlink["@rLineColor"] == "0x999999"):
                    # # Ignore Grey Links (or starting with ignore)
                    # Term.print_verbose("Relation Ignored (grey color) : " + clean_name(relation["@name"]))
                    # ignore = True
                    # continue
                if (tlink["@relationship-ref"] == relation["@id"]):
                    link["Description"] = clean_name(tlink["@pkLabelText"]) + " " + clean_name(tlink["@fkLabelText"])
                    if (link["Description"] == " "): link["Description"] = link["Name"]
                if (ignore is False) :
                    links[relation["@id"]] = link

    def handle_object(self, table):
        """ Extract Data from Architect Table for Object Descriptors """
        obj_desc = {}
        name = clean_name(table["@name"])
        obj_desc["name"] = "name"
        obj_desc["type"] = "object"
        # remarks -> description
        if (table["remarks"] is None):
            table["remarks"] = ""
        obj_desc["description"] = Util.remove_between(table["remarks"], "<schema>", "</schema>").strip()
        if (obj_desc["description"] == "") :
            obj_desc["description"] = "No Description for " + name

        # remarks : we may have a <schema> </schema> with property description
        desc_schema = decode_prop_schema(None, table["remarks"], key="schema")
        desc_schema = set_default(name, desc_schema, "key", False)
        desc_schema = set_default(name, desc_schema, "filter", False)
        desc_schema = set_default(name, desc_schema, "validationScript", "")
        desc_schema = set_default(name, desc_schema, "example", "")
        desc_schema = set_default(name, desc_schema, "applicableTo", "")
        desc_schema = set_default(name, desc_schema, "validFor", "")
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

    def handle_attribute(self, obj_desc, att):
        """ Extract Data from Architect Table Attribute for Object Property Descriptors """
        att_property = {}
        att_name = clean_name(att["@name"])
        att_property["name"] = att_name

        # Handling _PATH for OpenApi Yaml Generation
        if (att_name == "_PATH"):
            # https://amdocs.com<PATH_PREFIX>/<PATH>
            obj_desc["PATH"]        = att["@physicalName"]  # This is the route endpoint
            obj_desc["PATH_PREFIX"] = att["@defaultValue"]  # This is the route path prefix
            obj_desc["PATH_OPERATION"] = "READ-WRITE"
            if (att["remarks"] is not None):
                parameters = Util.find_between(att["remarks"], "<parameters>", "</parameters>")
                if (parameters):
                    obj_desc["PATH_PARAMETERS"] = parameters
                    att["remarks"] = Util.remove_between(att["remarks"], "<parameters>", "</parameters>")
                obj_desc["PATH_OPERATION"]  = att["remarks"]

        # remarks -> description
        if (att["remarks"] is None):
            att["remarks"] = ""
        att_property["description"] = Util.remove_between(att["remarks"], "<schema>", "</schema>").strip()
        if (att_property["description"] == "") :
            att_property["description"] = "No Description for " + att["@name"]

        # remarks : we may have a <schema> </schema> with property description
        desc_schema =  decode_prop_schema(att_name, att["remarks"], key="schema")
        desc_schema = set_default(att_name, desc_schema, "key", False)
        desc_schema = set_default(att_name, desc_schema, "filter", False)
        desc_schema = set_default(att_name, desc_schema, "validationScript", "")
        desc_schema = set_default(att_name, desc_schema, "valueSpecification", "")
        desc_schema = set_default(att_name, desc_schema, "possibleValues", ["default_value", "value1", "value2"])
        desc_schema = set_default(att_name, desc_schema, "defaultValue", "defaultValue")
        desc_schema = set_default(att_name, desc_schema, "format", "")
        desc_schema = set_default(att_name, desc_schema, "example", "")
        desc_schema = set_default(att_name, desc_schema, "minCardinality", 1)
        desc_schema = set_default(att_name, desc_schema, "maxCardinality", 1)
        desc_schema = set_default(att_name, desc_schema, "applicableTo", "")
        desc_schema = set_default(att_name, desc_schema, "validFor", "")
        att_property["Schema"] = desc_schema

        # physicalName -> example
        if (att["@physicalName"] is None):
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
        if (att["@type"] == "12"):   att_property["type"]   = "string"    # VARCHAR
        if ("@precision" in att):    att_property["precision"]  = att["@precision"]
        if (att["@type"] == "4"):    att_property["type"]   = "integer"   # INTEGER
        if (att["@type"] == "-2"):   att_property["type"]   = "binary"    # BINARY
        if (att["@type"] == "-5"):   att_property["type"]   = "integer"   # BIGINT
        if (att["@type"] == "92"):   att_property["type"]   = "string"    # TIME
        if (att["@type"] == "92"):   att_property["format"] = "date-time" # -
        if (att["@type"] == "93"):   att_property["type"]   = "string"    # TIMESTAMP
        if (att["@type"] == "93"):   att_property["format"] = "timestamp" # -
        if (att["@type"] == "2000"): att_property["type"]   = "string"    # JAVA_OBJECT
        if (att["@type"] == "2000"): att_property["format"] = "json"      # -
        if (att["@type"] == "1111"): att_property["type"]   = "any"       # UNKNOWN = any type (needs to be fixed in hooks)
        if (att["@type"] == "16"):   att_property["type"]   = "boolean"   # BOOLEAN
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
        if (desc_schema["key"] == True):
            obj_desc["KEY"] = att_name

        # add to object descriptor
        if (att_name != "_PATH"):
            obj_desc["properties"][att_name] = att_property

        return obj_desc, att_name

    def collect_tables(self):
        """ Scan for all Tables and their Attributes in the Architect Data Model """
        global entities, links
        for table in self.tables:
            data_type, entity_name = self.handle_object(table)
            if ("ignore" in data_type["example"]) :
                Term.print_verbose("Table Ignored (ignore in example/physicalName) : " + clean_name(entity_name))
                continue
            for folder in table["folder"]:
                if ("index" in folder):
                    if ("index-column" not in folder["index"]): continue
                    for index_col in folder["index"]["index-column"]:
                        data_type["primary_key"] = folder["index"]["index-column"]["@physicalName"]
                if "column" not in folder: continue
                column = folder["column"]
                data_type["KEY"] = None
                if isinstance(column, list):
                    for col in column:
                        data_type, att_name = self.handle_attribute(data_type, col)
                else:
                    data_type, att_name = self.handle_attribute(data_type, column)
            entities[entity_name] = data_type

    def read_architect(self, data_model : str):
        """ Read and Scan Architect Data Model """
        Term.print_yellow("> read_architect")
        global entities, links

        # Reading architect file
        myFile = open(data_model + ".architect", "r")
        architectSchema = myFile.read()
        myFile.close()
        self.architect = xmltodict.parse(architectSchema)

        # Save to JSON Format
        # FileSystem.saveFileContent(json.dumps(self.architect, indent=3), data_model + ".json")
        Term.print_verbose("architect : \n" + json.dumps(self.architect, indent=3))

        # Collecting architect entities
        self.tables    = self.architect["architect-project"]["target-database"]["table"]
        self.relations = self.architect["architect-project"]["target-database"]["relationships"]["relationship"]
        self.collect_links()
        self.collect_tables()

        # Replacing Table IDs by Names & Creating Sub-Relationships
        for entity in entities:
            for rel in find_table_contained(links, entities[entity]["TABLE"]):
                if (not self.find_table_name(rel["TableContained"])):
                    continue
                rel["TableContenanteID"] = rel["TableContaining"]
                rel["TableContenueID"]   = rel["TableContained"]
                rel["TableContaining"]   = self.find_table_name(rel["TableContenanteID"])
                rel["TableContained"]    = self.find_table_name(rel["TableContenueID"])
                foreign_key = self.find_table_key(rel["TableContenueID"])
                entities[entity]["RELATIONS"][rel["Name"]] = rel
                this_property = dict()
                this_property["description"] = rel["Description"]
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
                entities[entity]["properties"][rel["TableContained"]] = this_property

        # What did we get ?
        Term.print_verbose("tables    : " + str(self.tables))
        Term.print_verbose("relations : " + str(self.relations))
        Term.print_verbose("entities  : " + str(entities))
        Term.print_verbose("links     : " + str(links))

        Term.print_yellow("< read_architect")
        return entities, links


def get_entity_property_value(p_entity : dict, p_property: str) -> str :
    if (property not in p_entity["properties"]):
        return None
    if ("example" in p_entity["properties"][p_property]):
        # From Physical Name
        value = p_entity["properties"][p_property]["example"].strip()
        if (value != ""): return value
    return None


def lets_do_openapi_yaml():
    global data_model, input_dir, output_dir, openapi

    """ Created Openapi Yaml from Data Model """
    Term.print_yellow("> lets_do_openapi Yaml API")
    global entities, links, schema_parameters

    # Create API Operations
    paths = Term.json_load("{" + Path.create_path(entities) + "}")

    # Info Data / Default Values
    open_api_yaml = dict()
    open_api_yaml["openapi"] = "3.0.2"
    open_api_yaml["info"] = dict()
    open_api_yaml["info"]["title"]       = "Business Data Model"
    open_api_yaml["info"]["version"]     = "1.0.0"
    open_api_yaml["info"]["description"] = "Business Data Model. This is generated, modify source SQL Architect data model instead."
    open_api_yaml["info"]["contact"]     = {}
    open_api_yaml["info"]["contact"]["name"]  = "Bernard Heuse"
    open_api_yaml["info"]["contact"]["url"]   = "https://www.amdocs.com/"
    open_api_yaml["info"]["contact"]["email"] = "bheuse@gmail.com"

    if "OpenAPI" in entities :
        if ("title" in entities["OpenAPI"]["properties"]):
            open_api_yaml["info"]["title"]       = entities["OpenAPI"]["properties"]["title"]["example"]

        if ("version" in entities["OpenAPI"]["properties"]):
            open_api_yaml["info"]["version"]     = entities["OpenAPI"]["properties"]["version"]["example"]

        if ("description" in entities["OpenAPI"]["properties"]):
            open_api_yaml["info"]["description"] = entities["OpenAPI"]["properties"]["description"]["example"] + " " + entities["OpenAPI"]["properties"]["description"]["description"]

        if ("contact" in entities["OpenAPI"]["properties"]):
            contacts = Term.json_load(entities["OpenAPI"]["properties"]["contact"]["description"])
            open_api_yaml["info"]["contact"] = contacts

        if ("security" in entities["OpenAPI"]["properties"]):
            security = Term.json_load(entities["OpenAPI"]["properties"]["security"]["description"])
            open_api_yaml["security"] = security

        if ("license" in entities["OpenAPI"]["properties"]):
            license = Term.json_load(entities["OpenAPI"]["properties"]["license"]["description"])
            open_api_yaml["info"]["license"] = license

        if ("tags" in entities["OpenAPI"]["properties"]):
            tags = Term.json_load(entities["OpenAPI"]["properties"]["tags"]["description"])
            open_api_yaml["tags"] = tags

        if ("servers" in entities["OpenAPI"]["properties"]):
            servers = Term.json_load(entities["OpenAPI"]["properties"]["servers"]["description"])
            open_api_yaml["servers"] = servers

        if ("securitySchemes" in entities["OpenAPI"]["properties"]):
            securitySchemes = Term.json_load(entities["OpenAPI"]["properties"]["securitySchemes"]["description"])
            open_api_yaml["components"] = dict()
            open_api_yaml["components"]["securitySchemes"] = securitySchemes

        openapi = open_api_yaml
        del entities["OpenAPI"]

    # Clean-up before generation
    entities_yaml = copy.deepcopy(entities)
    for entity in entities_yaml:
        if ("TABLE" in entities_yaml[entity])     : del entities_yaml[entity]["TABLE"]
        if ("RELATIONS" in entities_yaml[entity]) : del entities_yaml[entity]["RELATIONS"]
        if ("NAME" in entities_yaml[entity])      : del entities_yaml[entity]["NAME"]
        if ("KEY" in entities_yaml[entity])       : del entities_yaml[entity]["KEY"]
        if ("prepend" in entities_yaml[entity])   : del entities_yaml[entity]["prepend"]
        if ("append" in entities_yaml[entity])    : del entities_yaml[entity]["append"]
        if ("options" in entities_yaml[entity])   : del entities_yaml[entity]["options"]
        if ("PATH_OPERATION" in entities_yaml[entity]):  del entities_yaml[entity]["PATH_OPERATION"]
        if ("PATH_PARAMETERS" in entities_yaml[entity]): del entities_yaml[entity]["PATH_PARAMETERS"]
        if ("PATH_PREFIX" in entities_yaml[entity]):     del entities_yaml[entity]["PATH_PREFIX"]
        if ("PATH"  in entities_yaml[entity]):           del entities_yaml[entity]["PATH"]
        if ("_ROOT" in entities_yaml[entity]):           del entities_yaml[entity]["_ROOT"]
        if ("name" in entities_yaml[entity]) :           del entities_yaml[entity]["name"]
        if ("mandatory" in entities_yaml[entity]) :      del entities_yaml[entity]["mandatory"]
        if ("properties" in entities_yaml[entity]) :
            if ("name" in entities_yaml[entity]["properties"]):           del entities_yaml[entity]["properties"]["name"]
            if ("mandatory" in entities_yaml[entity]["properties"]):      del entities_yaml[entity]["properties"]["mandatory"]
            if ("_ROOT" in entities_yaml[entity]["properties"]):          del entities_yaml[entity]["properties"]["_ROOT"]
            for prop in entities_yaml[entity]["properties"] :
                if ("name" in entities_yaml[entity]["properties"][prop]):           del entities_yaml[entity]["properties"][prop]["name"]
                if ("mandatory" in entities_yaml[entity]["properties"][prop]):      del entities_yaml[entity]["properties"][prop]["mandatory"]
                if ("precision" in entities_yaml[entity]["properties"][prop]):      del entities_yaml[entity]["properties"][prop]["precision"]
                if ("Schema" in entities_yaml[entity]["properties"][prop]):
                    check_as_parameter(entities_yaml[entity]["properties"][prop],       entities_yaml[entity]["properties"][prop]["Schema"])
                if ("Schema" in entities_yaml[entity]["properties"][prop]):             del entities_yaml[entity]["properties"][prop]["Schema"]
        if ("Schema" in entities_yaml[entity]) :         del entities_yaml[entity]["Schema"]

    # Add Paths
    open_api_yaml["paths"] = paths

    # Add Components
    if "components" in open_api_yaml:
        open_api_yaml["components"]["schemas"] = entities_yaml
    else:
        open_api_yaml["components"] = {"schemas": entities_yaml}

    # Add Parameters
    if "components" in open_api_yaml:
        open_api_yaml["components"]["parameters"] = schema_parameters
    else:
        open_api_yaml["components"] = {"parameters": schema_parameters}

    # Re-Order
    open_api = dict()
    if "openapi"      in open_api_yaml : open_api["openapi"]      = open_api_yaml["openapi"]
    if "info"         in open_api_yaml : open_api["info"]         = open_api_yaml["info"]
    if "externalDocs" in open_api_yaml : open_api["externalDocs"] = open_api_yaml["externalDocs"]
    if "servers"      in open_api_yaml : open_api["servers"]      = open_api_yaml["servers"]
    if "security"     in open_api_yaml : open_api["security"]     = open_api_yaml["security"]
    if "paths"        in open_api_yaml : open_api["paths"]        = open_api_yaml["paths"]
    if "components"   in open_api_yaml : open_api["components"]   = open_api_yaml["components"]

    # Some Custom for NEF_Configuration_Service
    if ("NEF_Configuration_Service" in data_model) :
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
    if ("NEF_SCEF" in data_model) :
        open_api["paths"]["/notify/message"] = open_api["paths"]["/notify/messages"]
        del open_api["paths"]["/notify/messages"]
        open_api["paths"]["/request/message"] = open_api["paths"]["/request/messages"]
        del open_api["paths"]["/request/messages"]
        for path in open_api["paths"] :
            if ("/request/message" == path):
                del open_api["paths"]["/request/message"]["parameters"]
                open_api["paths"]["/request/message"]["post"]["responses"]["202"]["content"]["application/json"]["schema"]["$ref"] = "#/components/schemas/Response"
                open_api["paths"]["/request/message"]["description"] = "Submit Message Request"
                open_api["paths"]["/request/message"]["summary"] = "Submit Message Request"
            if ("/notify/message" == path):
                del open_api["paths"]["/notify/message"]["parameters"]
                open_api["paths"]["/notify/message"]["post"]["responses"]["202"]["content"]["application/json"]["schema"]["$ref"] = "#/components/schemas/Response"
                open_api["paths"]["/notify/message"]["description"] = "Transmits Notifications"
                open_api["paths"]["/notify/message"]["summary"] = "Transmits Notifications"
        del open_api["components"]["schemas"]["AVP"]["properties"]["Value"]["type"]
        open_api["components"]["schemas"]["AVP"]["properties"]["Value"]["oneOf"] = [ { "type" : "integer"} ,
                                                                                     { "type" : "string"},
                                                                                     { "type" : "boolean"},
                                                                                     { "type" : "number"},
                                                                                     { "type" : "array" ,
                                                                                       "items" : { "$ref" : "#/components/schemas/AVP"  } }  ]

    Term.print_yellow("< lets_do_openapi")
    Term.print_verbose(open_api)

    # Done - Save
    yaml_text = yaml.safe_dump(open_api, indent=2, default_flow_style=False, sort_keys=False)
    Term.print_verbose(yaml_text)
    yaml_file = output_dir + os.sep + FileSystem.get_basename(data_model)+"_API.yaml"
    FileSystem.saveFileContent(yaml_text, yaml_file)
    Term.print_blue("Ready   : " + yaml_file)

    lets_do_datastore(with_upload=False)


baseURI  = "https://amdocs.com/schemas/nef/"
schemas  = {}


def lets_do_json_schema():
    global data_model, input_dir, output_dir
    Term.print_yellow("> lets_do_json Schema")
    ex_objets = {}

    # Clean-up before generation
    entities_json = copy.deepcopy(entities)
    for entity in entities_json:
        if ("TABLE" in entities_json[entity])     : del entities_json[entity]["TABLE"]
        if ("RELATIONS" in entities_json[entity]) : del entities_json[entity]["RELATIONS"]
        if ("NAME" in entities_json[entity])      : del entities_json[entity]["NAME"]
        if ("KEY" in entities_json[entity])       : del entities_json[entity]["KEY"]
        if ("prepend" in entities_json[entity])   : del entities_json[entity]["prepend"]
        if ("append" in entities_json[entity])    : del entities_json[entity]["append"]
        if ("options" in entities_json[entity])   : del entities_json[entity]["options"]
        if ("PATH_OPERATION" in entities_json[entity]):  del entities_json[entity]["PATH_OPERATION"]
        if ("PATH_PARAMETERS" in entities_json[entity]): del entities_json[entity]["PATH_PARAMETERS"]
        if ("PATH_PREFIX" in entities_json[entity]):     del entities_json[entity]["PATH_PREFIX"]
        if ("PATH"  in entities_json[entity]):           del entities_json[entity]["PATH"]
        # if ("name" in entities_json[entity]) :           del entities_json[entity]["name"]
        # if ("mandatory" in entities_json[entity]) :      del entities_json[entity]["mandatory"]
        Term.print_verbose("> " + entity)
        for prop in entities_json[entity]["properties"] :
            Term.print_verbose(" - " + prop)
            # if ("name" in entities_json[entity]["properties"][prop]):           del entities_json[entity]["properties"][prop]["name"]
            # if ("mandatory" in entities_json[entity]["properties"][prop]):      del entities_json[entity]["properties"][prop]["mandatory"]
            continue

    for entity in entities_json:
        Term.print_yellow("["+entity+"]")
        Term.print_verbose(json.dumps(entities_json[entity], indent=3))
        Term.print_verbose(" - description : " + str(entities_json[entity]["description"]))
        Term.print_verbose(" - type        : " + str(entities_json[entity]["type"]))
        Term.print_verbose(" - example     : " + str(entities_json[entity]["example"]))
        Term.print_verbose(" - " + str(entities_json[entity]))

        json_object = {}
        json_schema = {}
        object_desc = entities_json[entity]

        json_schema["$schema"]     = "http://json-schema.org/draft-07/schema"
        json_schema["$id"]         = baseURI+entity+".json"
        json_schema["type"]        = "object"
        json_schema["title"]       = "Schema for " + entity
        json_schema["description"] = object_desc["description"]
        json_schema["default"]     = {}
        json_schema["examples"]    = []
        json_schema["required"]    = []
        json_schema["properties"]  = {}
        json_schema["additionalProperties"] = True

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
                prop_schema["$ref"]  = os.path.basename(data_model) + "_" + item + "_schema.json"
                prop_schema["$ref"]  = "#/$defs/" + item + ""
                json_schema["properties"][item] = prop_schema
            elif ("items" in property_desc):
                # Array of ...
                if ("$ref" in property_desc["items"]):
                    # Array of Sub-objects
                    Term.print_verbose("   #>> Array objects : " + str(property_desc["items"]["$ref"]))
                    item = re.sub("#/components/schemas/", "", str(property_desc["items"]["$ref"]))
                    prop_schema["type"] = "array"
                    prop_schema["items"] = {"$ref" : "" + os.path.basename(data_model) + "_" + item + "_schema.json"}
                    prop_schema["items"] = {"$ref" : "#/$defs/" + item + ""}
                    # json_schema["properties"][item+"s"] = prop_schema
                    json_schema["properties"][item] = prop_schema
                else:
                    # Array of Basic Types
                    Term.print_verbose("   #>> Array Types : " + str(property_desc["items"]["type"]))
                    prop_schema["type"] = "array"
                    prop_schema["items"] = {"type" : property_desc["items"]["type"]  }
                    if ("format" in property_desc["items"]):
                        prop_schema["items"]["format"]= property_desc["items"]["format"]
            else:
                # Value Property
                desc = property_desc["description"]
                desc_schema = {}
                if ("Schema" in property_desc):
                    desc_schema = property_desc["Schema"]

                if (property_desc["name"] != "_ROOT"):
                    json_object[property_desc["name"]] = property_desc["example"] if ("example" in property_desc) else "noExample"
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
                    json_object[property_desc["name"]] = prop_schema["defaultValue"]

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
        Term.print_verbose("Sample Object: "+str(json_object))
        json_schema["examples"]  = [json_object]
        ex_objets[entity] = json_object
        schemas[entity]   = json_schema

        # Add Required Relationship Sub Objects Schemas
        for link in links:
            cardinality     = links[link]["Cardinalite"]
            TableContenue   = links[link]["TableContained"]
            TableContenante = links[link]["TableContaining"]
            Term.print_verbose(TableContenante + " Contains [" + cardinality + "] " + TableContenue)
            if (entity == TableContenante) and (str(cardinality)  in ["1", "3", "OneToMore" , "OneToOne"]):
                json_schema["required"].append(TableContenue)

    # Add $defs Sub-Objects Schemas & Generating Schemas
    schema_file = None
    for schema in schemas:
        if "properties" not in schemas[schema]: continue
        if ("_ROOT" in schemas[schema]["properties"]) :
            # del schemas[schema]["properties"]["_ROOT"]
            schemas[schema]["$defs"] = {}
            for schema2 in schemas:
                if "properties" not in schemas[schema]: continue
                if "_ROOT" in schemas[schema2]["properties"] :
                    del schemas[schema2]["properties"]["_ROOT"]
                    continue
                if ("$schema" in schemas[schema2]): del schemas[schema2]["$schema"]
                if ("$id"     in schemas[schema2]): del schemas[schema2]["$id"]
                schemas[schema]["$defs"][schema2] = schemas[schema2]
            # Generate Schema File - multiple _ROOT
            # schema_file = output_dir + FileSystem.get_basename(data_model) + "_" + schema + "_Schema.json"
            # FileSystem.saveFileContent(json.dumps(schemas[schema], indent=3), schema_file)
            # Generate Schema File - assuming only one _ROOT
            schema_file = data_model + "_Schema.json"
            FileSystem.saveFileContent(json.dumps(schemas[schema], indent=3), schema_file)

    Term.print_yellow("< lets_do_json Schema")

    Term.print_verbose(json.dumps(ex_objets, indent=3))
    if (schema_file) :
        Term.print_blue("Ready   : "+schema_file)
    else:
        Term.print_error("No _ROOT Entry")


def lets_do_datastore(with_upload : bool = True):
    global data_model, input_dir, output_dir
    Term.print_yellow("> lets_do_datastore API Targets")

    entities_json = copy.deepcopy(entities)

    # Clean-up before generation
    for entity in entities_json:
        if ("TABLE" in entities_json[entity])     : del entities_json[entity]["TABLE"]
        if ("RELATIONS" in entities_json[entity]) : del entities_json[entity]["RELATIONS"]
        # if ("NAME" in entities_json[entity])      : del entities_json[entity]["NAME"]
        if ("KEY" in entities_json[entity])       : del entities_json[entity]["KEY"]
        if ("prepend" in entities_json[entity])   : del entities_json[entity]["prepend"]
        if ("append" in entities_json[entity])    : del entities_json[entity]["append"]
        if ("options" in entities_json[entity])   : del entities_json[entity]["options"]
        if ("PATH_OPERATION" in entities_json[entity]):  del entities_json[entity]["PATH_OPERATION"]
        if ("PATH_PARAMETERS" in entities_json[entity]): del entities_json[entity]["PATH_PARAMETERS"]
        if ("PATH_PREFIX" in entities_json[entity]):     del entities_json[entity]["PATH_PREFIX"]
        # if ("PATH"  in entities_json[entity]):           del entities_json[entity]["PATH"]
        # if ("name" in entities_json[entity]) :           del entities_json[entity]["name"]
        # if ("mandatory" in entities_json[entity]) :      del entities_json[entity]["mandatory"]
        if ("Schema" in entities_json[entity])     : del entities_json[entity]["Schema"]
        Term.print_verbose("> " + entity)
        for prop in entities_json[entity]["properties"] :
            Term.print_verbose(" - " + prop)
            # if ("name" in entities_json[entity]["properties"][prop]):           del entities_json[entity]["properties"][prop]["name"]
            # if ("mandatory" in entities_json[entity]["properties"][prop]):      del entities_json[entity]["properties"][prop]["mandatory"]
            if ("Schema" in entities_json[entity]["properties"][prop]):      del entities_json[entity]["properties"][prop]["Schema"]
            continue

    # Generating Schema for _PATH Entities
    for entity in entities_json:
        entity_desc = entities_json[entity]
        if ("PATH" not in entity_desc) : continue
        api_target = entity_desc["PATH"]
        name = entity_desc["NAME"]
        schema_file = data_model + "_" + name + "_Schema.json"
        schema = schemas[name]

        entities_json[entity]["$schema"]     = "http://json-schema.org/draft-07/schema"
        entities_json[entity]["$id"]         = baseURI+entity+".json"
        entities_json[entity]["type"]        = "object"
        entities_json[entity]["title"]       = "Schema for " + entity

        # Add $defs Sub-Objects Schemas
        for schema in schemas:
            if (schema == entity) : continue
            if (schema not in find_table_contained_names(entity)): continue
            # Entity contain this schema
            if ("PATH" in entities_json[schema]):
                # Entity is external
                card = find_table_cardinatilty(entity, schema)
                if (card and (card == "OneToOne" or card == "ZeroToOne")):
                    # del entities_json[entity]["properties"][schema]["description"]
                    entities_json[entity]["properties"][schema]["-$ref"] = os.path.basename(data_model) + "_" + schema + "_Schema.json"
                    entities_json[entity]["properties"][schema]["type"] = "string"
                if (card and (card == "OneToMore" or card == "ZeroToMore")):
                    # del entities_json[entity]["properties"][schema]["description"]
                    entities_json[entity]["properties"][schema]["type"]  = "array"
                    entities_json[entity]["properties"][schema]["items"] = {}
                    entities_json[entity]["properties"][schema]["items"]["-$ref"] = os.path.basename(data_model) + "_" + schema + "_Schema.json"
                    entities_json[entity]["properties"][schema]["items"]["type"] = "string"
                pass
            else:
                # Entity is internal - Add to internal schema
                card = find_table_cardinatilty(entity, schema)
                if (card and (card == "OneToOne" or card == "ZeroToOne")):
                    # del entities_json[entity]["properties"][schema]["description"]
                    entities_json[entity]["properties"][schema]["$ref"] = "#/$defs/"+schema
                    if ("$defs" not in entities_json[entity]):
                        entities_json[entity]["$defs"] = {}
                    entities_json[entity]["$defs"][schema] = entities_json[schema]
                if (card and (card == "OneToMore" or card == "ZeroToMore")):
                    # del entities_json[entity]["properties"][schema]["description"]
                    entities_json[entity]["properties"][schema]["type"]  = "array"
                    entities_json[entity]["properties"][schema]["items"] = {}
                    entities_json[entity]["properties"][schema]["items"]["$ref"] = "#/$defs/"+schema
                    if ("$defs" not in entities_json[entity]):
                        entities_json[entity]["$defs"] = {}
                    entities_json[entity]["$defs"][schema] = entities_json[schema]

    Term.print_yellow("< lets_do_datastore")

    # if (not with_upload):
    #    return

    Term.print_yellow("> lets_do_datastore upload")

    # Creating DataStore and Loading Schema for _PATH Entities
    for entity in entities_json:
        entity_desc = entities_json[entity]
        if ("PATH" not in entity_desc): continue
        api_target = entity_desc["PATH"]
        if ("PATH" in entities_json[entity]): del entities_json[entity]["PATH"]
        schema_dir = output_dir + os.sep + "_Schemas"
        FileSystem.createDir(schema_dir)
        schema_file = schema_dir + os.sep + FileSystem.get_basename(data_model) + "_" + entity + "_Schema.json"
        Term.print_yellow(schema_file)
        FileSystem.saveFileContent(json.dumps(entities_json[entity], indent=3), schema_file)
        if (with_upload):
            curl = 'curl -X POST -H "Content-Type: application/json" -d @'+schema_file+' https://127.0.0.1:5000/datastore/'+api_target+'?create'
            Term.print_yellow(curl)
            req = "https://127.0.0.1:5000"+"/datastore/"+api_target+"s"+"?create"
            res = requests.post(req, json=schema, verify=False)
            Term.print_yellow(str(res))

    Term.print_yellow("< lets_do_datastore upload")


def lets_do_render():
    global data_model, input_dir, output_dir, openapi
    Term.print_yellow("> lets_do_render artifacts")

    context = {
        "DATAMODEL" : FileSystem.get_basename(data_model),
        "OPENAPI"   : openapi,
        "ENTITIES"  : entities
    }
    FileSystem.renderDir(input_dir, output_dir, context)
    FileSystem.renderDir2(input_dir, output_dir, context)

    Term.print_yellow("< lets_do_render")


def lets_do_it(do_what : str = "openapi, render"):
    global data_model, input_dir, output_dir
    input_dir  = data_model + input_dir_suffix
    output_dir = data_model + output_dir_suffix
    if FileSystem.is_FileExist(data_model+".architect"):
        Term.print_blue("Reading : "+data_model+".architect")
        architect = Architect()
        architect.read_architect(data_model)
    else:
        Term.print_error("Model not found : "+data_model)
        return

    FileSystem.createDir(data_model + input_dir_suffix)
    FileSystem.createDir(data_model + output_dir_suffix)

    if ("schema" in do_what.lower()) :
        lets_do_json_schema()
    if (("openapi" in do_what.lower()) or ("yaml" in do_what.lower())) :
        lets_do_openapi_yaml()
    if ("datastore" in do_what.lower()) :
        lets_do_datastore()
    if ("render" in do_what.lower()) :
        lets_do_render()


class Test(unittest.TestCase):

    def setUp(self) -> None:
        Term.print_red("> Setup")
        Term.setVerbose()
        Term.print_red("< Setup")

    def testValidateSchema(self):
        Term.print_green("> testValidateSchema")
        schema = {
            "items": {
                "anyOf": [
                    {"type": "string", "maxLength": 2},
                    {"type": "integer", "minimum": 5}
                ]
            }
        }
        validate(instance={"name": "Eggs", "price": 34.99}, schema=schema)
        obj_instance = [{}, 3, "foo"]
        validate(instance=obj_instance, schema=schema)
        obj_instance = ["fo", 3]
        validate(instance=obj_instance, schema=schema)
        Term.print_green("< testValidateSchema")

    def testGenerateNEFConfigurationSchema(self):
        Term.setVerbose(False)
        lets_do_it("NEF"+os.sep+"NEF_Configuration", "schema")

    def testGenerateNEFConfigurationService(self):
        Term.setVerbose(False)
        lets_do_it("NEF"+os.sep+"NEF_Configuration"+os.sep+"NEF_Configuration_Service", "openapi")

    def testGenerateNEFMarketPlaceDataService(self):
        Term.setVerbose(False)
        lets_do_it("NEF"+os.sep+"NEF_MarketPlace"+os.sep+"NEF_MarketPlace_DataModel", "openapi")

    def testGenerateNEFCatalogDataService(self):
        Term.setVerbose(False)
        global data_model
        data_model = "NEF"+os.sep+"NEF_Catalog"+os.sep+"NEF_Catalog_DataModel"
        lets_do_it("openapi + schema + render")
        # lets_do_it("Nef"+os.sep+"NEF_Catalog_DataModel", "openapi + schema + datastore + render")

    def testGenerateSCEFService(self):
        Term.setVerbose(True)
        global data_model
        data_model = "NEF"+os.sep+"NEF_SCEF"+os.sep+"NEF_SCEF_API"
        lets_do_it("openapi render")

    def testListFiles(self):
        FileSystem.listFiles(".")
        print(os.listdir("."))


if __name__ == '__main__':
    what = "openapi, render"
    if (len(sys.argv) >= 2):
        data_model = sys.argv[1]
    if (len(sys.argv) >= 3):
        what = sys.argv[2]
    lets_do_it(what)
