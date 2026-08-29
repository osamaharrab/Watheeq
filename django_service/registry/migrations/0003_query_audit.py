import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("registry", "0002_schema_registry_state"),
    ]

    operations = [
        migrations.CreateModel(
            name="QueryAudit",
            fields=[
                ("request_id", models.UUIDField(editable=False, primary_key=True, serialize=False)),
                ("question", models.TextField()),
                ("as_of", models.DateField(blank=True, null=True)),
                ("generated_cypher", models.TextField(blank=True, null=True)),
                ("cypher_executed", models.BooleanField(default=False)),
                ("model_name", models.CharField(max_length=100)),
                ("model_digest", models.CharField(max_length=128)),
                ("schema_version", models.CharField(max_length=64)),
                ("resolved_entities", models.JSONField(default=list)),
                ("citations", models.JSONField(default=list)),
                (
                    "outcome",
                    models.CharField(
                        choices=[
                            ("answered", "Answered"),
                            ("unsupported", "Unsupported"),
                            ("abstained", "Abstained"),
                            ("refused", "Refused"),
                            ("bounded_out", "Bounded out"),
                            ("unavailable", "Unavailable"),
                        ],
                        max_length=20,
                    ),
                ),
                ("final_response", models.JSONField()),
                ("failure_reason", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["created_at", "request_id"]},
        ),
    ]
