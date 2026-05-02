"""
migrate_encrypt_messages.py
----------------------------
Migrate all plaintext messages in MongoDB to encrypted format.

This script should be run once to encrypt all existing messages that were
stored as plaintext before the encryption system was implemented.

Usage:
    python manage.py shell < migrate_encrypt_messages.py
    OR
    python migrate_encrypt_messages.py
"""

import os
import sys
import django

# Setup Django if running standalone
if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()

from chat.models import Message
from chat.encryption import encrypt_text, decrypt_text, _CIPHER_PREFIX
import logging

logger = logging.getLogger(__name__)

def migrate_messages():
    """
    Find all plaintext messages (those NOT starting with 'enc:') and re-encrypt them.
    This is safe to run multiple times - already-encrypted messages are skipped.
    """
    print("[MIGRATE] Starting message encryption migration...")
    
    # Find all messages with plaintext text (not encrypted)
    plaintext_messages = Message.objects(text__not__startswith=_CIPHER_PREFIX)
    count = plaintext_messages.count()
    
    if count == 0:
        print("[MIGRATE] ✓ No plaintext messages found - all messages are already encrypted!")
        return 0
    
    print(f"[MIGRATE] Found {count} plaintext message(s) to encrypt")
    
    encrypted_count = 0
    errors = 0
    
    for msg in plaintext_messages:
        try:
            original_text = msg.text
            # Re-encrypt by calling the field's to_mongo which will encrypt
            encrypted_text = encrypt_text(original_text)
            
            if encrypted_text != original_text:  # Only update if actually encrypted
                # Update directly in MongoDB to avoid side effects
                Message.objects(id=msg.id).update(set__text=encrypted_text)
                encrypted_count += 1
                print(f"[MIGRATE] ✓ Encrypted message {msg.id}: {len(original_text)} chars")
            else:
                print(f"[MIGRATE] ⚠ Message {msg.id} returned unchanged (key unavailable?)")
                errors += 1
        except Exception as e:
            print(f"[MIGRATE] ✗ Error encrypting message {msg.id}: {e}")
            errors += 1
    
    print(f"\n[MIGRATE] Migration complete!")
    print(f"  ✓ Encrypted: {encrypted_count}")
    print(f"  ✗ Errors: {errors}")
    
    return encrypted_count


def migrate_reply_texts():
    """
    Find and encrypt all plaintext reply_to_text fields.
    """
    print("\n[MIGRATE] Starting reply_to_text encryption migration...")
    
    # Find all messages with plaintext reply_to_text
    plaintext_replies = Message.objects(
        reply_to_text__exists=True,
        reply_to_text__not__startswith=_CIPHER_PREFIX
    )
    count = plaintext_replies.count()
    
    if count == 0:
        print("[MIGRATE] ✓ No plaintext reply texts found!")
        return 0
    
    print(f"[MIGRATE] Found {count} plaintext reply_to_text(s) to encrypt")
    
    encrypted_count = 0
    errors = 0
    
    for msg in plaintext_replies:
        try:
            original_text = msg.reply_to_text
            encrypted_text = encrypt_text(original_text)
            
            if encrypted_text != original_text:
                Message.objects(id=msg.id).update(set__reply_to_text=encrypted_text)
                encrypted_count += 1
                print(f"[MIGRATE] ✓ Encrypted reply text for message {msg.id}")
            else:
                print(f"[MIGRATE] ⚠ Reply text for message {msg.id} returned unchanged")
                errors += 1
        except Exception as e:
            print(f"[MIGRATE] ✗ Error encrypting reply_to_text for message {msg.id}: {e}")
            errors += 1
    
    print(f"\n[MIGRATE] Reply text migration complete!")
    print(f"  ✓ Encrypted: {encrypted_count}")
    print(f"  ✗ Errors: {errors}")
    
    return encrypted_count


def verify_encryption():
    """
    Verify that all messages are properly encrypted in the database.
    """
    print("\n[VERIFY] Checking message encryption status...")
    
    total = Message.objects.count()
    plaintext = Message.objects(text__not__startswith=_CIPHER_PREFIX).count()
    encrypted = total - plaintext
    
    print(f"[VERIFY] Total messages: {total}")
    print(f"[VERIFY] Encrypted: {encrypted}")
    print(f"[VERIFY] Plaintext (legacy): {plaintext}")
    
    if plaintext > 0:
        print(f"\n⚠️  WARNING: {plaintext} plaintext message(s) still in database!")
        print("   These should be encrypted. Run migrate_messages() to fix.")
    else:
        print("\n✓ All messages are encrypted!")
    
    return encrypted, plaintext


if __name__ == "__main__":
    encrypted_messages = migrate_messages()
    encrypted_replies = migrate_reply_texts()
    verify_encryption()
    
    print(f"\n[SUMMARY] Total encrypted: {encrypted_messages + encrypted_replies}")
