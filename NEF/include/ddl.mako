<%def name="generate(shortServiceName)">
<% prefix = '@@DOC_PREFIX@@_' + shortServiceName %>
/* THIS IS AUTO GENERATED CODE. DO NOT CHANGE. CHANGE ARCHITECT SOURCE INSTEAD */
\n
/* DDL for ${DATAMODEL} */
\n
CREATE ROLE ${prefix}_role WITH sysproc, adhoc, defaultproc;
\n
% for ENTITY, ENTITY_DATA in ENTITIES.items():
% if 'PATH' in ENTITY_DATA:
/* ${ENTITY} Table */
\n
CREATE TABLE ${prefix}_${ENTITY} (
    id VARCHAR(36) NOT NULL,
    json_data VARCHAR(4096) NOT NULL,
    PRIMARY KEY(id)
);
PARTITION TABLE ${prefix}_${ENTITY} ON COLUMN id;
DR TABLE ${prefix}_${ENTITY};
\n
% if ENTITY_DATA['PATH_OPERATION'] != 'read-only':
CREATE PROCEDURE ${prefix}_create${ENTITY}
    ALLOW ${prefix}_role
    PARTITION ON TABLE ${prefix}_${ENTITY} COLUMN id
    AS INSERT INTO ${prefix}_${ENTITY} VALUES (?,?);
\n
CREATE PROCEDURE ${prefix}_update${ENTITY}
    ALLOW ${prefix}_role
    AS UPDATE ${prefix}_${ENTITY} SET
        json_data = ?
        WHERE id = ?;
\n
CREATE PROCEDURE ${prefix}_delete${ENTITY}
    ALLOW ${prefix}_role
    PARTITION ON TABLE ${prefix}_${ENTITY} COLUMN id
    AS DELETE FROM ${prefix}_${ENTITY} WHERE id = ?;
\n
% endif
CREATE PROCEDURE ${prefix}_get${ENTITY}
    ALLOW ${prefix}_role
    PARTITION ON TABLE ${prefix}_${ENTITY} COLUMN id
    AS SELECT * FROM ${prefix}_${ENTITY} WHERE id = ?;
\n
CREATE PROCEDURE ${prefix}_getAll${ENTITY}
    ALLOW ${prefix}_role
    AS SELECT * FROM ${prefix}_${ENTITY}
        ${generateWhere(ENTITY_DATA)}
        ORDER BY id
        LIMIT ?
        OFFSET ?;
\n
% endif
% endfor
</%def>

<%def name="generateWhere(entityData)">
<%
    def isFilterParam(propData):
        return 'Schema' in propData and propData['Schema']['filter']

    def countFilterParams(entityData):
        counter = 0
        for prop, propData in entityData['properties'].items():
            if isFilterParam(propData):
                counter += 1
        return counter

    filterParamCount = countFilterParams(entityData)
%>
% if filterParamCount:
        WHERE
        % for prop, propData in entityData['properties'].items():
            % if isFilterParam(propData):
            field(json_data, '${prop}') = (CASE WHEN CAST(? as varchar) IS NOT NULL THEN CAST(? as varchar) ELSE field(json_data, '${prop}') END) ${'AND' if filterParamCount > 1 else ''}
            <% filterParamCount -= 1 %>
            % endif
        % endfor
% endif
</%def>
