<%doc>
    Procedures Template for VoltDB
</%doc>\
// Procedures for ${DATAMODEL}

% for ENTITY in ENTITIES:

function get_${ENTITY}(request) {

        // Call RB AC Hook
        invokeHook("RBAC","GET", request, Null, Null,  'API');
        // Call Validation Hook
        invokeHook("VALIDATE","GET", request, Null, Null, 'API');

        // VoltDB DataStore Access
        ClientResponse response = client.callProcedure("@AdHoc", "Select\
% for PROP in ENTITIES[ENTITY]["properties"]:
${PROP}${'' if loop.last else ', '}\
% endfor
 from ${ENTITY} ;");
        error = Null ;
        if (response.getStatus() != ClientResponse.SUCCESS) {
            error = response.getStatusString();
            }

        // Call Action Hook
        invokeHook("ACTION","GET", request, response, error, 'API');
        // Call RB Filter Hook
        invokeHook("RBFILTER","GET", request, response, error, 'API');
    }


% endfor




