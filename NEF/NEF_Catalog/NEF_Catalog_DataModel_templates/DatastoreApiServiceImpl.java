/* THIS IS AUTO GENERATED CODE. DO NOT CHANGE. CHANGE ARCHITECT SOURCE INSTEAD */
\n
package com.openet.modules.nef.servicescatalogservice.service.service.impl;
\n
import com.openet.fusionworks.component.statistics.StatisticsInterface;
import com.openet.fusionworks.component.statistics.StatisticsInterfaceProvider;
import com.openet.modules.deployment.config.api.DeploymentConfigApi;
import com.openet.modules.deployment.config.api.DeploymentConfigFields;
import com.openet.modules.framework.vertx.core.common.ApiResponse;
import com.openet.modules.nef.servicescatalogservice.service.api.model.*;
import com.openet.modules.nef.servicescatalogservice.service.api.service.DatastoreApiService;
import com.openet.sba.core.flowcontext.api.FlowContext;
import com.openet.servicescatalogmanager.api.provider.ServicesCatalogManagerProvider;
import com.openet.stages.common.exception.CatchAllErrorWrapper;
import io.reactivex.Single;
import org.osgi.service.component.annotations.Activate;
import org.osgi.service.component.annotations.Component;
import org.osgi.service.component.annotations.Modified;
import org.osgi.service.component.annotations.Reference;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
\n
import java.util.List;
import java.util.Map;
\n
@Component(property = "type=native", configurationPid = "NefServicesCatalogService.DatastoreApiService")
@javax.annotation.Generated(value = "com.openet.sba.codegen.rest.ms.codegen.service.VertxOsgiServiceCodegen", date = "2022-01-28T10:21:26.450+03:00[Europe/Moscow]")
public class DatastoreApiServiceImpl implements DatastoreApiService {
\n
    private Logger logger = LoggerFactory.getLogger(this.getClass());
\n
    @Reference
    private StatisticsInterfaceProvider statisticsInterfaceProvider;
    private StatisticsInterface statistics;
\n
    @Reference
    private DeploymentConfigApi deploymentConfigApi;
\n
    @Reference
    private ServicesCatalogManagerProvider servicesCatalogManagerProvider;
\n
    @Activate
    public void activate(Map<String, Object> config) {
        statistics = statisticsInterfaceProvider.getInterface((String) config.get(DeploymentConfigFields.NAME));
    }
\n
    @Modified
    public void modified(Map<String, Object> config) {
    }
\n
% for ENTITY, ENTITY_DATA in ENTITIES.items():
<% className = ENTITY.replace('_', '') %>
% if 'PATH' in ENTITY_DATA:

% if ENTITY_DATA['PATH_OPERATION'] != 'read-only':
    @Override
    public Single<ApiResponse<${className}>> create${className}(Create${className}ServiceData serviceData, FlowContext ctx) {
        logger.trace(ctx.getMarker(), "create${className}()");
\n
        return servicesCatalogManagerProvider.get()
                .create${className}(serviceData.getRequest(), ctx)
                .map(entity -> new ApiResponse<>(entity))
                .onErrorResumeNext(error -> createErrorReply(error));
    }
\n
    @Override
    public Single<ApiResponse<Void>> update${className}(Update${className}ServiceData serviceData, FlowContext ctx) {
        logger.trace(ctx.getMarker(), "update${className}()");
\n
        serviceData.getRequest()
                .setId(serviceData.getPathParams().getId());
\n
        return servicesCatalogManagerProvider.get()
                .update${className}(serviceData.getRequest(), ctx)
                .map(entity -> new ApiResponse<Void>())
                .onErrorResumeNext(error -> createErrorReply(error));
    }
\n
    @Override
    public Single<ApiResponse<Void>> delete${className}(Delete${className}ServiceData serviceData, FlowContext ctx) {
        logger.trace(ctx.getMarker(), "delete${className}()");
\n
        return servicesCatalogManagerProvider.get()
                .delete${className}(serviceData.getPathParams().getId(), ctx)
                .andThen(Single.just(new ApiResponse<Void>()))
                .onErrorResumeNext(error -> createErrorReply(error));
    }
\n
% endif
    @Override
    public Single<ApiResponse<${className}>> get${className}(Get${className}ServiceData serviceData, FlowContext ctx) {
        logger.trace(ctx.getMarker(), "get${className}()");
\n
        return servicesCatalogManagerProvider.get()
                .get${className}(serviceData.getPathParams().getId(), ctx)
                .map(entity -> new ApiResponse<>(entity))
                .onErrorResumeNext(error -> createErrorReply(error));
    }
\n
    @Override
    public Single<ApiResponse<List<${className}>>> get${className}s(Get${className}sServiceData serviceData, FlowContext ctx) {
        logger.trace(ctx.getMarker(), "get${className}s()");
\n
        return servicesCatalogManagerProvider.get()
                .getAll${className}(ctx)
                .map(entities -> new ApiResponse<>(entities))
                .onErrorResumeNext(error -> createErrorReply(error));
    }
\n
% endif
% endfor
    private <T> Single<T> createErrorReply(Throwable throwable) {
        CatchAllErrorWrapper error = new CatchAllErrorWrapper(throwable);
        return Single.error(error);
    }
}
