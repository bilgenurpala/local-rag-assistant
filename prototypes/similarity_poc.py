from foundry_local_sdk import Configuration, FoundryLocalManager
import math

config = Configuration(app_name='local_rag_assistant')
FoundryLocalManager.initialize(config)
manager = FoundryLocalManager.instance

model = manager.catalog.get_model('qwen3-embedding-0.6b')
print('Loading embedding model...')
model.download()
model.load()
client = model.get_embedding_client()

def cosine_similarity(vec_a, vec_b):
    """Return how similar two vectors are, from -1 (opposite) to 1 (identical)."""
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    return dot / (norm_a * norm_b)

documents =[
    'Cats drink milk.',
    'Dogs eat food.',
    'The weather is sunny today.',
]

query = 'What do cats like to drink?'

print('Embedding documents...')
doc_vectors = [client.generate_embedding(doc).data[0].embedding for doc in documents]
print('Embedding query...')
query_vector = client.generate_embedding(query).data[0].embedding

print()
print('=== SIMILARITY RESULTS ===')
scores = []
for doc, vec in zip(documents, doc_vectors):
    score = cosine_similarity(query_vector, vec)
    scores.append((score, doc))

scores.sort(reverse=True)
for score, doc in scores:
    print(f'{score:.3f} {doc}')
print('==========================')

model.unload()
print('Model unloaded. Done')