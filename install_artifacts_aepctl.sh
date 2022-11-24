#! /usr/bin/bash

function generate() {
    architect=$1
    python data_model_to_openapi.py -r -y -o -s -d -m $architect -i NEF/include
}

# Services Catalog Service

generate NEF/NEF_Catalog/NEF_Catalog_DataModel

# API
echo "Copying NEF_Catalog for NEF_AepCtl ..."
cp \
    NEF/NEF_Catalog/NEF_Catalog_DataModel_artifacts/NEF_Catalog_DataModel_API.yaml \
    ../NEF_AepCtl/etc/NEF_Catalog_DataModel
# Schema
cp \
    NEF/NEF_Catalog/NEF_Catalog_DataModel_artifacts/_Schemas/* \
    ../NEF_AepCtl/etc/NEF_Catalog_DataModel/_Schemas

# Application User Profile Service

generate NEF/NEF_ApplicationUserProfile/NEF_ApplicationUserProfile_DataModel

# API
echo "Copying NEF_ApplicationUserProfile for NEF_AepCtl ..."
cp \
    NEF/NEF_ApplicationUserProfile/NEF_ApplicationUserProfile_DataModel_artifacts/NEF_ApplicationUserProfile_DataModel_API.yaml \
    ../NEF_AepCtl/etc/NEF_ApplicationUserProfile_DataModel
# Schema
cp \
    NEF/NEF_ApplicationUserProfile/NEF_ApplicationUserProfile_DataModel_artifacts/_Schemas/* \
    ../NEF_AepCtl/etc/NEF_ApplicationUserProfile_DataModel/_Schemas