"""
Apply all Chat.jsx changes for WhatsApp-like scroll behavior.
"""
import sys

path = '../two-hearts-chat/src/pages/Chat.jsx'

with open(path, 'rb') as f:
    raw = f.read()

text = raw.decode('utf-8', errors='surrogateescape')
original_len = len(text)
changes = 0

# ── Change 1: Declare visibleMessages early (TDZ fix) ─────────────────────────
old1 = '  const isFocusedView = Array.isArray(focusedMessages);\r\n'
new1 = (
    '  const isFocusedView = Array.isArray(focusedMessages);\r\n'
    '  // Declared here (before any useEffect that reads it) to prevent TDZ crash\r\n'
    '  const visibleMessages = isFocusedView ? focusedMessages : currentMessages;\r\n'
)
if old1 in text:
    text = text.replace(old1, new1, 1)
    changes += 1
    print("Change 1 (TDZ fix): OK")
else:
    print("Change 1 FAILED - isFocusedView line not found with CRLF")
    sys.exit(1)

# ── Change 2: Add scrollToBottomOnNextRenderRef ref ───────────────────────────
old2 = '  const navigate = useNavigate();\r\n'
new2 = (
    '  const navigate = useNavigate();\r\n'
    '  const scrollToBottomOnNextRenderRef = useRef(false);\r\n'
)
if old2 in text:
    text = text.replace(old2, new2, 1)
    changes += 1
    print("Change 2 (new ref): OK")
else:
    print("Change 2 FAILED")
    sys.exit(1)

# ── Change 3: Replace premature RAF scroll in fetch effect ─────────────────────
# Exact content from file inspection (all CRLF, no setIsFetchingMessages here):
fetch_old = (
    '      requestAnimationFrame(() => {\r\n'
    "        chatEndRef.current?.scrollIntoView({ behavior: 'auto' });\r\n"
    '        requestAnimationFrame(() => {\r\n'
    '          if (!active) return;\r\n'
    '          isPositioningRef.current = false;\r\n'
    '          setScrollReady(true);\r\n'
    '        });\r\n'
    '      });\r\n'
)
fetch_new = (
    '      // Signal: scroll to bottom AFTER renderedMessages updates the DOM.\r\n'
    '      // Scrolling here fires before messages are painted.\r\n'
    '      scrollToBottomOnNextRenderRef.current = true;\r\n'
    '      setScrollReady(true);\r\n'
)
if fetch_old in text:
    text = text.replace(fetch_old, fetch_new, 1)
    changes += 1
    print("Change 3 (remove premature RAF scroll): OK")
else:
    print("Change 3 FAILED - dumping exact context:")
    idx = text.find("chatEndRef.current?.scrollIntoView")
    # find the auto one
    idx2 = text.find("'auto'", idx)
    while idx2 != -1:
        if "chatEndRef" in text[max(0,idx2-100):idx2]:
            print(repr(text[max(0,idx2-200):idx2+300]))
            break
        idx2 = text.find("'auto'", idx2+1)
    sys.exit(1)

# ── Change 4a: Add renderedMessages state if missing ─────────────────────────
if 'renderedMessages' not in text:
    old4 = '  const [isFetchingMessages, setIsFetchingMessages] = useState(true);\r\n'
    new4 = (
        '  const [isFetchingMessages, setIsFetchingMessages] = useState(true);\r\n'
        '  const [renderedMessages, setRenderedMessages] = useState([]);\r\n'
    )
    if old4 in text:
        text = text.replace(old4, new4, 1)
        changes += 1
        print("Change 4a (add renderedMessages state): OK")
    else:
        print("Change 4a FAILED")
        sys.exit(1)
else:
    print("Change 4a: renderedMessages already exists")

# ── Change 4b: Add render + scroll effects after fetch effect ─────────────────
if 'setRenderedMessages(visibleMessages)' not in text:
    close_marker = '  }, [mode, fetchMessages]);\r\n'
    close_idx = text.rfind(close_marker)
    if close_idx == -1:
        print("Change 4b FAILED")
        sys.exit(1)
    insert_pos = close_idx + len(close_marker)

    new_effects = (
        '\r\n'
        '  // Render all visible messages immediately — no chunk rendering.\r\n'
        '  // The backend caps initial fetch at 50 messages (not heavy), and\r\n'
        '  // chunk-rendering from index-0 (oldest) caused wrong initial scroll.\r\n'
        '  useEffect(() => {\r\n'
        '    setRenderedMessages(visibleMessages);\r\n'
        '  }, [visibleMessages]);\r\n'
        '\r\n'
        '  // Scroll to bottom AFTER renderedMessages is committed to the DOM.\r\n'
        '  useEffect(() => {\r\n'
        '    if (!scrollToBottomOnNextRenderRef.current) return;\r\n'
        '    scrollToBottomOnNextRenderRef.current = false;\r\n'
        '    requestAnimationFrame(() => {\r\n'
        "      chatEndRef.current?.scrollIntoView({ behavior: 'auto' });\r\n"
        '      isPositioningRef.current = false;\r\n'
        '    });\r\n'
        '  }, [renderedMessages]);\r\n'
    )
    text = text[:insert_pos] + new_effects + text[insert_pos:]
    changes += 1
    print("Change 4b (render + scroll effects): OK")
else:
    print("Change 4b: effects already present")

# ── Change 5: Remove duplicate visibleMessages near return, add messagesToRender
old5 = (
    '  const showNotLinkedMessage = isCalm && !isLinked;\r\n'
    '  const visibleMessages = isFocusedView ? focusedMessages : currentMessages;\r\n'
    '\r\n'
    '  return ('
)
new5 = (
    '  const showNotLinkedMessage = isCalm && !isLinked;\r\n'
    '  const messagesToRender = renderedMessages.length || visibleMessages.length === 0 ? renderedMessages : visibleMessages;\r\n'
    '\r\n'
    '  return ('
)
if old5 in text:
    text = text.replace(old5, new5, 1)
    changes += 1
    print("Change 5 (add messagesToRender, remove dup visibleMessages): OK")
elif '  const messagesToRender' in text:
    print("Change 5: messagesToRender already exists")
else:
    print("Change 5 FAILED - near-return block not found")
    idx5 = text.find('showNotLinkedMessage')
    print(repr(text[max(0,idx5-10):idx5+300]))
    sys.exit(1)

# ── Write output ──────────────────────────────────────────────────────────────
with open(path, 'wb') as f:
    f.write(text.encode('utf-8', errors='surrogateescape'))

print(f"\n{changes} changes applied. {original_len} -> {len(text)} bytes. SUCCESS!")
