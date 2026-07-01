from foundry_local_sdk import Configuration, FoundryLocalManager

config = Configuration(app_name= 'local_rag_assistant')
FoundryLocalManager.initialize(config)
manager = FoundryLocalManager.instance

model = manager.catalog.get_model('qwen3-embedding-0.6b')
model.load()

client = model.get_embedding_client()
print('=== embedding client methods ===')
print([a for a in dir(client) if not a.startswith('_')])

model.unload()