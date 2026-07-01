from foundry_local_sdk import Configuration, FoundryLocalManager

config = Configuration(app_name='local_rag_assistant')
FoundryLocalManager.initialize(config)
manager = FoundryLocalManager.instance

print('=== catalog attributes ===')
print([a for a in dir(manager.catalog) if not a.startswith('_')])

print()
print('=== list_models() ===')
models = manager.catalog.list_models()
print('type:', type(models))
print('count:', len(models))
print()
print('=== first entry ===')
first = models[0]
print('type:', type(first))
print('attributes:', [a for a in dir(first) if not a.startswith('_')])

print()
print('=== alias : capabilities ===')
for m in models:
    print(f'{m.alias:35} : {m.capabilities}')