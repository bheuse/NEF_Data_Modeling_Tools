#! /usr/bin/bash

function generate() {
    architect=$1
    python data_model_to_openapi.py -r -y -o -s -d -m $architect -i NEF/include
}

# Services Catalog Service

generate NEF/NEF_Catalog/NEF_Catalog_DataModel

# API
cp \
    NEF/NEF_Catalog/NEF_Catalog_DataModel_artifacts/NEF_Catalog_DataModel_API.yaml \
    ../services-catalog-service-api/services-catalog-service-api/src/main/resources
# DDL
cp \
    NEF/NEF_Catalog/NEF_Catalog_DataModel_artifacts/ServicesCatalog.sql \
    ../voltdb-nef-catalog/voltdb-nef-catalog-template/src/main/resources/ddl
# Manager
cp \
    NEF/NEF_Catalog/NEF_Catalog_DataModel_artifacts/ServicesCatalogManager.java \
    ../services-catalog-manager/services-catalog-manager-api/src/main/java/com/openet/servicescatalogmanager/api
cp \
    NEF/NEF_Catalog/NEF_Catalog_DataModel_artifacts/ServicesCatalogManagerImpl.java \
    ../services-catalog-manager/services-catalog-manager-impl/src/main/java/com/openet/servicescatalogmanager/impl
# Service
cp \
    NEF/NEF_Catalog/NEF_Catalog_DataModel_artifacts/DatastoreApiServiceImpl.java \
    ../services-catalog-service-service/services-catalog-service-service-impl/src/main/java/com/openet/modules/nef/servicescatalogservice/service/service/impl
# System tests
cp \
    NEF/NEF_Catalog/NEF_Catalog_DataModel_artifacts/ServicesCatalogService.feature \
    ../services-catalog-service-packager/services-catalog-service-system-test/src/test/java/com/openet/services_catalog_service/test/features

# Application User Profile Service

generate NEF/NEF_ApplicationUserProfile/NEF_ApplicationUserProfile_DataModel

# API
cp \
    NEF/NEF_ApplicationUserProfile/NEF_ApplicationUserProfile_DataModel_artifacts/NEF_ApplicationUserProfile_DataModel_API.yaml \
    ../application-user-profile-service-api/application-user-profile-service-api/src/main/resources
# DDL
cp \
    NEF/NEF_ApplicationUserProfile/NEF_ApplicationUserProfile_DataModel_artifacts/ApplicationUserProfile.sql \
    ../voltdb-nef-catalog/voltdb-nef-catalog-template/src/main/resources/ddl
# Manager
cp \
    NEF/NEF_ApplicationUserProfile/NEF_ApplicationUserProfile_DataModel_artifacts/ApplicationUserProfileManager.java \
    ../application-user-profile-manager/application-user-profile-manager-api/src/main/java/com/openet/applicationuserprofilemanager/api
cp \
    NEF/NEF_ApplicationUserProfile/NEF_ApplicationUserProfile_DataModel_artifacts/ApplicationUserProfileManagerImpl.java \
    ../application-user-profile-manager/application-user-profile-manager-impl/src/main/java/com/openet/applicationuserprofilemanager/impl
