<%def name="generate(managerName)">
#!/usr/bin/env python3
\n
# THIS IS AUTO GENERATED CODE. DO NOT CHANGE. CHANGE ARCHITECT SOURCE INSTEAD
\n
import os
from typing import Union
\n
import uvicorn
from fastapi import Depends, FastAPI, Query, Request, Path, Body, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, PlainTextResponse
from pydantic import BaseModel, Field
from typing import List
from enum import Enum
from threading import Thread
import markdown
import sys
import argparse
import re
import datetime
import logging
from aepctl import AepCtl
import Util as ut

# ut.setup_logging()
\n
# Console Output
logging.basicConfig(format='%(levelname)s:%(name)s:%(message)s', level=logging.INFO)
\n
# File Logs
timestamp = datetime.datetime.now().strftime("%y%m%d-%H%M%S")
logDir    = "."+os.sep+"logs"
logFile   = logDir+os.sep+__name__+"-"+timestamp+".log"
logging.basicConfig(filename=logFile, filemode='w', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
logger    = logging.getLogger(__name__)
\n
\n
def handle(command, payload : Union[dict, str, File] = None):
    command = command.replace("API_Category",   "categories")
    command = command.replace("API_Collection", "collections")
    command = command.replace("API_Bundle",     "API_Bundles")
    command = command.replace("API",            "apis")
    command = command.replace("UsagePolicy",    "usagepolicies")
    command = command.replace("API_Provider",   "providers")
    command = command.replace("API_Articles",   "articles")
    logger.info("AepCtl Command " + str(command))
    payload_filename = ut.uuid()

    if (payload):
        if (isinstance(payload, dict)):  # JSON Request Body
            logger.info("AepCtl dict Payload \n" + ut.to_json(payload))
            payload_filename = "backup" + os.sep + payload_filename+"_payload.json"
            ut.saveJsonFile(payload, payload_filename)
            logger.info("Payload dict saved in : " + payload_filename)
            command = command + " " + payload_filename
        if (isinstance(payload, str)):  # FileName
            # payload = ut.loadData(str)
            ut.saveJsonFile(payload, payload_filename)
            payload_filename = payload
            logger.info("Payload filename saved in : " + payload_filename)
            command = command + " " + payload_filename
        if (isinstance(payload, UploadFile)):  # File
            payload_filename = "backup" + os.sep + payload_filename + "_" + payload.filename
            with open(payload_filename, "wb+") as file_object:
                file_object.write(payload.file.read())
            logger.info("Payload file saved in : " + payload_filename)
            command = command + " " + payload_filename

        logger.info("AepCtl Command " + str(command))

    result = AepCtl.main(command, interactive=False)

    if (payload):
        ut.safeDeleteFile(payload_filename)
        logger.info("Payload deleted  : " + payload_filename)

    logger.info(str(result))
    js_res = ut.loadDataContent(result)
    if (js_res):
        return js_res
        return JSONResponse(content=js_res, status_code=200)
    else:
        return result
        return PlainTextResponse(content=result, status_code=400)
\n
\n

% for ENTITY, ENTITY_DATA in ENTITIES.items():

<%
    className = ENTITY
%>

class ${className}(BaseModel):
    """
    ${ENTITY_DATA["description"]}
    """
% for PROPERTY, PROPERTY_DATA in ENTITY_DATA["properties"].items():
<%
    if (PROPERTY_DATA.get("$ref")):
        # $ref: '#/$defs/API_Details'
        ref = PROPERTY_DATA.get("$ref")
        attType = ref.replace("#/$defs/","")
        attType = attType.replace("#/components/schemas/","")
    else:
        attType = PROPERTY_DATA.get("type")
        if (attType == "string")  : attType = "str"
        if (attType == "integer") : attType = "int"
        if (attType == "boolean") : attType = "bool"
        if (attType == "array")   :
            typeof = PROPERTY_DATA.get("items").get("type")
            if (typeof == "string")  : typeof = "str"
            if (typeof == "integer") : typeof = "int"
            if (typeof == "boolean") : typeof = "bool"
            attType = "List["+typeof+"] | None"
    description = PROPERTY_DATA.get("description").replace("\n"," ")
%>
    ${PROPERTY} : ${attType} = Field(description="${description}")
% endfor
% if 'PATH' in ENTITY_DATA:
% if ENTITY_DATA['PATH_OPERATION'] != 'read-only':
    # read-only
% endif
    # NOT read-only
% endif
\n
\n
% endfor
tags_metadata = [
    {
        "name": "${DATAMODEL}",
        "description": "${DATAMODEL} API Management Store Operations.",
        "externalDocs": {
            "description": "${DATAMODEL} Developer Portal Rest API",
            "url": "https://apim.docs.wso2.com/en/latest/reference/product-apis/devportal-apis/devportal-v2/devportal-v2/",
        },
    },
    {
        "name": "AepCtl",
        "description": "AepCtl support operations.",
    },
]
\n
\n
description = """

<img src="images/AepLogo.png" width="60">

Manage the Amdocs Exposure Platform ${DATAMODEL}.

"""
\n
\n
app = FastAPI(
    title="${DATAMODEL}",
    description=description,
    version="0.0.1",
    terms_of_service="http://example.com/terms/",
    contact={
        "name": "Bernard Heuse",
        "url": "https://www.linkedin.com/in/bernard-heuse-16296a",
        "email": "bheuse@amdocs.com",
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
    openapi_tags=tags_metadata
)
\n
\n
@app.get("/")
async def root():
    return { "Status" : "All Good !"}
\n
\n

class ListTypes(str, Enum):
    ids     = "ids"
    names   = "names"
    entries = "entries"
    help    = "help"

class ParamsList:
    def __init__(self,
                 idNames  : ListTypes   = Query(description="List entries, names or ids",  default="names")):
        self.idNames = idNames


% for ENTITY, ENTITY_DATA in ENTITIES.items():
% if 'PATH' in ENTITY_DATA:
@app.get("/${ENTITY}", tags=["${ENTITY}"])
async def get_list_of_${ENTITY}(params: ParamsList = Depends()):
    return handle("fs ${ENTITY} list"+ " " + params.idNames)
\n
\n
@app.get("/${ENTITY}/{idName}", tags=["${ENTITY}"], response_model=${ENTITY})
async def get_${ENTITY}(idName : str) -> ${ENTITY}:
    response = handle("fs ${ENTITY} get "+idName)
    if (isinstance(response,dict)):
        return ${ENTITY}(**response)
    else:
        return response
\n
\n
@app.post("/${ENTITY}", tags=["${ENTITY}"], response_model=${ENTITY})
async def create_${ENTITY}(entity : ${ENTITY} = Body(embed=False)):
    return handle("fs ${ENTITY} create ", entity.dict())
\n
\n
@app.delete("/${ENTITY}/{idName}", tags=["${ENTITY}"], response_model=${ENTITY})
async def delete_${ENTITY}(idName : str):
    return handle("fs ${ENTITY} delete "+idName)
\n
\n
@app.put("/${ENTITY}/{idName}", tags=["${ENTITY}"], response_model=${ENTITY})
async def update_${ENTITY}(entity : ${ENTITY} = Body(embed=False)):
    return handle("fs ${ENTITY} update "+str(idName)+" ", entity.dict())
\n
\n
% endif
% endfor
\n
\n
# Main
\n
\n
# uvicorn ServicesCatalog:app --reload
def main(argv=None, aepctlServer : str=None):
    if (aepctlServer):
        host = re.sub(":.*", "", aepctlServer)
        port = re.sub(".*:", "", aepctlServer)
    else:
        ## Gets IP and PORT from command line and parses them
        ServerInfo = argparse.ArgumentParser(prog='aepctl server')
        ServerInfo.add_argument("-n", "--host",   default='localhost')
        ServerInfo.add_argument("-p", "--port",   type=int, default='8089')
        ServerInfo = ServerInfo.parse_args(argv)
        host = ServerInfo.host
        port = ServerInfo.port
    if (str(host).strip() == "") : host = "localhost"
    if (str(port).strip() == "") : port = "8080"
    # Start Server
    print("uvicorn on " + str(host) + ":" + str(port))
    logger.info("uvicorn on " + str(host) + ":" + str(port))
    uvicorn.run(app, host=host, port=int(port))
\n
# Development command for realtime updates
# uvicorn ServicesCatalog:app --reload
\n
if __name__ == '__main__' :
    main(argv=sys.argv[1:])
</%def>