/* THIS IS AUTO GENERATED CODE. DO NOT CHANGE. CHANGE ARCHITECT SOURCE INSTEAD */
\n
package com.openet.servicescatalogmanager.impl;
\n
import com.openet.modules.framework.voltdb.client.VoltClient;
import com.openet.modules.framework.voltdb.client.VoltProcedure;
import com.openet.modules.framework.voltdb.client.impl.VoltClientImpl;
import com.openet.modules.nef.servicescatalogservice.service.api.model.*;
import com.openet.modules.opc.common.enums.HttpStatus;
import com.openet.sba.core.flowcontext.api.FlowContext;
import com.openet.sba.core.provider.annotations.ProviderActivate;
import com.openet.sba.core.provider.annotations.ProviderEnabledComponent;
import com.openet.sba.core.provider.annotations.ProviderInjectedConfig;
import com.openet.sba.core.provider.enums.ProviderEnabledComponentType;
import com.openet.servicescatalogmanager.api.ServicesCatalogManager;
import com.openet.stages.common.exception.NefStageException;
import io.reactivex.Completable;
import io.reactivex.Scheduler;
import io.reactivex.Single;
import io.vertx.core.json.Json;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.voltdb.VoltTable;
import org.voltdb.client.ClientResponse;
\n
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
\n
import static com.openet.modules.opc.common.enums.HttpStatus.INTERNAL_SERVER_ERROR;
import static com.openet.modules.opc.common.enums.HttpStatus.NOT_FOUND;
\n
@ProviderEnabledComponent(configurationPid = "ServicesCatalogManager", componentType = ProviderEnabledComponentType.COMPONENT)
public class ServicesCatalogManagerImpl implements ServicesCatalogManager {
\n
    private final Logger logger = LoggerFactory.getLogger(this.getClass());
\n
    private VoltClient voltClient;
\n
    @ProviderInjectedConfig
    private ServicesCatalogManagerConfig config;
\n
    @ProviderActivate
    public void activate() throws Exception {
        voltClient = new VoltClientImpl(config.getVoltConfig());
    }
\n
% for ENTITY, ENTITY_DATA in ENTITIES.items():
<% className = ENTITY.replace('_', '') %>
% if 'PATH' in ENTITY_DATA:
    @Override
    public Single<${className}> create${className}(${className} entity, FlowContext ctx) {
        entity.setId(UUID.randomUUID().toString());
\n
        String procedureName = "NEF_create${ENTITY}";
        return executeProcedureRx(ctx,
                procedureName,
                entity.getId(),
                Json.encode(entity))
                .doOnSuccess(response -> logResponse(procedureName, response, ctx))
                .doOnSuccess(response -> checkResponseStatus(procedureName, response, ctx))
                .map(response -> entity);
    }
\n
    @Override
    public Single<${className}> get${className}(String id, FlowContext ctx) {
        String procedureName = "NEF_get${ENTITY}";
        return executeProcedureRx(ctx, procedureName, id)
                .doOnSuccess(response -> logResponse(procedureName, response, ctx))
                .doOnSuccess(response -> checkResponseStatus(procedureName, response, ctx))
                .doOnSuccess(response -> checkEntityFoundByRowCount(procedureName, response, ctx))
                .map(response -> {
                    VoltTable table = response.getResults()[0];
                    table.resetRowPosition();
                    table.advanceRow();
\n
                    ${className} entity = Json.decodeValue(table.getString(1), ${className}.class);
                    entity.setId(table.getString(0));
                    return entity;
                });
    }
\n
    @Override
    public Single<List<${className}>> getAll${className}(FlowContext ctx) {
        String procedureName = "NEF_getAll${ENTITY}";
        return executeProcedureRx(ctx, procedureName)
                .doOnSuccess(response -> logResponse(procedureName, response, ctx))
                .doOnSuccess(response -> checkResponseStatus(procedureName, response, ctx))
                .map(response -> {
                    List<${className}> entities = new ArrayList<>();
\n
                    VoltTable table = response.getResults()[0];
                    table.resetRowPosition();
                    while (table.advanceRow()) {
                        ${className} entity = Json.decodeValue(table.getString(1), ${className}.class);
                        entity.setId(table.getString(0));
                        entities.add(entity);
                    }
\n
                    return entities;
                });
    }
\n
    @Override
    public Single<${className}> update${className}(${className} entity, FlowContext ctx) {
        String procedureName = "NEF_update${ENTITY}";
        return executeProcedureRx(ctx,
                procedureName,
                Json.encode(entity),
                entity.getId())
                .doOnSuccess(response -> logResponse(procedureName, response, ctx))
                .doOnSuccess(response -> checkResponseStatus(procedureName, response, ctx))
                .doOnSuccess(response -> checkEntityFoundByModifiedCount(procedureName, response, ctx))
                .map(response -> entity);
    }
\n
    @Override
    public Completable delete${className}(String id, FlowContext ctx) {
        String procedureName = "NEF_delete${ENTITY}";
        return executeProcedureRx(ctx, procedureName, id)
                .doOnSuccess(response -> logResponse(procedureName, response, ctx))
                .doOnSuccess(response -> checkResponseStatus(procedureName, response, ctx))
                .doOnSuccess(response -> checkEntityFoundByModifiedCount(procedureName, response, ctx))
                .ignoreElement();
    }
\n
% endif
% endfor
\n
    private Single<ClientResponse> executeProcedureRx(FlowContext ctx, String name, Object... request) {
        logger.trace(ctx.getMarker(), "executeProcedureRx(name:{}, request:{})", name, request);
        return toRx(executeProcedure(name, request), ctx.getScheduler())
                .onErrorResumeNext(throwable -> Single.error(procedureError(INTERNAL_SERVER_ERROR, name, "error",
                        throwable, ctx)));
    }
\n
    private CompletableFuture<ClientResponse> executeProcedure(String name, Object... request) {
        return voltClient.executeProcedure(new VoltProcedure(name, request));
    }
\n
    public static <T> Single<T> toRx(CompletableFuture<T> future, Scheduler scheduler) {
        Single<T> single = Single.create(emitter -> future
                .thenAccept(emitter::onSuccess)
                .exceptionally(error -> {
                    emitter.onError(error);
                    return null;
                }));
        return single.observeOn(scheduler);
    }
\n
    private void logResponse(String procedureName, ClientResponse clientResponse, FlowContext ctx) {
        logger.trace(ctx.getMarker(), "logResponse(procedureName:{}, status:{}, results:{})", procedureName,
                clientResponse.getStatus(), clientResponse.getResults());
    }
\n
    private void checkResponseStatus(String procedureName, ClientResponse clientResponse, FlowContext ctx) {
        if (clientResponse.getStatus() != ClientResponse.SUCCESS) {
            throw procedureError(INTERNAL_SERVER_ERROR, procedureName, "status",
                    clientResponse.getAppStatusString(), ctx);
        }
    }
\n
    private void checkEntityFoundByRowCount(String procedureName, ClientResponse clientResponse, FlowContext ctx) {
        if (clientResponse.getResults()[0].getRowCount() != 1) {
            throw notFoundError(procedureName, ctx);
        }
    }
\n
    private void checkEntityFoundByModifiedCount(String procedureName, ClientResponse clientResponse, FlowContext ctx) {
        VoltTable table = clientResponse.getResults()[0];
        table.resetRowPosition();
        if (!table.advanceRow() || table.getLong(0) != 1) {
            throw notFoundError(procedureName, ctx);
        }
    }
\n
    private NefStageException notFoundError(String procedureName, FlowContext ctx) {
        return procedureError(NOT_FOUND, procedureName, "error", "No entity found", ctx);
    }

    private NefStageException procedureError(HttpStatus httpStatus, String procedureName, String cause, Object details,
                                             FlowContext ctx) {
        String message = String.format("Procedure '%s' execution failed with %s: %s", procedureName, cause, details);
        logger.error(ctx.getMarker(), message);
        return new NefStageException(httpStatus, null, cause, message);
    }
}
