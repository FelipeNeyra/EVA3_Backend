from django.db import migrations, models


OLD_COLUMN = 'idCertificacion_Sanitaria'
NEW_COLUMN = 'id_certificacion_sanitaria'


def _rename_column(apps, schema_editor, source, target):
    Prestador = apps.get_model('website', 'Prestador')
    field = Prestador._meta.get_field('numCertificacion_sanitaria')
    table = Prestador._meta.db_table

    with schema_editor.connection.cursor() as cursor:
        columns = {
            column.name
            for column in schema_editor.connection.introspection.get_table_description(
                cursor,
                table,
            )
        }

    if target in columns:
        return
    if source not in columns:
        raise RuntimeError(
            f'No se encontró la columna esperada en {table}: {source} o {target}.'
        )

    new_field = field.clone()
    new_field.db_column = target
    new_field.set_attributes_from_name(field.name)
    new_field.model = Prestador
    schema_editor.alter_field(Prestador, field, new_field)


def forwards(apps, schema_editor):
    _rename_column(apps, schema_editor, OLD_COLUMN, NEW_COLUMN)


def backwards(apps, schema_editor):
    _rename_column(apps, schema_editor, NEW_COLUMN, OLD_COLUMN)


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0010_alter_reservahasservicio_id_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(forwards, backwards),
            ],
            state_operations=[
                migrations.AlterField(
                    model_name='prestador',
                    name='numCertificacion_sanitaria',
                    field=models.CharField(
                        db_column=NEW_COLUMN,
                        max_length=45,
                    ),
                ),
            ],
        ),
    ]
