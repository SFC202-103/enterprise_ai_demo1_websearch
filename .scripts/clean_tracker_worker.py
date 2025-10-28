from pathlib import Path

p = Path('src/tracker_worker.py')
if not p.exists():
    print('file missing')
    raise SystemExit(1)
text = p.read_text(encoding='utf-8')
# Remove common markdown/patch markers accidentally included
text = text.replace('```python\n', '')
text = text.replace('\n```\n', '\n')
text = text.replace('\n*** End Patch', '')
# Also remove any trailing '*** End Patch' with newline
text = text.replace('*** End Patch\n', '')
# Trim leading/trailing whitespace
text = text.strip('\n') + '\n'
p.write_text(text, encoding='utf-8')
print('cleaned')
