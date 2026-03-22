# UsTwo Backend

Django + MongoDB backend for the UsTwo couple communication app.

## Stack
- **Django REST Framework** — REST API
- **Django Channels + Daphne** — WebSocket for calm mode chat
- **MongoDB Atlas** via mongoengine
- **Groq (llama-3.3-70b)** — AI for vent mode
- **JWT** — Authentication

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill in your values
daphne -p 8000 config.asgi:application
```

## API Reference

### Auth
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/register` | No | Register |
| POST | `/api/auth/login` | No | Login |
| POST | `/api/auth/refresh` | No | Refresh token |
| GET | `/api/auth/me` | Yes | Get current user |
| PUT | `/api/auth/role` | Yes | Set role gf/bf |

### Couple
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/couple/generate-code` | Yes | Get couple code |
| POST | `/api/couple/link` | Yes | Link with partner |

### Assessment
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/assessment/generate-questions` | Yes | Get 10 AI questions |
| POST | `/api/assessment/submit` | Yes | Submit answers |

### Chat
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/messages?mode=calm\|vent` | Yes | Get messages |
| POST | `/api/messages` | Yes | Save message |
| POST | `/api/chat/ai-respond` | Yes | AI reply (vent only) |
| POST | `/api/chat/resolve` | Yes | Clear vent messages |

### WebSocket (Calm Mode)
```
ws://127.0.0.1:8000/ws/chat/<couple_id>/
```
Send: `{ "text": "hello", "sender_role": "bf", "sender_name": "Rishabh" }`
Receive: `{ "id", "text", "sender", "sender_role", "sender_name", "timestamp" }`

### Goals
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/goals` | Yes | Get goals |
| POST | `/api/goals` | Yes | Create goal |
| PATCH | `/api/goals/<id>/toggle` | Yes | Toggle complete |
| PATCH | `/api/goals/<id>` | Yes | Edit goal |
| DELETE | `/api/goals/<id>` | Yes | Delete goal |

## Auth Header
```
Authorization: Bearer <access_token>
```
