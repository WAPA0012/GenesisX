import sys
import requests
import json

# 测试简单请求
print('=== Test 1: Simple ===')
response = requests.post(
    'http://127.0.0.1:5000/api/chat',
    json={'message': '123 * 456'},
    timeout=90
)
print(f'Status: {response.status_code}')
data = response.json()
resp_text = data.get('response', '')
print(f'Response: {resp_text[:200]}...')
print()
# Test 2
print('=== Test 2: Tool Call ===')
response = requests.post(
    'http://127.0.0.1:5000/api/chat',
    json={'message': 'Please帮我列出桌面上的文件'},
    timeout=90
)
print(f'Status: {response.status_code}')
data = response.json()
if 'response' in data:
    print(f'Response: {data["response"][:300]}...')
else:
    print(f'Error: {data.get("error", "Unknown")}')
