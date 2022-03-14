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
% for ENTITY, ENTITY_DATA in ENTITIES.items():
<% className = ENTITY.replace('_', '') %>
% if 'PATH' in ENTITY_DATA:
\n
% if ENTITY_DATA['PATH_OPERATION'] != 'read-only':
    Single<${className}> create${className}(${className} entity, FlowContext ctx);
    Single<${className}> update${className}(${className} entity, FlowContext ctx);
    Completable delete${className}(String id, FlowContext ctx);
% endif
    Single<${className}> get${className}(String id, FlowContext ctx);
    Single<List<${className}>> getAll${className}(Get${className}sQueryParams queryParams, FlowContext ctx);
% endif
% endfor
}
</%def>
