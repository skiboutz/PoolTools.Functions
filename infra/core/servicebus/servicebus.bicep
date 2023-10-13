param serviceBusNamespaceName string
param location string
param tags object = {}
param queues array = []
param topics array = []

resource serviceBusNamespace 'Microsoft.ServiceBus/namespaces@2022-10-01-preview' = {
  name: serviceBusNamespaceName
  location: location
  tags: tags
  sku: {
    name: 'Standard'
    tier: 'Standard'
    capacity: 1
  }
}

resource sbQueues 'Microsoft.ServiceBus/namespaces/queues@2021-11-01' =  [ for queue in queues: {
  parent: serviceBusNamespace
  name: queue.name
}]

resource sbTopics 'Microsoft.ServiceBus/namespaces/topics@2021-11-01' =  [ for topic in topics: {
  parent: serviceBusNamespace
  name: topic.name
}]


output namespaceEndpoint string = serviceBusNamespace.properties.serviceBusEndpoint
output namespaceFqdn string = '${serviceBusNamespace.name}.servicebus.windows.net'
