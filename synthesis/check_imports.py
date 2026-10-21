with open(r'D:\algorise-ai\synthesis\synthesis_guardrails.py', 'r') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")
for i in range(0, min(50, len(lines))):
    print(f'{i+1}: {repr(lines[i])}')