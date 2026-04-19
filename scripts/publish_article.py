#!/usr/bin/env python3
"""Publish Dev.to draft article 3521010 on schedule."""
import requests

API_KEY = 'VuqtfNaAJifTz4h2ckG3sCdG'
ARTICLE_ID = 3521010

r = requests.put(
    f'https://dev.to/api/articles/{ARTICLE_ID}',
    headers={'api-key': API_KEY, 'Content-Type': 'application/json'},
    json={'article': {'published': True}},
    timeout=30
)
print(f'Status: {r.status_code}')
if r.status_code in (200, 201):
    d = r.json()
    print(f'URL: {d["url"]}')
    print(f'Published: {d.get("published")}')
else:
    print(r.text[:500])
