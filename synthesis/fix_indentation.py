with open('D:\\algorise-ai\\synthesis\\synthesis_guardrails.py', 'r') as f:
    lines = f.readlines()

# Find and fix the all_gates_pass method indentation
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    if line.strip().startswith('def all_gates_pass'):
        # Fix indentation: should be 4 spaces
        new_lines.append('    ' + line.lstrip())
        i += 1
        # Keep the rest of the method as-is until we hit the next method/class
        while i < len(lines):
            i += 1
            if i < len(lines):
                new_lines.append(lines[i])
                if lines[i].strip().startswith('def ') and 'all_gates_pass' not in lines[i]:
                    break
                if lines[i].strip().startswith('class ') and 'synthesis_guardrails' not in lines[i]:
                    break
    else:
        new_lines.append(line)
        i += 1

with open('D:\\algorise-ai\\synthesis\\synthesis_guardrails.py', 'w') as f:
    f.writelines(new_lines)
print('Fixed all_gates_pass indentation')