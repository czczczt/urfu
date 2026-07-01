import json

with open('src/config/config.json') as f:
    data = json.load(f)

def save():
    with open('src/config/config.json', 'w') as f:
        json.dump(data, f)