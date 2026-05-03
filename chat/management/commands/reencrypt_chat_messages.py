from django.core.management.base import BaseCommand

from chat.models import Message


class Command(BaseCommand):
    help = "Re-save all chat messages so message text is stored encrypted in MongoDB."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Optional limit for testing a smaller batch first.",
        )

    def handle(self, *args, **options):
        limit = int(options.get("limit") or 0)
        qs = Message.objects.order_by("timestamp")
        if limit > 0:
            qs = qs[:limit]

        total = 0
        for message in qs:
            message.save()
            total += 1
            if total % 100 == 0:
                self.stdout.write(f"Encrypted {total} messages...")

        self.stdout.write(self.style.SUCCESS(f"Finished encrypting {total} messages."))
