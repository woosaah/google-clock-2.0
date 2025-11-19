#!/usr/bin/env python3
"""Database initialization script."""

import sys
from database import init_db, drop_db, SessionLocal, Settings as SettingsModel


def initialize_default_settings():
    """Insert default settings into the database."""
    db = SessionLocal()
    try:
        # Default settings
        default_settings = [
            {
                "key": "clock_format",
                "value": {"format": "24hr", "show_seconds": True}
            },
            {
                "key": "weather_location",
                "value": {"city": "San Francisco", "country": "US", "units": "metric"}
            },
            {
                "key": "display",
                "value": {
                    "brightness": 100,
                    "auto_dim": True,
                    "dim_start_hour": 22,
                    "dim_end_hour": 7,
                    "dim_brightness": 30
                }
            },
            {
                "key": "voice",
                "value": {
                    "enabled": True,
                    "wake_word": "hey google",
                    "sensitivity": 0.5,
                    "volume": 80
                }
            },
            {
                "key": "media",
                "value": {
                    "auto_play": True,
                    "default_volume": 70,
                    "slideshow_duration": 10
                }
            }
        ]

        for setting in default_settings:
            existing = db.query(SettingsModel).filter_by(key=setting["key"]).first()
            if not existing:
                db_setting = SettingsModel(**setting)
                db.add(db_setting)
                print(f"Added default setting: {setting['key']}")
            else:
                print(f"Setting already exists: {setting['key']}")

        db.commit()
        print("\nDefault settings initialized successfully!")

    except Exception as e:
        print(f"Error initializing settings: {e}")
        db.rollback()
    finally:
        db.close()


def main():
    """Main initialization function."""
    if len(sys.argv) > 1 and sys.argv[1] == "--drop":
        confirm = input("Are you sure you want to DROP all tables? (yes/no): ")
        if confirm.lower() == "yes":
            drop_db()
        else:
            print("Aborted.")
            return

    print("Initializing database tables...")
    init_db()

    print("\nInitializing default settings...")
    initialize_default_settings()

    print("\n✓ Database initialization complete!")


if __name__ == "__main__":
    main()
