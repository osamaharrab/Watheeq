from django.db import migrations, models


SCHEMA_VERSION = "watheeq-graph-1.0.0"


def create_schema_registry_state(apps, schema_editor):
    SchemaRegistryState = apps.get_model("registry", "SchemaRegistryState")
    SchemaRegistryState.objects.create(id=1, version=SCHEMA_VERSION)


class Migration(migrations.Migration):
    dependencies = [
        ("registry", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SchemaRegistryState",
            fields=[
                (
                    "id",
                    models.PositiveSmallIntegerField(
                        default=1,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("version", models.CharField(max_length=64)),
            ],
            options={
                "constraints": [
                    models.CheckConstraint(
                        check=models.Q(id=1),
                        name="schema_registry_state_singleton_id",
                    )
                ],
            },
        ),
        migrations.RunPython(
            create_schema_registry_state,
            migrations.RunPython.noop,
        ),
    ]
