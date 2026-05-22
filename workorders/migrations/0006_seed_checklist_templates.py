from django.db import migrations


CHECKLISTS = {
    'MOTOR': [
        'Nivel y estado del aceite',
        'Estado del filtro de aire',
        'Filtro de aceite',
        'Banda de distribución',
        'Bujías',
        'Compresión de cilindros',
        'Fugas visibles',
        'Estado del radiador / refrigerante',
    ],
    'TRANSMISION': [
        'Nivel del aceite de transmisión',
        'Estado del embrague',
        'Cambios suaves',
        'Ruidos anómalos al cambiar',
        'Fugas en caja',
        'Estado de soportes',
    ],
    'SUSPENSION': [
        'Amortiguadores delanteros',
        'Amortiguadores traseros',
        'Bujes',
        'Rótulas',
        'Bieletas',
        'Resortes',
        'Alineación visual',
    ],
    'FRENOS': [
        'Pastillas delanteras',
        'Pastillas traseras',
        'Discos / tambores',
        'Líquido de frenos',
        'Mangueras y líneas',
        'Freno de mano',
        'Pedal — recorrido y firmeza',
    ],
    'ELECTRICO': [
        'Batería — voltaje y bornes',
        'Alternador',
        'Motor de arranque',
        'Luces delanteras',
        'Luces traseras y stop',
        'Direccionales',
        'Tablero — testigos',
        'Fusibles',
    ],
    'CARROCERIA': [
        'Pintura — golpes y rayones',
        'Vidrios',
        'Espejos',
        'Puertas y cerraduras',
        'Sellos y empaques',
        'Estado del chasis',
    ],
    'GENERAL': [
        'Revisión visual general',
        'Niveles de fluidos',
        'Llantas — desgaste y presión',
        'Limpiaparabrisas',
        'Cinturones de seguridad',
        'Documentos del vehículo',
    ],
}


def crear_templates(apps, schema_editor):
    ChecklistTemplate = apps.get_model('workorders', 'ChecklistTemplate')
    ChecklistTemplateItem = apps.get_model('workorders', 'ChecklistTemplateItem')
    for categoria, items in CHECKLISTS.items():
        tmpl, _ = ChecklistTemplate.objects.get_or_create(
            categoria=categoria,
            defaults={'descripcion': f'Plantilla estándar — {categoria}'},
        )
        if not tmpl.items.exists():
            for i, texto in enumerate(items):
                ChecklistTemplateItem.objects.create(template=tmpl, texto=texto, orden=i)


def borrar_templates(apps, schema_editor):
    ChecklistTemplate = apps.get_model('workorders', 'ChecklistTemplate')
    ChecklistTemplate.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ('workorders', '0005_checklisttemplate_bahia_checklisttemplateitem_and_more'),
    ]
    operations = [migrations.RunPython(crear_templates, borrar_templates)]
