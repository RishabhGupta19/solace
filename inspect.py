path = '../two-hearts-chat/src/pages/Chat.jsx'
with open(path, 'rb') as f:
    raw = f.read()
text = raw.decode('utf-8', errors='surrogateescape')

checks = [
    ('visibleMessages declared early', 'isFocusedView = Array.isArray(focusedMessages);\r\n  // Declared here'),
    ('scrollToBottomOnNextRenderRef ref', 'scrollToBottomOnNextRenderRef = useRef(false)'),
    ('fetch effect flag set', 'scrollToBottomOnNextRenderRef.current = true'),
    ('render effect', 'setRenderedMessages(visibleMessages)'),
    ('scroll after render effect', 'if (!scrollToBottomOnNextRenderRef.current) return'),
    ('messagesToRender', 'const messagesToRender = renderedMessages.length'),
    ('no RAF in fetch effect', 'requestAnimationFrame(() => {\r\n        chatEndRef.current?.scrollIntoView' not in text),
]

print("=== VERIFICATION ===")
all_ok = True
for name, check in checks:
    if isinstance(check, bool):
        ok = check
    else:
        ok = check in text
    status = "OK" if ok else "FAIL"
    print(f"  [{status}] {name}")
    if not ok:
        all_ok = False

print()
if all_ok:
    print("All checks passed!")
else:
    print("Some checks failed!")
