<%def name="generate(serviceName, servicePackageName, shortServiceName, pidPrefix, managerName, managerPackageName)">
/* THIS IS AUTO GENERATED CODE. DO NOT CHANGE. CHANGE ARCHITECT SOURCE INSTEAD */
\n
package com.openet.modules.nef.${servicePackageName}.service.impl;
\n
import com.openet.fusionworks.component.statistics.StatisticsInterface;
import com.openet.fusionworks.component.statistics.StatisticsInterfaceProvider;
import com.openet.modules.deployment.config.api.DeploymentConfigApi;
import com.openet.modules.deployment.config.api.DeploymentConfigFields;
import com.openet.modules.framework.vertx.core.common.ApiResponse;
import com.openet.modules.nef.${servicePackageName}.api.model.*;
import com.openet.modules.nef.${servicePackageName}.api.service.DatastoreApiService;
import com.openet.sba.core.flowcontext.api.FlowContext;
import com.openet.sba.core.http.headers.MultiMap;
import com.openet.${managerPackageName}.api.provider.${managerName}Provider;
import com.openet.stages.auth.api.AuthStageInput;
import com.openet.stages.auth.api.AuthStageOutput;
import com.openet.stages.auth.api.provider.AuthStageProvider;
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
import static com.openet.stages.auth.api.Role.*;
\n
@Component(property = "type=native", configurationPid = "${pidPrefix}.${serviceName}")
@javax.annotation.Generated(value = "com.openet.sba.codegen.rest.ms.codegen.service.VertxOsgiServiceCodegen", date = "2022-01-28T10:21:26.450+03:00[Europe/Moscow]")
public class ${serviceName}Impl implements ${serviceName} {
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
    private AuthStageProvider authStageProvider;
\n
<% managerProviderName = managerName[0].lower() + managerName[1:] + 'Provider' %>
    @Reference
    private ${managerName}Provider ${managerProviderName};
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
        return Single
                .defer(() -> authorize(ctx, serviceData.getRequestHeaders(), ROLE_${shortServiceName}_CREATE))
                .flatMap(output -> ${managerProviderName}.get().create${className}(serviceData.getRequest(), ctx))
                .map(entity -> new ApiResponse<>(entity))
                .onErrorResumeNext(error -> createErrorReply(error));
    }
\n
    @Override
    public Single<ApiResponse<${className}>> update${className}(Update${className}ServiceData serviceData, FlowContext ctx) {
        logger.trace(ctx.getMarker(), "update${className}()");
\n
        serviceData.getRequest()
                .setId(serviceData.getPathParams().getId());
\n
        return Single
                .defer(() -> authorize(ctx, serviceData.getRequestHeaders(), ROLE_${shortServiceName}_UPDATE))
                .flatMap(output -> ${managerProviderName}.get().update${className}(serviceData.getRequest(), ctx))
                .map(entity -> new ApiResponse<>(entity))
                .onErrorResumeNext(error -> createErrorReply(error));
    }
\n
    @Override
    public Single<ApiResponse<Void>> delete${className}(Delete${className}ServiceData serviceData, FlowContext ctx) {
        logger.trace(ctx.getMarker(), "delete${className}()");
\n
        return Single
                .defer(() -> authorize(ctx, serviceData.getRequestHeaders(), ROLE_${shortServiceName}_DELETE))
                .flatMap(output -> ${managerProviderName}.get().delete${className}(serviceData.getPathParams().getId(), ctx)
                        .andThen(Single.just(new ApiResponse<Void>())))
                .onErrorResumeNext(error -> createErrorReply(error));
    }
\n
% endif
    @Override
    public Single<ApiResponse<${className}>> get${className}(Get${className}ServiceData serviceData, FlowContext ctx) {
        logger.trace(ctx.getMarker(), "get${className}()");
\n
        return Single
                .defer(() -> authorize(ctx, serviceData.getRequestHeaders(), ROLE_${shortServiceName}_READ))
                .flatMap(output -> ${managerProviderName}.get().get${className}(serviceData.getPathParams().getId(), ctx))
                .map(entity -> new ApiResponse<>(entity))
                .onErrorResumeNext(error -> createErrorReply(error));
    }
\n
    @Override
    public Single<ApiResponse<List<${className}>>> get${className}s(Get${className}sServiceData serviceData, FlowContext ctx) {
        logger.trace(ctx.getMarker(), "get${className}s()");
\n
        return Single
                .defer(() -> authorize(ctx, serviceData.getRequestHeaders(), ROLE_${shortServiceName}_READ))
                .flatMap(output -> ${managerProviderName}.get().getAll${className}(serviceData.getQueryParams(), ctx))
                .map(entities -> new ApiResponse<>(entities))
                .onErrorResumeNext(error -> createErrorReply(error));
    }
\n
% endif
% endfor
    private Single<AuthStageOutput> authorize(FlowContext ctx, MultiMap requestHeaders,
                                              com.openet.stages.auth.api.Role role) {
        AuthStageInput stageInput = new AuthStageInput()
                .setAuthorizationHeader(requestHeaders.get("Authorization"))
                .setRole(role);
\n
        return authStageProvider.get().execute(stageInput, ctx);
    }
\n
    private <T> Single<T> createErrorReply(Throwable throwable) {
        CatchAllErrorWrapper error = new CatchAllErrorWrapper(throwable);
        return Single.error(error);
    }
}
</%def>
