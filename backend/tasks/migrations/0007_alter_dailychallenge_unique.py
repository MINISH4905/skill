# Generated manually for production: per-domain daily challenges

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0006_task_difficulty_task_solution_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dailychallenge",
            name="date",
            field=models.DateField(db_index=True),
        ),
        migrations.AlterField(
            model_name="dailychallenge",
            name="domain",
            field=models.CharField(db_index=True, max_length=100),
        ),
        migrations.AlterUniqueTogether(
            name="dailychallenge",
            unique_together={("date", "domain")},
        ),
    ]
