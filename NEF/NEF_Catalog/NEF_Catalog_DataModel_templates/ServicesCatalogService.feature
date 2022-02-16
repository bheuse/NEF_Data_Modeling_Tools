# THIS IS AUTO GENERATED CODE. DO NOT CHANGE. CHANGE ARCHITECT SOURCE INSTEAD
\n
@ServicesCatalogService
Feature: Services Catalog Service operations
\n
  Background:
    * url apiBaseUrl
<% deleteFromTablesQuery = '; '.join(['DELETE FROM NEF_' + ENTITY for ENTITY, ENTITY_DATA in ENTITIES.items() if 'PATH' in ENTITY_DATA]) %>
    * configure afterScenario =
      """
      function() {
        commandLineUtil('docker exec voltdb-nef-data-model sqlcmd --query="${deleteFromTablesQuery};"')
      }
      """
\n
% for ENTITY, ENTITY_DATA in ENTITIES.items():

% if 'PATH' in ENTITY_DATA and ENTITY_DATA['PATH_OPERATION'] != 'read-only':

<% path = ENTITY_DATA['PATH'] + 's' %>

  Scenario: Get ${ENTITY} by id
    Given path '/datastore/${path}'
    And def entity =
      """
      ${generateEntityJson(ENTITY_DATA)}
      """
    And request entity
    When method post
    And print response
    And status 202
    And eval entity.id = response.id
    Then match response == entity
\n
    Given path '/datastore/${path}/' + entity.id
    When method get
    And print response
    And status 200
    Then match response == entity
\n
  Scenario: Get ${ENTITY} by id not found
    Given path '/datastore/${path}/dummy'
    When method get
    And print response
    And status 404
\n
  Scenario: Get All ${ENTITY}
    When def entity =
      """
      ${generateEntityJson(ENTITY_DATA)}
      """
\n
    Given path '/datastore/${path}'
    And request entity
    When method post
    And print response
    And status 202
\n
    Given path '/datastore/${path}'
    And request entity
    When method post
    And print response
    And status 202
\n
    Given path '/datastore/${path}'
    When method get
    Then status 200
    And print response
    And assert response.length == 2
\n
  Scenario: Update ${ENTITY} by id
    Given path '/datastore/${path}'
    And request
      """
      ${generateEntityJson(ENTITY_DATA)}
      """
    When method post
    And print response
    And status 202
\n
    And def updatedEntity =
      """
      ${generateEntityJson(ENTITY_DATA)}
      """
    And eval updatedEntity.id = response.id
\n
    Given path '/datastore/${path}/' + updatedEntity.id
    And request updatedEntity
    When method put
    And print response
    And status 202
    Then match response == updatedEntity
\n
  Scenario: Update ${ENTITY} by id not found
    Given path '/datastore/${path}/dummy'
    And request
      """
      ${generateEntityJson(ENTITY_DATA)}
      """
    When method put
    And print response
    And status 404
\n
  Scenario: Delete ${ENTITY} by id
    Given path '/datastore/${path}'
    And request
      """
      ${generateEntityJson(ENTITY_DATA)}
      """
    When method post
    And print response
    And status 202
    And def id = response.id
\n
    Given path '/datastore/${path}/' + id
    When method delete
    And print response
    And status 204
\n
    Given path '/datastore/${path}/' + id
    When method get
    And print response
    And status 404
\n
  Scenario: Delete ${ENTITY} by id not found
    Given path '/datastore/${path}/dummy'
    When method delete
    And print response
    And status 404
\n
% endif
% endfor

<%def name="generateEntityJson(entityData)">
<%
    import random, string

    def randomString(length=10):
        letters = string.ascii_lowercase
        return ''.join(random.choice(letters) for i in range(length))

    def randomBoolean():
        return random.choice([True, False])

    def randomInt(begin=0, end=100):
        return random.randint(begin, end)

    def now():
        import datetime
        return datetime.datetime.now().replace(microsecond=0).isoformat() + 'Z'

    def randomValue(type, format, subType, subFormat):
        if type == 'string':
            return now() if format == 'date-time' else randomString()
        elif type == 'boolean':
            return randomBoolean()
        elif type == 'integer':
            return randomInt()
        elif type == 'array':
            return [randomValue(subType, subFormat, None, None)]
        else:
            return None
        
    def doGenerateEntity(entityData):
        entity = {}

        for prop, propData in entityData['properties'].items():
            if '$ref' in propData:
                subEntity = propData['$ref'].split('/')[-1]
                entity[prop] = doGenerateEntity(ENTITIES[subEntity])
            else:
                type = propData['type']
                format = propData['format'] if 'format' in propData else None
                subType = None
                subFormat = None
                if type == 'array':
                    items = propData['items']
                    subType   = items['type']   if 'type'   in items else 'string'
                    subFormat = items['format'] if 'format' in items else None

                entity[prop] = randomValue(type, format, subType, subFormat)

        return entity

    def doGenerateEntityJson(entityData):
        import json
        return json.dumps(doGenerateEntity(entityData), indent=2)
%>
    % for line in doGenerateEntityJson(entityData).splitlines():
      ${line}
    % endfor
</%def>
