<%doc>
    DDL Template for VoltDB
</%doc>\
# DDL for ${DATAMODEL}

% for ENTITY in ENTITIES:
CREATE TABLE ${ENTITY} (
% for PROP in ENTITIES[ENTITY]["properties"]:
    ${PROP}  VARCHAR ${'' if loop.last else ','}
% endfor
);

% endfor


