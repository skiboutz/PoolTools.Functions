param name string
param location string = resourceGroup().location
param tags object = {}

param allowedOrigins array = []
param applicationInsightsName string = ''
param appServicePlanId string
param appSettings object = {}
param keyVaultName string
param serviceName string = 'pooltools-functions'
param storageAccountName string

module api '../core/host/functions.bicep' = {
  name: serviceName
  params: {
    name: name
    location: location
    tags: union(tags, { 'azd-service-name': serviceName })
    allowedOrigins: allowedOrigins
    alwaysOn: false
    appSettings: union(appSettings, { EXPORT_AZURE_STORAGE_CONNECTION_STRING: 'DefaultEndpointsProtocol=https;AccountName=${storage.name};AccountKey=${storage.listKeys().keys[0].value};EndpointSuffix=${environment().suffixes.storage}'})
    applicationInsightsName: applicationInsightsName
    appServicePlanId: appServicePlanId
    keyVaultName: keyVaultName
    runtimeName: 'python'
    runtimeVersion: '3.9'
    storageAccountName: storageAccountName
    scmDoBuildDuringDeployment: true
  }
}

resource storage 'Microsoft.Storage/storageAccounts@2021-09-01' existing = {
  name: storageAccountName
}

var serviceBusDataSenderRoleId = '69a216fc-b8fb-44d8-bc22-1f3c2cd27a39'

module apiServiceBusDataSender '../core/security/role.bicep' = {
  name: 'apiServiceBusRbac'
  params:{
    principalId: api.outputs.identityPrincipalId
    roleDefinitionId: serviceBusDataSenderRoleId
    principalType: 'ServicePrincipal'
  }
}

output SERVICE_API_IDENTITY_PRINCIPAL_ID string = api.outputs.identityPrincipalId
output SERVICE_API_NAME string = api.outputs.name
output SERVICE_API_URI string = api.outputs.uri
