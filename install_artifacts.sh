#! /usr/bin/bash

# Services Catalog Service

cd NEF/NEF_Catalog
python ../../data_model_to_openapi.py NEF_Catalog_DataModel
cd ../..

# API
cp NEF/NEF_Catalog/NEF_Catalog_DataModel_artifacts/NEF_Catalog_DataModel_API.yaml ../services-catalog-service-api/services-catalog-service-api/src/main/resources
# DDL
cp NEF/NEF_Catalog/NEF_Catalog_DataModel_artifacts/ServicesCatalog.sql ../voltdb-nef-catalog/voltdb-nef-catalog-template/src/main/resources/ddl
# Manager
cp NEF/NEF_Catalog/NEF_Catalog_DataModel_artifacts/ServicesCatalogManager.java ../services-catalog-manager/services-catalog-manager-api/src/main/java/com/openet/servicescatalogmanager/api
cp NEF/NEF_Catalog/NEF_Catalog_DataModel_artifacts/ServicesCatalogManagerImpl.java ../services-catalog-manager/services-catalog-manager-impl/src/main/java/com/openet/servicescatalogmanager/impl
# Service
cp NEF/NEF_Catalog/NEF_Catalog_DataModel_artifacts/DatastoreApiServiceImpl.java ../services-catalog-service-service/services-catalog-service-service-impl/src/main/java/com/openet/modules/nef/servicescatalogservice/service/service/impl
# System tests
cp NEF/NEF_Catalog/NEF_Catalog_DataModel_artifacts/ServicesCatalogService.feature ../services-catalog-service-packager/services-catalog-service-system-test/src/test/java/com/openet/services_catalog_service/test/features
