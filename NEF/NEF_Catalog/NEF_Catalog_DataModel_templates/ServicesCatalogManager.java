<%doc>
    DDL Template for VoltDB
</%doc>
/* THIS IS AUTO GENERATED CODE. DO NOT CHANGE. CHANGE ARHITECT SOURCE INSTEAD */
\n
package com.openet.servicescatalogmanager.api;
\n
import com.openet.modules.nef.servicescatalogservice.service.api.model.*;
import com.openet.sba.core.flowcontext.api.FlowContext;
import com.openet.sba.core.provider.annotations.ProviderEnabledApi;
import io.reactivex.Completable;
import io.reactivex.Single;
\n
import java.util.List;
\n
@ProviderEnabledApi
public interface ServicesCatalogManager {
% for entityName, entityData in ENTITIES.items():
<% entity = entityName.replace('_', '') %>
% if 'PATH' in entityData:
\n
    Single<${entity}> create${entity}(${entity} entity, FlowContext ctx);
    Single<${entity}> get${entity}(String id, FlowContext ctx);
    Single<List<${entity}>> getAll${entity}(FlowContext ctx);
    Single<${entity}> update${entity}(${entity} entity, FlowContext ctx);
    Completable delete${entity}(String id, FlowContext ctx);
%endif
% endfor
}
