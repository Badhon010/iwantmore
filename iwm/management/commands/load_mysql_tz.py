"""
Management command to populate MySQL timezone tables on Windows.

MySQL on Windows ships without timezone data, causing Django's CONVERT_TZ()
to return NULL and triggering:
  ValueError: Database returned an invalid datetime value.

This command populates the mysql.time_zone* tables with the essential
timezone offsets that Django needs (UTC and the project TIME_ZONE).
"""

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection


# Fixed-offset timezones from -12:00 to +14:00 (every 30 min) plus named
# aliases for common IANA zones that map to a single fixed offset today.
# This list is intentionally small — it covers what Django actually uses
# (UTC ↔ settings.TIME_ZONE) plus a generous set of offsets.

OFFSET_ZONES = []
for h in range(-12, 15):
    for m in (0, 30):
        total = h * 60 + (m if h >= 0 else -m)
        if -720 <= total <= 840:
            sign = "+" if total >= 0 else "-"
            abs_h, abs_m = divmod(abs(total), 60)
            name = f"{sign}{abs_h:02d}:{abs_m:02d}"
            OFFSET_ZONES.append((name, total * 60))  # offset in seconds

# Named timezone → offset in seconds  (current, ignoring historical DST)
NAMED_ZONES = {
    "UTC": 0,
    "GMT": 0,
    "US/Eastern": -18000,
    "US/Central": -21600,
    "US/Mountain": -25200,
    "US/Pacific": -28800,
    "America/New_York": -18000,
    "America/Chicago": -21600,
    "America/Denver": -25200,
    "America/Los_Angeles": -28800,
    "America/Sao_Paulo": -10800,
    "Europe/London": 0,
    "Europe/Berlin": 3600,
    "Europe/Paris": 3600,
    "Europe/Moscow": 10800,
    "Europe/Istanbul": 10800,
    "Asia/Dubai": 14400,
    "Asia/Karachi": 18000,
    "Asia/Kolkata": 19800,
    "Asia/Dhaka": 21600,
    "Asia/Bangkok": 25200,
    "Asia/Singapore": 28800,
    "Asia/Shanghai": 28800,
    "Asia/Hong_Kong": 28800,
    "Asia/Tokyo": 32400,
    "Asia/Seoul": 32400,
    "Australia/Sydney": 36000,
    "Pacific/Auckland": 43200,
}


class Command(BaseCommand):
    help = "Populate MySQL timezone tables so CONVERT_TZ() works on Windows."

    def handle(self, *args, **options):
        if "mysql" not in settings.DATABASES["default"]["ENGINE"]:
            self.stderr.write("This command is only for MySQL databases.")
            return

        tz_setting = getattr(settings, "TIME_ZONE", "UTC")
        if tz_setting not in NAMED_ZONES:
            NAMED_ZONES[tz_setting] = self._guess_offset(tz_setting)

        with connection.cursor() as cursor:
            # Check if already populated
            cursor.execute("SELECT COUNT(*) FROM mysql.time_zone")
            count = cursor.fetchone()[0]
            if count > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"mysql.time_zone already has {count} rows. "
                        "Skipping. Use --force to repopulate."
                    )
                )
                if "--force" not in args:
                    return

            self.stdout.write("Populating MySQL timezone tables...")

            zone_id = 0

            # 1) Insert all fixed-offset zones
            for name, offset_sec in OFFSET_ZONES:
                zone_id += 1
                self._insert_zone(cursor, zone_id, name, offset_sec)

            # 2) Insert named zones
            for name, offset_sec in NAMED_ZONES.items():
                zone_id += 1
                self._insert_zone(cursor, zone_id, name, offset_sec)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Done! Inserted {zone_id} timezone entries. "
                    f"Project TIME_ZONE '{tz_setting}' is included."
                )
            )

    @staticmethod
    def _insert_zone(cursor, zone_id, name, offset_seconds):
        cursor.execute(
            "INSERT INTO mysql.time_zone (Time_zone_id, Use_leap_seconds) "
            "VALUES (%s, 'N')",
            [zone_id],
        )
        cursor.execute(
            "INSERT INTO mysql.time_zone_name (Name, Time_zone_id) "
            "VALUES (%s, %s)",
            [name, zone_id],
        )
        cursor.execute(
            "INSERT INTO mysql.time_zone_transition_type "
            "(Time_zone_id, Transition_type_id, Offset, Is_DST, Abbreviation) "
            "VALUES (%s, 0, %s, 0, %s)",
            [zone_id, offset_seconds, name[:8]],
        )

    @staticmethod
    def _guess_offset(tz_name):
        """Try to get the current UTC offset for a timezone name."""
        try:
            from zoneinfo import ZoneInfo
            from datetime import datetime

            dt = datetime.now(ZoneInfo(tz_name))
            return int(dt.utcoffset().total_seconds())
        except Exception:
            return 0
