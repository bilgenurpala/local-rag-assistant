from foundry_local_sdk import Configuration, FoundryLocalManager

config = Configuration(app_name='local_rag_assistant')
FoundryLocalManager.initialize(config)
manager = FoundryLocalManager.instance

model = manager.catalog.get_model('qwen2.5-0.5b')
print('Loading chat model...')
model.download()
model.load()
client = model.get_chat_client()

question = 'What license does the Contoso Widget library use?'

print()
print('=== EXPERIMENT 1: no context ===')
response = client.complete_chat(
    [{'role': 'user', 'content': question}]
)
print(response.choices[0].message.content)
print('=============================')

context = 'The Contoso Widget library is released under the Apache 2.0 license.'

print()
print('=== EXPERIMENT 2: with context ===')
response = client.complete_chat([
    {'role': 'system', 'content': 
     'Answer using ONLY the context below.'
     'If the answer is not in the context, say "Idon\'t know."\n\n'
     f'Context: {context}'},
     {'role': 'user', 'content': question}
])
print(response.choices[0].message.content)
print('=============================')

model.unload()
print('Model unloaded. Done.')