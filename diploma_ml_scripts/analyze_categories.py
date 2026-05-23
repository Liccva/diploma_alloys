import json

with open('aloro/data_cleaned.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

categories = sorted(set(entry.get('category', 'unknown') for entry in data))

print(f"Всего уникальных категорий: {len(categories)}\n")
for i, cat in enumerate(categories, 1):
    print(f"{i:3d}. {cat}")
