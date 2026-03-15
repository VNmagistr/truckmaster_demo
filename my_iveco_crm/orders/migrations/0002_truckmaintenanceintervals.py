from django.db import migrations, connection


def run_pg_sql(apps, schema_editor):
    if connection.vendor == 'postgresql':
        schema_editor.execute("""
            DROP SEQUENCE IF EXISTS orders_truckmaintenanceintervals_id_seq CASCADE;
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
        """)


def reverse_pg_sql(apps, schema_editor):
    if connection.vendor == 'postgresql':
        schema_editor.execute('DROP TABLE IF EXISTS "orders_truckmaintenanceintervals";')


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(run_pg_sql, reverse_pg_sql),
    ]
