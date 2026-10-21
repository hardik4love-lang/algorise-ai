with open('synthesis_guardrails.py', 'r') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")
for i in range(300, 420):
    if i < len(lines):
        print(f'{i+1}: {repr(lines[i])}')