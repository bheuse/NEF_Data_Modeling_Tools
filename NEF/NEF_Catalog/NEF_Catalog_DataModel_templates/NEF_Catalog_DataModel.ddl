<%doc>
    DDL Template for VoltDB
</%doc>

/* DDL for ${DATAMODEL} */
\n
CREATE ROLE @@DOC_PREFIX@@_role WITH sysproc, adhoc, defaultproc;
\n
% for ENTITY in ENTITIES:

<% PROPS = ENTITIES[ENTITY]["properties"] %>

/* ${ENTITY} Table */
\n
CREATE TABLE @@DOC_PREFIX@@_${ENTITY} (
    id VARCHAR(36) NOT NULL,
% for name, data in PROPS.items():
    ${renderProp(name, data)}
% endfor
    PRIMARY KEY(id)
);
PARTITION TABLE @@DOC_PREFIX@@_${ENTITY} ON COLUMN id;
DR TABLE @@DOC_PREFIX@@_${ENTITY};
\n
CREATE PROCEDURE @@DOC_PREFIX@@_create${ENTITY}
    ALLOW @@DOC_PREFIX@@_role
    PARTITION ON TABLE @@DOC_PREFIX@@_${ENTITY} COLUMN id
    AS INSERT INTO @@DOC_PREFIX@@_${ENTITY} VALUES ${renderPropsValues(PROPS)};
\n
CREATE PROCEDURE @@DOC_PREFIX@@_get${ENTITY}
    ALLOW @@DOC_PREFIX@@_role
    PARTITION ON TABLE @@DOC_PREFIX@@_${ENTITY} COLUMN id
    AS SELECT * FROM @@DOC_PREFIX@@_${ENTITY} WHERE id = ?;
\n
CREATE PROCEDURE @@DOC_PREFIX@@_getAll${ENTITY}
    ALLOW @@DOC_PREFIX@@_role
    AS SELECT * FROM @@DOC_PREFIX@@_${ENTITY};
\n
CREATE PROCEDURE @@DOC_PREFIX@@_update${ENTITY}
    ALLOW @@DOC_PREFIX@@_role
    AS UPDATE @@DOC_PREFIX@@_${ENTITY} SET
% for name, data in PROPS.items():
        ${renderSetProp(name, data, loop.last)}
% endfor
        WHERE id = ?;
\n
CREATE PROCEDURE @@DOC_PREFIX@@_delete${ENTITY}
    ALLOW @@DOC_PREFIX@@_role
    PARTITION ON TABLE @@DOC_PREFIX@@_${ENTITY} COLUMN id
    AS DELETE FROM @@DOC_PREFIX@@_${ENTITY} WHERE id = ?;
\n
% endfor

<%doc>
    Utilities
</%doc>

<%!
    def getEntity(entities, propData):
        return entities[propData['$ref'].split('/')[-1]] if '$ref' in propData else None

    def countProps(entities, props):
        counter = 0

        for name, data in props.items():
            entity = getEntity(entities, data)
            if entity and not 'PATH' in entity: # subobject
                counter += countProps(entities, entity["properties"])
            else:
                counter += 1

        return counter

    def doRenderPropsValues(entities, props):
        return '(?,' + ','.join(['?' for i in range(0, countProps(entities, props))]) + ')'
%>

<%def name="renderProp(name, data)">
<% entity = getEntity(ENTITIES, data) %>
% if not entity: # primitive type
    ${name} VARCHAR,
% elif 'PATH' in entity: # reference to another entity
    ${name} VARCHAR(36),
% else: # subobject
    % for subname, subdata in entity["properties"].items():
        ${renderProp(name + '_' + subname, subdata)}
    % endfor
% endif
</%def>

<%def name="renderPropsValues(props)">${doRenderPropsValues(ENTITIES, props)}</%def>

<%def name="renderSetProp(name, data, last)">
<% entity = getEntity(ENTITIES, data) %>
% if entity and not 'PATH' in entity: # subobject
    % for subname, subdata in entity["properties"].items():
        ${renderSetProp(name + '_' + subname, subdata, last)}
    % endfor
% else:
        ${name} = ?${'' if last else ','}
% endif
</%def>
