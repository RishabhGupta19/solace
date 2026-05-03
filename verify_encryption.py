"""
verify_encryption.py
--------------------
Verify encryption setup and test that messages can be encrypted/decrypted.

Usage:
    python manage.py shell < verify_encryption.py
    OR
    python verify_encryption.py
"""

import os
import sys
import django

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()

from chat.encryption import _get_fernet, encrypt_text, decrypt_text, _CIPHER_PREFIX
from chat.models import Message
import logging

logger = logging.getLogger(__name__)

def test_encryption():
    """Test that encryption/decryption works."""
    print("[TEST] Testing encryption setup...")
    
    # Test 1: Check if encryption key is loaded
    fernet = _get_fernet()
    if fernet is None:
        print("✗ CRITICAL: Encryption key NOT loaded!")
        print("   Set CHAT_ENCRYPTION_KEY environment variable in .env")
        return False
    
    print("✓ Encryption key loaded successfully")
    
    # Test 2: Test encrypt/decrypt round-trip
    test_messages = [
        "Hello, this is a test message",
        "Another test with emojis: 😀🎉",
        "Special chars: !@#$%^&*()",
    ]
    
    for original in test_messages:
        encrypted = encrypt_text(original)
        decrypted = decrypt_text(encrypted)
        
        if not encrypted.startswith(_CIPHER_PREFIX):
            print(f"✗ FAILED: Text not encrypted: {original[:30]}")
            return False
        
        if decrypted != original:
            print(f"✗ FAILED: Decrypt mismatch for: {original[:30]}")
            return False
        
        print(f"✓ Encryption works: '{original[:30]}...' -> encrypted -> decrypted")
    
    # Test 3: Check database for plaintext messages
    plaintext_count = Message.objects(text__not__startswith=_CIPHER_PREFIX).count()
    if plaintext_count > 0:
        print(f"\n⚠️  WARNING: {plaintext_count} plaintext message(s) in database")
        print("   These are not encrypted. Run migrate_encrypt_messages.py to fix.")
        first_msg = Message.objects(text__not__startswith=_CIPHER_PREFIX).first()
        if first_msg:
            print(f"   Example: {str(first_msg.text)[:50]}...")
    else:
        print(f"\n✓ All messages in database are encrypted")
    
    # Test 4: Create a test message and verify it's encrypted
    print("\n[TEST] Creating test message...")
    try:
        test_msg = Message(
            couple_id="test_couple",
            user_id="test_user",
            sender="user",
            sender_role="gf",
            text="This is an encrypted test message",
            mode="calm",
        )
        test_msg.save()
        
        # Retrieve from database raw
        raw_from_db = Message.objects(id=test_msg.id).first()
        raw_text_in_db = raw_from_db._data.get('text')
        
        if raw_text_in_db.startswith(_CIPHER_PREFIX):
            print(f"✓ Message stored encrypted in MongoDB")
        else:
            print(f"✗ Message NOT encrypted in MongoDB: {raw_text_in_db}")
        
        # Clean up
        test_msg.delete()
        print("✓ Test message cleaned up")
        
    except Exception as e:
        print(f"✗ Error creating test message: {e}")
        return False
    
    print("\n[TEST] ✓ All encryption tests passed!")
    return True


def show_status():
    """Show current encryption status."""
    print("\n[STATUS] Current Encryption Status")
    print("=" * 50)
    
    fernet = _get_fernet()
    key_status = "✓ Loaded" if fernet else "✗ Not loaded"
    print(f"Encryption key: {key_status}")
    
    total_messages = Message.objects.count()
    plaintext_messages = Message.objects(text__not__startswith=_CIPHER_PREFIX).count()
    encrypted_messages = total_messages - plaintext_messages
    
    print(f"Total messages: {total_messages}")
    print(f"  ✓ Encrypted: {encrypted_messages}")
    print(f"  ⚠️  Plaintext: {plaintext_messages}")
    
    print("\n" + "=" * 50)


if __name__ == "__main__":
    success = test_encryption()
    show_status()
    
    sys.exit(0 if success else 1)
