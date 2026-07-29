from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("_p2p", "0003_alter_p2p_content")]

    operations = [
        migrations.AddField(
            model_name="p2ppurchase",
            name="email_attempt_count",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="p2ppurchase",
            name="email_last_error",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="p2ppurchase",
            name="email_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
