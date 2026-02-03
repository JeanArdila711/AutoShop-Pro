# AutoShop-Pro

Sistema de gestión para talleres automotrices desarrollado con Django.

## Requisitos

- Python 3.12+
- Django 5.0+

## Instalación

1. Clonar el repositorio:
```bash
git clone https://github.com/JeanArdila711/AutoShop-Pro.git
cd AutoShop-Pro
```

2. Crear entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Aplicar migraciones:
```bash
python manage.py migrate
```

5. Ejecutar servidor de desarrollo:
```bash
python manage.py runserver
```

## Estructura del Proyecto

```
AutoShop-Pro/
├── autoshop/          # Configuración principal de Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── manage.py
├── requirements.txt
└── README.md
```

## Licencia

MIT
