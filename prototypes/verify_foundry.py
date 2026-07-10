from foundry_local_sdk import Configuration, FoundryLocalManager

config = Configuration(app_name='local_rag_assistant')
FoundryLocalManager.initialize(config)
manager = FoundryLocalManager.instance

model = manager.catalog.get_model('qwen2.5-0.5b')

print('Downloading model (first run only, may take a few minutes)...')
model.download()

print('Loading model into memory...')
model.load()

try:
    client = model.get_chat_client()
    response = client.complete_chat(
        [{'role': 'user', 'content': 'In one short sentence, what is local AI?'}]
    )
    print()
    print('=== MODEL REPLY ===')
    print(response.choices[0].message.content)
    print('===================')
finally:
    model.unload()
    print('Model unloaded. Done.')
