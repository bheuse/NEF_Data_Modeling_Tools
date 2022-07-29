<%def name="generate(managerName, managerPackageName, servicePackageName)">
/* THIS IS AUTO GENERATED CODE. DO NOT CHANGE. CHANGE ARCHITECT SOURCE INSTEAD */
\n
package com.openet.${managerPackageName}.api;
\n
import com.openet.modules.nef.${servicePackageName}.api.beans.DatastoreApiBeans.*;
import com.openet.modules.nef.${servicePackageName}.api.model.*;
import com.openet.sba.core.flowcontext.api.FlowContext;
import com.openet.sba.core.provider.annotations.ProviderEnabledApi;
import io.reactivex.Completable;
import io.reactivex.Single;
\n
import java.util.List;
\n
@ProviderEnabledApi
public interface ${managerName} {

<%
    # For pagination of list responses the sba generator will generate entities in the format of
    # 'InlineResponse[statusCode][counter]'. We need to increment the counter to reflect entities.
    entity_counter = 0
%>

% for ENTITY, ENTITY_DATA in ENTITIES.items():

<%
    className = ENTITY.replace('_', '')
    list_response_class_name = "InlineResponse200" + (str(entity_counter) if entity_counter != 0 else '')
%>

% if 'PATH' in ENTITY_DATA:
\n
% if ENTITY_DATA['PATH_OPERATION'] != 'read-only':
    Single<${className}> create${className}(${className} entity, FlowContext ctx);
    Single<${className}> update${className}(${className} entity, FlowContext ctx);
    Completable delete${className}(String id, FlowContext ctx);
% endif
    Single<${className}> get${className}(String id, FlowContext ctx);
    Single<${list_response_class_name}> getAll${className}(Get${className}sQueryParams queryParams, FlowContext ctx);
<% entity_counter += 1 %>
% endif
% endfor
}
</%def>
