from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE TABLE IF NOT EXISTS "orders_truckmaintenanceintervals" (
                    "id" bigserial NOT NULL PRIMARY KEY,
                    "engine_oil_interval" integer NULL CHECK ("engine_oil_interval" >= 0),
                    "engine_oil_last_km" integer NULL CHECK ("engine_oil_last_km" >= 0),
                    "gearbox_oil_interval" integer NULL CHECK ("gearbox_oil_interval" >= 0),
                    "gearbox_oil_last_km" integer NULL CHECK ("gearbox_oil_last_km" >= 0),
                    "rear_axle_oil_interval" integer NULL CHECK ("rear_axle_oil_interval" >= 0),
                    "rear_axle_oil_last_km" integer NULL CHECK ("rear_axle_oil_last_km" >= 0),
                    "belts_interval" integer NULL CHECK ("belts_interval" >= 0),
                    "belts_last_km" integer NULL CHECK ("belts_last_km" >= 0),
                    "chains_interval" integer NULL CHECK ("chains_interval" >= 0),
                    "chains_last_km" integer NULL CHECK ("chains_last_km" >= 0),
                    "truck_id" bigint NOT NULL UNIQUE
                        REFERENCES "clients_truck" ("id") DEFERRABLE INITIALLY DEFERRED
                );
            """,
            reverse_sql='DROP TABLE IF EXISTS "orders_truckmaintenanceintervals";',
        ),
    ]
