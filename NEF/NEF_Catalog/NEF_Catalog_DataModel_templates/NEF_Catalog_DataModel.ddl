<%doc>
    DDL Template for VoltDB
</%doc>\
/* DDL for ${DATAMODEL} */

CREATE ROLE @@DOC_PREFIX@@_role WITH sysproc, adhoc, defaultproc;

% for ENTITY in ENTITIES:
/* ${ENTITY} Table */
<%
    PROPS = ENTITIES[ENTITY]["properties"]
%>
CREATE TABLE @@DOC_PREFIX@@_${ENTITY} (
    id VARCHAR(36) NOT NULL,
% for PROP in PROPS:
    ${PROP} VARCHAR(255),
% endfor
    PRIMARY KEY(id)
);
PARTITION TABLE @@DOC_PREFIX@@_${ENTITY} ON COLUMN id;
DR TABLE @@DOC_PREFIX@@_${ENTITY};

CREATE PROCEDURE @@DOC_PREFIX@@_create${ENTITY}
    ALLOW @@DOC_PREFIX@@_role
    PARTITION ON TABLE @@DOC_PREFIX@@_${ENTITY} COLUMN id
    AS INSERT INTO @@DOC_PREFIX@@_${ENTITY} VALUES (?,${','.join(['?' for PROP in PROPS])});

CREATE PROCEDURE @@DOC_PREFIX@@_get${ENTITY}
    ALLOW @@DOC_PREFIX@@_role
    PARTITION ON TABLE @@DOC_PREFIX@@_${ENTITY} COLUMN id
    AS SELECT * FROM @@DOC_PREFIX@@_${ENTITY} WHERE id = ?;

CREATE PROCEDURE @@DOC_PREFIX@@_getAll${ENTITY}
    ALLOW @@DOC_PREFIX@@_role
    AS SELECT * FROM @@DOC_PREFIX@@_${ENTITY};

CREATE PROCEDURE @@DOC_PREFIX@@_update${ENTITY}
    ALLOW @@DOC_PREFIX@@_role
    AS UPDATE @@DOC_PREFIX@@_${ENTITY} SET
% for PROP in PROPS:
        ${PROP} = ?${'' if loop.last else ','}
% endfor
        WHERE id = ?;

CREATE PROCEDURE @@DOC_PREFIX@@_delete${ENTITY}
    ALLOW @@DOC_PREFIX@@_role
    PARTITION ON TABLE @@DOC_PREFIX@@_${ENTITY} COLUMN id
    AS DELETE FROM @@DOC_PREFIX@@_${ENTITY} WHERE id = ?;

% endfor
