from foundry_local_sdk import Configuration, FoundryLocalManager

config = Configuration(app_name = 'local_rag_assistant')
FoundryLocalManager.initialize(config)
manager = FoundryLocalManager.instance

model = manager.catalog.get_model('qwen3-embedding-0.6b')
print('Downloading embedding model ( first run only, may take a few minutes)...')
model.download()
print('Loading model into memory...')
model.load()

client = model.get_embedding_client()
text = ' Foundry Local runs language models on your own device.'
response = client.generate_embedding(text)
vector = response.data[0].embedding

try:
    print()
    print('=== EMBEDDING RESULT ===')
    print('text:', text)
    print('vector length:', len(vector))
    print('first 5 numbers:', vector[:5])
    print('type of one number:', type(vector[0]))
    print('========================')
finally:
    model.unload()
    print('Model unloaded. Done.')