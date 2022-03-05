<%def name="generate()">
/* THIS IS AUTO GENERATED CODE. DO NOT CHANGE. CHANGE ARCHITECT SOURCE INSTEAD */
\n
/* DDL for ${DATAMODEL} */
\n
CREATE ROLE @@DOC_PREFIX@@_role WITH sysproc, adhoc, defaultproc;
\n
% for ENTITY, ENTITY_DATA in ENTITIES.items():
% if 'PATH' in ENTITY_DATA:
/* ${ENTITY} Table */
\n
CREATE TABLE @@DOC_PREFIX@@_${ENTITY} (
    id VARCHAR(36) NOT NULL,
    json_data VARCHAR(4096) NOT NULL,
    PRIMARY KEY(id)
);
PARTITION TABLE @@DOC_PREFIX@@_${ENTITY} ON COLUMN id;
DR TABLE @@DOC_PREFIX@@_${ENTITY};
\n
% if ENTITY_DATA['PATH_OPERATION'] != 'read-only':
CREATE PROCEDURE @@DOC_PREFIX@@_create${ENTITY}
    ALLOW @@DOC_PREFIX@@_role
    PARTITION ON TABLE @@DOC_PREFIX@@_${ENTITY} COLUMN id
    AS INSERT INTO @@DOC_PREFIX@@_${ENTITY} VALUES (?,?);
\n
CREATE PROCEDURE @@DOC_PREFIX@@_update${ENTITY}
    ALLOW @@DOC_PREFIX@@_role
    AS UPDATE @@DOC_PREFIX@@_${ENTITY} SET
        json_data = ?
        WHERE id = ?;
\n
CREATE PROCEDURE @@DOC_PREFIX@@_delete${ENTITY}
    ALLOW @@DOC_PREFIX@@_role
    PARTITION ON TABLE @@DOC_PREFIX@@_${ENTITY} COLUMN id
    AS DELETE FROM @@DOC_PREFIX@@_${ENTITY} WHERE id = ?;
\n
% endif
CREATE PROCEDURE @@DOC_PREFIX@@_get${ENTITY}
    ALLOW @@DOC_PREFIX@@_role
    PARTITION ON TABLE @@DOC_PREFIX@@_${ENTITY} COLUMN id
    AS SELECT * FROM @@DOC_PREFIX@@_${ENTITY} WHERE id = ?;
\n
CREATE PROCEDURE @@DOC_PREFIX@@_getAll${ENTITY}
    ALLOW @@DOC_PREFIX@@_role
    AS SELECT * FROM @@DOC_PREFIX@@_${ENTITY}
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
