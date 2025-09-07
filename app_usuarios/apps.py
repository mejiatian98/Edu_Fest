# app_usuarios/apps.py
from django.apps import AppConfig

class AppUsuariosConfig(AppConfig):
    name = 'app_usuarios'

    def ready(self):
        import app_usuarios.signals
